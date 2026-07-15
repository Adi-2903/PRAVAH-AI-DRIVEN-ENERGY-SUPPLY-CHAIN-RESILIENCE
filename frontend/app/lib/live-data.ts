// ═══════════════════════════════════════════════
//  PRAVAH — Live data layer
//  Fetches REAL backend data (/corridors, /market) and maps the backend
//  RiskScoreResponse into the shapes the dashboard / risk / citizen views
//  render. Everything here is computed by api.py — no fabricated telemetry.
//  mock-data.ts is used ONLY as an offline fallback (badged as such by the UI).
// ═══════════════════════════════════════════════

import { serviceUrl } from './api';
import type { RiskSignal, KeyEvent, LiveSignal } from './mock-data';
import { CORRIDOR_RISK_DATA, LIVE_SIGNALS } from './mock-data';

// ── Backend response shapes (exactly what api.py returns) ────────────────────
export interface BackendRiskSignal { type: string; source: string; weight: number; detail: string; }
export interface BackendKeyEvent { headline: string; severity: 'low' | 'medium' | 'high' | 'critical'; date: string; source: string; corridor: string; }
export interface BackendRisk {
  corridor: string;
  score: number;
  confidence: number;
  alert_level: 'low' | 'elevated' | 'high' | 'critical';
  signals: BackendRiskSignal[];
  reasoning_trail: string;
  key_events: BackendKeyEvent[];
  computed_at: string;
  data_sources: string[];
  model: string;
}

export interface MarketData {
  brent_usd: number; wti_usd: number; dubai_usd: number; oman_usd: number;
  usd_inr: number; nat_gas_usd: number;
  is_live: boolean; data_source: string; fetched_at: string;
}

// ── UI-facing corridor shape (derived only from backend + reference facts) ───
export interface LiveCorridor {
  corridor_id: string;
  name: string;
  short: string;
  throughput: string | null;   // published reference volume; null = not applicable
  score: number;
  alert_level: 'low' | 'elevated' | 'high' | 'critical';
  volatility: 'Very High' | 'High' | 'Moderate' | 'Low';
  confidence: number;
  signals: RiskSignal[];
  key_events: KeyEvent[];
  reasoning_trail: string;
  model: string;
  as_of: string;
}

// Published real-world reference figures (facts, NOT live telemetry).
// Transit volumes are widely-cited EIA approximations for each chokepoint.
const CORRIDOR_META: Record<string, { name: string; short: string; throughput: string | null }> = {
  hormuz:   { name: 'Strait of Hormuz',        short: 'HORMUZ',   throughput: '≈21 Mb/d' },
  redsea:   { name: 'Red Sea / Bab-el-Mandeb', short: 'RED SEA',  throughput: '≈9 Mb/d' },
  cape:     { name: 'Cape of Good Hope',       short: 'CAPE',     throughput: '≈6 Mb/d' },
  domestic: { name: 'Domestic Pipeline',       short: 'DOMESTIC', throughput: null },
};

// Throughput weights (Mb/d) for the composite index — maritime chokepoints only.
const THROUGHPUT_WEIGHT: Record<string, number> = { hormuz: 21, redsea: 9, cape: 6 };

const now = () => new Date().toISOString();

function volatilityFor(score: number): LiveCorridor['volatility'] {
  if (score > 75) return 'Very High';
  if (score > 55) return 'High';
  if (score > 30) return 'Moderate';
  return 'Low';
}

/** Map one backend RiskScoreResponse → the UI corridor shape. */
export function mapBackendCorridor(r: BackendRisk): LiveCorridor {
  const meta = CORRIDOR_META[r.corridor] ?? { name: r.corridor, short: r.corridor.toUpperCase(), throughput: null };
  return {
    corridor_id: r.corridor,
    name: meta.name,
    short: meta.short,
    throughput: meta.throughput,
    score: r.score,
    alert_level: r.alert_level,
    volatility: volatilityFor(r.score),
    confidence: r.confidence,
    signals: r.signals as RiskSignal[],
    key_events: r.key_events as KeyEvent[],
    reasoning_trail: r.reasoning_trail,
    model: r.model,
    as_of: r.computed_at,
  };
}

/** Fallback: derive the same UI shape from the bundled mock (offline mode). */
function mockCorridors(): LiveCorridor[] {
  return CORRIDOR_RISK_DATA.map(c => ({
    corridor_id: c.corridor_id,
    name: c.name,
    short: c.short,
    throughput: CORRIDOR_META[c.corridor_id]?.throughput ?? c.barrels ?? null,
    score: c.score,
    alert_level: c.alert_level,
    volatility: c.volatility,
    confidence: c.confidence,
    signals: c.signals,
    key_events: [],
    reasoning_trail: c.reasoning_trail,
    model: 'offline-fallback',
    as_of: c.as_of,
  }));
}

/** Fetch REAL per-corridor risk from the backend. Never throws. */
export async function loadCorridors(): Promise<{ data: LiveCorridor[]; is_live: boolean; as_of: string }> {
  try {
    const res = await fetch(serviceUrl('risk', '/corridors'), { signal: AbortSignal.timeout(6000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const rows: BackendRisk[] = await res.json();
    if (!Array.isArray(rows) || rows.length === 0) throw new Error('empty');
    return { data: rows.map(mapBackendCorridor), is_live: true, as_of: now() };
  } catch {
    return { data: mockCorridors(), is_live: false, as_of: now() };
  }
}

/** Fetch REAL market prices from the backend. Never throws. */
export async function loadMarket(): Promise<{ data: MarketData; is_live: boolean }> {
  const fallback: MarketData = {
    brent_usd: 84.12, wti_usd: 80.55, dubai_usd: 82.9, oman_usd: 83.15,
    usd_inr: 83.42, nat_gas_usd: 2.81,
    is_live: false, data_source: 'offline-fallback', fetched_at: now(),
  };
  try {
    const res = await fetch(serviceUrl('procurement', '/market'), { signal: AbortSignal.timeout(6000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data: MarketData = await res.json();
    return { data, is_live: true };
  } catch {
    return { data: fallback, is_live: false };
  }
}

/**
 * Throughput-weighted composite risk index over the maritime chokepoints.
 * Chokepoints carrying more crude weigh proportionally more. Genuinely derived
 * from the live corridor scores — no hardcoded index.
 */
export function compositeIndex(corridors: LiveCorridor[]): number {
  let wSum = 0, sSum = 0;
  for (const c of corridors) {
    const w = THROUGHPUT_WEIGHT[c.corridor_id];
    if (!w) continue;
    wSum += w;
    sSum += w * c.score;
  }
  if (wSum === 0) {
    // no maritime corridors present — fall back to a plain mean
    return corridors.length ? Math.round(corridors.reduce((a, c) => a + c.score, 0) / corridors.length) : 0;
  }
  return Math.round(sSum / wSum);
}

export function alertLevelFor(score: number): 'low' | 'elevated' | 'high' | 'critical' {
  if (score >= 75) return 'critical';
  if (score >= 55) return 'high';
  if (score >= 30) return 'elevated';
  return 'low';
}

const SEV_COLOR: Record<string, LiveSignal['color']> = {
  critical: 'critical', high: 'high', medium: 'elevated', low: 'low',
};
const SEV_LABEL: Record<string, LiveSignal['severity']> = {
  critical: 'CRITICAL', high: 'HIGH', medium: 'ELEVATED', low: 'LOW',
};

/**
 * Build the intelligence feed from the REAL key_events the backend used to
 * score each corridor — the same events that drive the displayed scores.
 * Newest first. No invented headlines/IMO numbers.
 */
export function feedFromCorridors(corridors: LiveCorridor[]): LiveSignal[] {
  const events: (LiveSignal & { _ts: number })[] = [];
  for (const c of corridors) {
    for (const e of c.key_events) {
      const ts = new Date(e.date).getTime();
      events.push({
        _ts: Number.isNaN(ts) ? 0 : ts,
        time: Number.isNaN(ts)
          ? '—'
          : new Date(e.date).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false }) + ' IST',
        source: (e.source === 'GDELT' ? 'GDELT' : 'MARKET') as LiveSignal['source'],
        type: 'GEO_EVENT',
        corridor: c.short,
        text: e.headline,
        severity: SEV_LABEL[e.severity] ?? 'LOW',
        color: SEV_COLOR[e.severity] ?? 'low',
      });
    }
  }
  events.sort((a, b) => b._ts - a._ts);
  if (events.length === 0) {
    // Offline: reuse the bundled illustrative feed so the panel is never blank.
    return LIVE_SIGNALS;
  }
  return events.map(({ _ts, ...rest }) => rest);
}
