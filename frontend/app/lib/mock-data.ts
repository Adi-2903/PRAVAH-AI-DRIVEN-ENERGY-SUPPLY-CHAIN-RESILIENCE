// ═══════════════════════════════════════════════
//  PRAVAH — Centralized Mock Data Layer
//  Shaped exactly like the frozen JSON contracts.
//  Every view imports from here for demo/fallback mode.
// ═══════════════════════════════════════════════

// ─── Types ───────────────────────────────────────

export interface RiskSignal {
  type: 'geo_event' | 'ais_anomaly' | 'sanctions' | 'price';
  source: 'GDELT' | 'aisstream' | 'OFAC' | 'EIA';
  weight: number;
  detail: string;
}

export interface KeyEvent {
  headline: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  date: string;
  source: string;
  corridor: string;
}

export interface RiskScoreResponse {
  corridor: string;
  score: number;
  confidence: number;
  alert_level: 'low' | 'elevated' | 'high' | 'critical';
  signals: RiskSignal[];
  reasoning_trail: string;
  key_events: KeyEvent[];
  computed_at: string;
  data_sources: string[];
  model: string;
}

export interface SimulateResponse {
  scenario_id: string;
  brent_price_distribution: { p10: number; p50: number; p90: number; mean: number; std_dev: number };
  daily_price_path: Array<{ day: number; p10: number; p50: number; p90: number }>;
  pump_price_impact: { current_inr_per_litre: number; projected_p50_inr_per_litre: number; projected_p90_inr_per_litre: number };
  gdp_impact_pct: { p10: number; p50: number; p90: number };
  import_bill_delta_usd_bn: number;
  calibration_note: string;
  num_simulations_run: number;
  computed_at: string;
  data_source: string;
  volatility_calibrated_from: string;
  model: string;
}

export interface SupplierRecommendation {
  country: string;
  grade: string;
  price_usd: number;
  transit_days: number;
  route_risk: number;
  grade_match: number;
  score: number;
  why: string;
}

export interface RecommendResponse {
  ranked_suppliers: SupplierRecommendation[];
  reasoning_trail: string;
  as_of: string;
}

export interface DrawdownEntry {
  day: number;
  draw_bbl: number;
}

export interface SPRScheduleResponse {
  drawdown_schedule: DrawdownEntry[];
  days_of_cover_remaining: number;
  objective: string;
  reasoning_trail: string;
  as_of: string;
}

export interface CoordinatorResponse {
  summary: string;
  risk: RiskScoreResponse;
  scenario: SimulateResponse;
  procurement: RecommendResponse;
  spr: SPRScheduleResponse;
  as_of: string;
}

export interface CorridorRiskData {
  name: string;
  short: string;
  corridor_id: string;
  score: number;
  trend: 'up' | 'down' | 'stable';
  delta: string;
  volatility: 'Very High' | 'High' | 'Moderate' | 'Low';
  barrels: string;
  alert_level: 'critical' | 'high' | 'elevated' | 'low';
  confidence: number;
  signals: RiskSignal[];
  reasoning_trail: string;
  as_of: string;
}

export interface LiveSignal {
  time: string;
  source: 'GDELT' | 'AIS' | 'OFAC' | 'MARKET' | 'REUTERS';
  type: string;
  corridor: string;
  text: string;
  severity: 'CRITICAL' | 'HIGH' | 'ELEVATED' | 'LOW';
  color: 'critical' | 'high' | 'elevated' | 'low';
  is_dark_shipping?: boolean;
}

// ─── Timestamp helper ────────────────────────────

const now = () => new Date().toISOString();
const minutesAgo = (m: number) => new Date(Date.now() - m * 60000).toISOString();

// ─── Corridor Risk Data ──────────────────────────

export const CORRIDOR_RISK_DATA: CorridorRiskData[] = [
  {
    name: 'Strait of Hormuz',
    short: 'HORMUZ',
    corridor_id: 'hormuz',
    score: 82,
    trend: 'up',
    delta: '+5.8',
    volatility: 'Very High',
    barrels: '17M bbl/day',
    alert_level: 'critical',
    confidence: 0.74,
    signals: [
      { type: 'geo_event', source: 'GDELT', weight: 0.4, detail: 'Iran naval exercises near Strait of Hormuz; IRGC Commander issues warning on oil corridor access.' },
      { type: 'ais_anomaly', source: 'aisstream', weight: 0.3, detail: '3 VLCC tankers went dark near 26.5°N 56.2°E — AIS transponders off for 4+ hours in the traffic separation zone.' },
      { type: 'sanctions', source: 'OFAC', weight: 0.1, detail: '2 new Iranian entities added to SDN list — linked to crude oil shipping front companies.' },
      { type: 'price', source: 'EIA', weight: 0.2, detail: 'Brent crude +6.1% in 24h ($84.12), largest single-day move since March 2026.' },
    ],
    reasoning_trail: 'The Strait of Hormuz corridor risk is elevated to 82/100 driven primarily by GDELT-classified Iranian naval activity (weight 0.4, severity HIGH) combined with anomalous AIS dark-shipping patterns near the traffic separation zone (weight 0.3). Three VLCCs ceased transmitting for 4+ hours — consistent with sanctioned-vessel evasion patterns. OFAC added 2 new SDN entities linked to Iranian oil front companies, reinforcing sanctions enforcement pressure. Brent crude spiked 6.1% in the last 24 hours, confirming market perception of elevated chokepoint risk.',
    as_of: minutesAgo(3),
  },
  {
    name: 'Red Sea / Bab-el-Mandeb',
    short: 'RED SEA',
    corridor_id: 'redsea',
    score: 64.5,
    trend: 'up',
    delta: '+12.3',
    volatility: 'High',
    barrels: '8M bbl/day',
    alert_level: 'high',
    confidence: 0.68,
    signals: [
      { type: 'geo_event', source: 'GDELT', weight: 0.4, detail: 'Anti-ship missile fired near Bab-el-Mandeb commercial transit zone; no vessel hit.' },
      { type: 'ais_anomaly', source: 'aisstream', weight: 0.3, detail: 'Crude tanker diversions through Cape of Good Hope up 40% vs. monthly average.' },
      { type: 'price', source: 'EIA', weight: 0.2, detail: 'War-risk insurance premiums for Red Sea transit rose 15% week-over-week.' },
      { type: 'sanctions', source: 'OFAC', weight: 0.1, detail: 'No new sanctions activity in this corridor.' },
    ],
    reasoning_trail: 'Red Sea corridor risk elevated to 64.5/100 following an anti-ship missile event near the Bab-el-Mandeb strait. AIS data shows a 40% increase in crude tanker diversions via Cape of Good Hope, indicating the shipping industry is pricing in elevated risk. War-risk insurance premiums rose 15% WoW. No new OFAC activity specific to this corridor.',
    as_of: minutesAgo(8),
  },
  {
    name: 'Cape of Good Hope',
    short: 'CAPE',
    corridor_id: 'cape',
    score: 22.1,
    trend: 'down',
    delta: '-3.2',
    volatility: 'Low',
    barrels: '4M bbl/day',
    alert_level: 'low',
    confidence: 0.89,
    signals: [
      { type: 'geo_event', source: 'GDELT', weight: 0.4, detail: 'No geopolitical threats along Cape route. Normal South African port operations.' },
      { type: 'ais_anomaly', source: 'aisstream', weight: 0.3, detail: 'Increased tanker traffic — diverted vessels from Red Sea route operating normally.' },
      { type: 'price', source: 'EIA', weight: 0.2, detail: 'Bunkering costs at South African ports stable.' },
      { type: 'sanctions', source: 'OFAC', weight: 0.1, detail: 'No sanctions activity.' },
    ],
    reasoning_trail: 'Cape of Good Hope route risk low at 22.1/100. Increased traffic from Red Sea diversions is operating smoothly. No geopolitical threats, stable port operations and bunkering costs. This route is absorbing overflow traffic without congestion.',
    as_of: minutesAgo(5),
  },
  {
    name: 'Domestic Pipeline',
    short: 'DOMESTIC',
    corridor_id: 'domestic',
    score: 12.2,
    trend: 'stable',
    delta: '+0.4',
    volatility: 'Low',
    barrels: '—',
    alert_level: 'low',
    confidence: 0.6,
    signals: [
      { type: 'geo_event', source: 'GDELT', weight: 1.0, detail: 'Maintenance shutdown at an Indian refinery trims output.' },
    ],
    reasoning_trail: 'Domestic pipeline/refinery risk low at 12.2/100. Baseline domestic conditions with a routine refinery maintenance shutdown trimming output marginally. No supply-security concern.',
    as_of: minutesAgo(9),
  },
];

// ─── Live Signals Feed ───────────────────────────

export const LIVE_SIGNALS: LiveSignal[] = [
  {
    time: '14:22 IST',
    source: 'GDELT',
    type: 'GEO_EVENT',
    corridor: 'HORMUZ',
    text: 'Iran\'s IRGC Navy seizes second foreign-flagged tanker in Strait of Hormuz within 48 hours; US Fifth Fleet raises force posture to DEFCON-3 equivalent.',
    severity: 'CRITICAL',
    color: 'critical',
  },
  {
    time: '13:58 IST',
    source: 'AIS',
    type: 'DARK_SHIP',
    corridor: 'HORMUZ',
    text: '3 VLCCs (IMO 9834521, 9756203, 9812445) ceased AIS transmission near 26.5°N 56.2°E — traffic separation zone. Dark for 4+ hours. Pattern consistent with sanctioned-vessel evasion.',
    severity: 'CRITICAL',
    color: 'critical',
    is_dark_shipping: true,
  },
  {
    time: '13:48 IST',
    source: 'GDELT',
    type: 'MILITARY',
    corridor: 'RED SEA',
    text: 'Anti-ship ballistic missile fired near commercial vessel transit zone in southern Bab-el-Mandeb corridor. No vessel hit. Houthi-affiliated group claims responsibility.',
    severity: 'HIGH',
    color: 'high',
  },
  {
    time: '12:30 IST',
    source: 'OFAC',
    type: 'SANCTIONS',
    corridor: 'HORMUZ',
    text: 'US Treasury OFAC adds 2 new Iranian entities to SDN list — Petro Sina and Darya Bandar Shipping, both linked to crude oil front companies circumventing sanctions.',
    severity: 'HIGH',
    color: 'high',
  },
  {
    time: '11:15 IST',
    source: 'MARKET',
    type: 'INSURANCE',
    corridor: 'RED SEA',
    text: 'War-risk insurance premiums for Indian-flagged crude carriers in Red Sea corridor rise 15% week-over-week following regional military alerts. Lloyd\'s of London issues advisory.',
    severity: 'ELEVATED',
    color: 'elevated',
  },
  {
    time: '10:42 IST',
    source: 'AIS',
    type: 'DIVERSION',
    corridor: 'CAPE',
    text: 'AIS tracking shows 12 crude tankers re-routed via Cape of Good Hope in last 24h — a 40% increase vs. monthly average. Bunkering demand at Durban port rising.',
    severity: 'ELEVATED',
    color: 'elevated',
  },
  {
    time: '09:30 IST',
    source: 'MARKET',
    type: 'PRICE',
    corridor: 'HORMUZ',
    text: 'Brent crude spot surges 6.1% to $84.12/bbl — largest single-day move since March 2026. Asian Oman/Dubai premium widens to $2.80/bbl over Brent.',
    severity: 'HIGH',
    color: 'high',
  },
  {
    time: '08:15 IST',
    source: 'GDELT',
    type: 'DIPLOMACY',
    corridor: 'HORMUZ',
    text: 'India\'s External Affairs Ministry issues travel advisory for Gulf region; MoP&NG convenes emergency meeting on crude import contingency planning.',
    severity: 'ELEVATED',
    color: 'elevated',
  },
];

// ─── Mock Risk Score (Flagship) ──────────────────

export const MOCK_RISK_SCORE: RiskScoreResponse = {
  corridor: 'Strait of Hormuz',
  score: 82,
  confidence: 0.74,
  alert_level: 'critical',
  signals: CORRIDOR_RISK_DATA[0].signals,
  reasoning_trail: CORRIDOR_RISK_DATA[0].reasoning_trail,
  key_events: [
    { headline: 'Iran seizes second tanker in Strait of Hormuz', severity: 'critical', date: minutesAgo(30), source: 'GDELT', corridor: 'hormuz' },
    { headline: '3 VLCCs dark near Hormuz TSS — sanctioned vessel evasion pattern', severity: 'critical', date: minutesAgo(45), source: 'aisstream', corridor: 'hormuz' },
    { headline: 'OFAC adds 2 Iranian crude-shipping front companies to SDN list', severity: 'high', date: minutesAgo(120), source: 'OFAC', corridor: 'hormuz' },
    { headline: 'Brent crude +6.1% in 24h to $84.12/bbl', severity: 'high', date: minutesAgo(180), source: 'EIA', corridor: 'hormuz' },
  ],
  computed_at: minutesAgo(3),
  data_sources: ['GDELT', 'aisstream', 'OFAC', 'EIA'],
  model: 'gemini-2.5-flash',
};

// ─── Mock Simulate ───────────────────────────────

export const MOCK_SIMULATE: SimulateResponse = {
  scenario_id: 'sc_hormuz_001',
  brent_price_distribution: { p10: 88.0, p50: 96.0, p90: 112.0, mean: 97.4, std_dev: 8.1 },
  daily_price_path: Array.from({ length: 28 }, (_, i) => ({
    day: i + 1,
    p10: 82 + i * 0.22,
    p50: 82 + i * 0.5 + Math.sin(i / 3) * 2,
    p90: 82 + i * 1.07 + Math.sin(i / 2) * 3,
  })),
  pump_price_impact: { current_inr_per_litre: 96.5, projected_p50_inr_per_litre: 104.2, projected_p90_inr_per_litre: 111.8 },
  gdp_impact_pct: { p10: -0.08, p50: -0.42, p90: -0.71 },
  import_bill_delta_usd_bn: 14.6,
  calibration_note: 'Elasticities validated against EIA historical shock: 2022 Ukraine invasion price spike. Volatility calibrated from 24 months of realized Brent returns.',
  num_simulations_run: 10000,
  computed_at: minutesAgo(2),
  data_source: 'fallback_cache',
  volatility_calibrated_from: '2024-07-09 to 2026-07-09',
  model: 'gemini-2.5-flash',
};

// ─── Mock Recommend ──────────────────────────────

export const MOCK_RECOMMEND: RecommendResponse = {
  ranked_suppliers: [
    { country: 'Russia', grade: 'Urals', price_usd: 63.0, transit_days: 24, route_risk: 0.21, grade_match: 0.90, score: 0.81, why: 'Lowest corridor risk via Cape of Good Hope (22/100). Steep discount of $21/bbl vs. Arab Light baseline. 24-day transit is longer but acceptable for strategic diversification. Grade compatibility 90% with Jamnagar refinery (medium-sour blend).' },
    { country: 'USA', grade: 'WTI', price_usd: 74.0, transit_days: 40, route_risk: 0.15, grade_match: 0.78, score: 0.68, why: 'Near-zero corridor risk via trans-Atlantic/Cape route. Premium of $10/bbl offsets risk reduction. 40-day transit is the longest option. Light-sweet grade requires blending at Indian refineries optimised for medium-sour.' },
    { country: 'Nigeria', grade: 'Bonny Light', price_usd: 85.2, transit_days: 28, route_risk: 0.18, grade_match: 0.72, score: 0.62, why: 'Low-risk African route via Cape. Premium pricing ($85/bbl) but high-quality light-sweet crude. 28-day transit via West African corridor. Limited refinery grade compatibility for Indian downstream needs.' },
    { country: 'Iraq', grade: 'Basra Light', price_usd: 79.1, transit_days: 9, route_risk: 0.60, grade_match: 0.95, score: 0.55, why: 'Best grade match for Indian refineries (95%). Competitive pricing at $79/bbl. However, shares Hormuz transit risk (60/100) — only partial diversification. 9-day transit is fastest option.' },
    { country: 'UAE', grade: 'Murban', price_usd: 82.9, transit_days: 7, route_risk: 0.78, grade_match: 0.88, score: 0.42, why: 'Shortest transit (7 days) and good grade match (88%). However, fully exposed to Hormuz corridor risk (78/100) — same chokepoint as current Saudi baseline. No diversification benefit.' },
  ],
  reasoning_trail: 'Ranked 5 alternative suppliers for Hormuz disruption scenario. Optimization weighted: risk 30%, price 25%, transit 20%, grade compatibility 25%. Russia (Urals) ranks #1 due to steep price discount and Cape route risk avoidance, despite longer transit. USA (WTI) ranks #2 for minimal route risk but high cost and light-sweet grade mismatch. Iraq (Basra Light) offers best grade compatibility but shares Hormuz exposure.',
  as_of: minutesAgo(4),
};

// ─── Mock SPR Schedule ───────────────────────────

export const MOCK_SPR_SCHEDULE: SPRScheduleResponse = {
  drawdown_schedule: [
    { day: 1, draw_bbl: 900000 },
    { day: 2, draw_bbl: 900000 },
    { day: 3, draw_bbl: 850000 },
    { day: 4, draw_bbl: 800000 },
    { day: 5, draw_bbl: 700000 },
    { day: 6, draw_bbl: 500000 },
    { day: 7, draw_bbl: 350000 },
    { day: 8, draw_bbl: 200000 },
    { day: 9, draw_bbl: 100000 },
    { day: 10, draw_bbl: 0 },
  ],
  days_of_cover_remaining: 4.2,
  objective: 'Minimise weighted price impact subject to reserve floor constraint (20% minimum retention)',
  reasoning_trail: 'The LP solver front-loaded drawdowns during the first 5 days when projected Brent prices are highest ($96–$112/bbl range). Releases taper after Day 5 as prices stabilise and the reserve floor constraint begins to bind. Total release: 5.3M bbl over 9 active days. Reserve never drops below the 20% floor (4.2 days remaining). Strategy saves an estimated $8.2M vs. naive uniform-drawdown baseline.',
  as_of: minutesAgo(5),
};

// ─── Mock Coordinator ────────────────────────────

export const MOCK_COORDINATOR: CoordinatorResponse = {
  summary: 'The Strait of Hormuz corridor is at CRITICAL risk (82/100). In a 4-week disruption scenario, Brent crude is projected to reach $96/bbl (median), pushing Indian fuel prices up ~8% and adding $14.6B to the annual import bill. The AI recommends shifting procurement volume to Russian Urals ($63/bbl via Cape of Good Hope) and activating a front-loaded SPR drawdown schedule releasing 5.3M bbl over 9 days. This combined strategy reduces net exposure by 58% while keeping reserves above the safety floor.',
  risk: MOCK_RISK_SCORE,
  scenario: MOCK_SIMULATE,
  procurement: MOCK_RECOMMEND,
  spr: MOCK_SPR_SCHEDULE,
  as_of: minutesAgo(1),
};

// ─── Fetch with Fallback Utility ─────────────────

export async function fetchWithFallback<T>(
  url: string,
  fallback: T,
  options?: RequestInit
): Promise<{ data: T; is_live: boolean; as_of: string }> {
  try {
    const res = await fetch(url, { ...options, signal: AbortSignal.timeout(5000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return { data, is_live: true, as_of: now() };
  } catch {
    return { data: fallback, is_live: false, as_of: now() };
  }
}
