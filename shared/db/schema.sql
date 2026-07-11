-- ================================================
-- PRAVAH — Master Database Schema
-- ================================================

-- Required for gen_random_uuid() below. Already enabled by default on
-- Supabase — this line only matters if someone runs this schema against
-- a bare/self-hosted Postgres instance instead.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Lookup: Countries
CREATE TABLE countries (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(3) UNIQUE NOT NULL,  -- ISO 3166-1 alpha-3, e.g. 'SAU'
    name        TEXT NOT NULL,
    region      TEXT,                         -- e.g. 'Middle East'
    import_share_pct FLOAT                   -- India's oil import share from this country
);

-- Lookup: Suppliers (crude oil producers/exporters)
CREATE TABLE suppliers (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    country_id  INT REFERENCES countries(id),
    grade       TEXT,                         -- 'Arab Light', 'Basra Heavy', etc.
    api_gravity FLOAT,
    sulphur_pct FLOAT,
    active      BOOLEAN DEFAULT TRUE
);

-- Shipping corridors
-- NOTE: `name` is the canonical identifier used everywhere in this project —
-- in this table, in shared/db/knowledge_graph.py node names, and in the
-- frozen schema enums below. It is ALWAYS lowercase (hormuz, redsea, cape,
-- domestic). Never introduce an uppercase or mixed-case variant anywhere —
-- a case mismatch between the DB and the graph is a silent join failure.
CREATE TABLE corridors (
    id              SERIAL PRIMARY KEY,
    name            TEXT UNIQUE NOT NULL,     -- e.g. 'hormuz', 'redsea', 'cape'
    display_name    TEXT,
    chokepoint_lat  FLOAT,
    chokepoint_lng  FLOAT,
    typical_transit_days INT,
    tankers_per_day_avg INT
);

-- Refineries
CREATE TABLE refineries (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    city        TEXT,
    state       TEXT,
    capacity_mbpd FLOAT,                     -- Million barrels per day
    primary_grade TEXT,                      -- crude grade it is configured for
    lat         FLOAT,
    lng         FLOAT
);

-- Ships (tankers being tracked)
CREATE TABLE ships (
    id          SERIAL PRIMARY KEY,
    mmsi        VARCHAR(9) UNIQUE,           -- AIS MMSI number
    name        TEXT,
    flag        VARCHAR(3),                  -- country code
    imo         TEXT,
    ship_type   TEXT,
    deadweight  INT,
    last_lat    FLOAT,
    last_lng    FLOAT,
    last_seen   TIMESTAMPTZ,
    is_sanctioned BOOLEAN DEFAULT FALSE
);

-- Risk events ingested from GDELT / news
CREATE TABLE risk_events (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    source          TEXT NOT NULL,            -- 'gdelt', 'manual', 'aisstream'
    headline        TEXT,
    corridor_id     INT REFERENCES corridors(id),
    country_id      INT REFERENCES countries(id),
    event_date      TIMESTAMPTZ NOT NULL,
    goldstein_scale FLOAT,                    -- GDELT conflict scale (-10 to +10)
    severity        TEXT,                     -- 'low', 'medium', 'high', 'critical'
    raw_payload     JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
-- You will query "latest events for this corridor" on every page load —
-- index it now rather than after the demo feels slow.
CREATE INDEX idx_risk_events_corridor_date ON risk_events (corridor_id, event_date DESC);

-- Risk scores computed by the Risk Agent
CREATE TABLE risk_scores (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    corridor_id     INT REFERENCES corridors(id),
    score           FLOAT NOT NULL,           -- 0 to 100
    confidence      FLOAT,
    reasoning_trail JSONB,                    -- full LangGraph chain output
    computed_at     TIMESTAMPTZ DEFAULT NOW(),
    data_sources    TEXT[]                    -- which sources informed this
);
-- Same reasoning as above: "give me the latest score for this corridor"
-- is the single most common query in the whole product.
CREATE INDEX idx_risk_scores_corridor_computed ON risk_scores (corridor_id, computed_at DESC);

-- Results from the Scenario Simulation Engine
CREATE TABLE scenario_results (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    corridor_id     INT REFERENCES corridors(id),
    risk_score_id   UUID REFERENCES risk_scores(id),
    brent_p10       FLOAT,
    brent_p50       FLOAT,
    brent_p90       FLOAT,
    pump_price_p50  FLOAT,
    gdp_impact_p50  FLOAT,
    num_simulations INT,
    computed_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Procurement recommendations from the Procurement Agent
CREATE TABLE recommendations (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    scenario_id     UUID REFERENCES scenario_results(id),
    supplier_id     INT REFERENCES suppliers(id),
    corridor_id     INT REFERENCES corridors(id),
    rank            INT,
    score           FLOAT,
    rationale       TEXT,
    estimated_cost_usd FLOAT,
    transit_days    INT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- SPR (Strategic Petroleum Reserve) release schedules
CREATE TABLE spr_schedule (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    scenario_id     UUID REFERENCES scenario_results(id),
    release_mbpd    FLOAT,                   -- million barrels per day
    duration_days   INT,
    start_date      DATE,
    cover_days_before FLOAT,
    cover_days_after  FLOAT,
    optimization_notes TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Track external data source health
CREATE TABLE data_sources (
    id          SERIAL PRIMARY KEY,
    name        TEXT UNIQUE NOT NULL,        -- 'eia_api', 'gdelt', 'aisstream', 'ofac'
    is_live     BOOLEAN DEFAULT FALSE,
    last_synced TIMESTAMPTZ,
    record_count INT,
    status_msg  TEXT
);

-- User-saved analysis views / sessions
CREATE TABLE user_views (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id     UUID,
    name        TEXT,
    view_type   TEXT,                        -- 'citizen', 'analyst', 'policy'
    config      JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ================================================
-- Row Level Security
-- ================================================
-- Your product has a public no-login Citizen view, so most tables (risk
-- scores, events, corridors, etc.) are meant to be openly readable via the
-- anon key — leave RLS off on those. user_views is the one table that holds
-- per-user private data, so it needs to be locked to its owner:

ALTER TABLE user_views ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own saved views"
    ON user_views FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own saved views"
    ON user_views FOR INSERT
    WITH CHECK (auth.uid() = user_id);
