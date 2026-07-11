# PRAVAH Pipeline Audit

This document summarizes the audit of the Stage 1, 2, and 3 pipeline components, identifying disconnects between the data ingestion, the database schema, and the knowledge graph.

## Step 1: Audit Findings

1. **Live Data Sources (EIA, GDELT, aisstream.io, OFAC)**
   - **Clients are functional but isolated:** All four clients successfully fetch real data. However, they currently act as independent functions returning Python dictionaries.
   - **No data ingestion:** None of the clients actually insert their payload into the Supabase database. They only update the `data_sources` table to mark their health status (`is_live`, `last_synced`).

2. **Database Integration (Stage 2)**
   - **Disconnect:** The fetched data is NOT landing in the Supabase tables (`ships`, `risk_events`, etc.).
   - **Missing Schema Table:** The EIA client fetches crude oil spot prices, but there is no `crude_prices` or equivalent table defined in the `schema.sql`. (We will add a `crude_prices` table to hold this data).
   - **Missing schemas in Stage 3:** The clients do not currently fall back to reading from the database if they fail; they fall back to hardcoded mock dictionaries.

3. **Knowledge Graph (Stage 3)**
   - **Disconnect:** The `shared/db/knowledge_graph.py` builds the graph using entirely hardcoded, local dictionaries for `suppliers`, `corridors`, `ports`, `refineries`, and `fuels`. It does not query the actual `suppliers` or `corridors` tables in the Supabase database.

4. **JSON Schemas (`shared/schemas/`)**
   - **Disconnect:** The clients return loosely typed dictionaries instead of validating against the Pydantic models in `shared/schemas/`. 

## Identified Gaps

1. **Gap 1 (Ingestion):** Clients (GDELT, AIS, EIA, OFAC) do not INSERT their parsed payload into the Supabase tables (`risk_events`, `ships`, `crude_prices`).
2. **Gap 2 (Schema):** Missing `crude_prices` table in `shared/db/schema.sql` to store EIA data.
3. **Gap 3 (Fallbacks):** Clients fall back to hardcoded mock JSON instead of fetching the latest `last_synced_at` row from Supabase.
4. **Gap 4 (Knowledge Graph):** The Knowledge Graph does not read from Supabase; it reads from hardcoded lists.
5. **Gap 5 (Health Check & Orchestration):** No central `/system-status` API endpoint exists on the shared backend, and there is no unified script to run the full end-to-end flow.

## Fix Plan
- **EIA:** Add `crude_prices` table to `schema.sql`. Update `eia_client.py` to INSERT price. Fallback queries `crude_prices` for the latest entry.
- **GDELT:** Update `gdelt_client.py` to INSERT into `risk_events`. Fallback queries `risk_events`.
- **AIS:** Update `ais_client.py` to INSERT/UPSERT into `ships`. Fallback queries `ships`.
- **OFAC:** Update `ofac_client.py` to update the `ships.is_sanctioned` flag.
- **Knowledge Graph:** Update `knowledge_graph.py` to read `suppliers`, `corridors`, and `refineries` from Supabase using `db_helper.py`.
- **System Status:** Add `GET /system-status` to `shared/main.py`.
- **Orchestration:** Add `run_pipeline.sh` (and `run_pipeline.ps1`) that calls a single Python orchestrator.
- **Tests:** Add integration tests in `shared/clients/test_integration.py`.

## Stage 1-3 Schemas (Frozen)
The JSON/Pydantic schemas in `shared/schemas/` have been audited. They are intended as stable contracts for downstream consumers (risk-agent, scenario-engine). To ensure the pipeline works correctly without breaking those agents, **these schemas are now frozen**. No field names, types, or validations in `shared/schemas/` should be modified unless explicitly noted and negotiated with the downstream agent owners.

Specifically, the database columns in `risk_events`, `ships`, and other tables mapped by these schemas must be maintained identically moving forward.
