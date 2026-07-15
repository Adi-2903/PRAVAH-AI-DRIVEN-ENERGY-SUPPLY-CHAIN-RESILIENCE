// Frontend↔backend contract / integration test (dependency-free — Node 18+).
//
// Asserts that the running backend returns the exact fields each frontend view
// reads, and that the derived values the UI shows (composite index, event feed,
// SPR real-input path) are genuinely live — not fabricated. Mirrors the transforms
// in frontend/app/lib/live-data.ts.
//
//   1) start the backend:  uvicorn api:app --port 8000
//   2) run:                node verify_frontend_contract.mjs   [BASE=http://host:port]
//
// Exit 0 = every contract the frontend depends on holds.
const BASE = process.env.BASE || 'http://127.0.0.1:8000';
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log('  ✓', m); } else { fail++; console.log('  ✗ FAIL:', m); } };

// --- transforms copied from frontend/app/lib/live-data.ts (keep in sync) ---
const THROUGHPUT_WEIGHT = { hormuz: 21, redsea: 9, cape: 6 };
const compositeIndex = (cs) => {
  let w = 0, s = 0;
  for (const c of cs) { const ww = THROUGHPUT_WEIGHT[c.corridor]; if (!ww) continue; w += ww; s += ww * c.score; }
  return w === 0 ? (cs.length ? Math.round(cs.reduce((a, c) => a + c.score, 0) / cs.length) : 0) : Math.round(s / w);
};
const alertLevelFor = (s) => s >= 75 ? 'critical' : s >= 55 ? 'high' : s >= 30 ? 'elevated' : 'low';

async function getJSON(path, opts) { const r = await fetch(`${BASE}${path}`, opts); if (!r.ok) throw new Error(`${path} -> HTTP ${r.status}`); return r.json(); }

async function main() {
  console.log(`\n=== FRONTEND CONTRACT CHECK @ ${BASE} ===\n`);

  console.log('[/corridors] Command Center + Risk Intelligence + composite index');
  const corridors = await getJSON('/corridors');
  ok(Array.isArray(corridors) && corridors.length === 4, `4 corridors (got ${corridors?.length})`);
  ok(corridors.map(c => c.corridor).join(',') === 'hormuz,redsea,cape,domestic', 'ids = hormuz,redsea,cape,domestic');
  for (const c of corridors) {
    for (const f of ['corridor', 'score', 'confidence', 'alert_level', 'signals', 'reasoning_trail', 'key_events', 'computed_at', 'model'])
      ok(f in c, `${c.corridor}.${f} present`);
    ok(c.score >= 0 && c.score <= 100, `${c.corridor}.score in range (${c.score})`);
    ok(['low', 'elevated', 'high', 'critical'].includes(c.alert_level), `${c.corridor}.alert_level valid`);
    ok(c.signals.every(s => 'type' in s && 'source' in s && 'weight' in s && 'detail' in s), `${c.corridor}.signals shape ok`);
    ok(c.key_events.every(e => 'headline' in e && 'severity' in e && 'date' in e && 'source' in e && 'corridor' in e), `${c.corridor}.key_events shape ok`);
  }
  const comp = compositeIndex(corridors);
  const scores = corridors.map(c => c.score);
  ok(comp >= Math.min(...scores) && comp <= Math.max(...scores), `composite index ${comp} within corridor range → alert ${alertLevelFor(comp)}`);
  const events = corridors.flatMap(c => c.key_events);
  ok(events.length > 0, `feed has ${events.length} real scoring events`);

  console.log('\n[/market] ticker + Brent spot + Citizen KPI');
  const m = await getJSON('/market');
  for (const f of ['brent_usd', 'wti_usd', 'dubai_usd', 'oman_usd', 'usd_inr', 'nat_gas_usd', 'is_live'])
    ok(f in m, `market.${f} present`);

  console.log('\n[/final-recommendation] Citizen View blend');
  const coord = await getJSON('/final-recommendation', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ corridor: 'hormuz' }) });
  ok(typeof coord.summary === 'string' && coord.summary.length > 40, 'coordinator.summary present');
  ok(coord.risk && typeof coord.risk.score === 'number', 'coordinator.risk.score present (Citizen gauge fallback)');

  console.log('\n[/simulate → /spr-schedule] SPR real-input path');
  const horizon = 14;
  const risk = corridors.find(c => c.corridor === 'hormuz').score;
  const sim = await getJSON('/simulate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ risk_score: risk, corridor: 'hormuz', shock_duration_days: horizon, num_simulations: 4000, current_brent_usd: 84.0, elasticity_assumptions: { price_elasticity_of_demand: -0.05, pass_through_rate_to_pump: 0.6, gdp_sensitivity_per_10pct_oil_shock: -0.15 } }) });
  ok(Array.isArray(sim.daily_price_path) && sim.daily_price_path.length === horizon, `real price path (${sim.daily_price_path?.length}d)`);
  const prices = sim.daily_price_path.map(p => Number(p.p50.toFixed(2)));
  const spr = await getJSON('/spr-schedule', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ planning_horizon_days: horizon, current_reserve_days: 9.5, min_safety_floor_days: 3.0, daily_risk_scores: Array(horizon).fill(risk), daily_price_forecast_usd_per_bbl: prices, max_daily_drawdown_days: 1.0 }) });
  ok(spr.schedule.length === horizon && spr.reserve_never_below_floor === true, 'SPR schedule respects floor over real inputs');
  ok(spr.schedule.some(d => d.price_usd === prices[d.day - 1]), 'SPR carries the REAL /simulate prices (not synthetic)');

  console.log(`\n=== ${pass} passed, ${fail} failed ===`);
  process.exit(fail === 0 ? 0 : 1);
}
main().catch(e => { console.error('ERROR:', e.message); process.exit(2); });
