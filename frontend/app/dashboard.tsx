"use client";

import { useState, useEffect } from 'react';
import {
  AlertTriangle, TrendingUp, ChevronRight,
  Activity, BarChart3, Shield, Anchor, AlertCircle, Zap, Printer, FileDown, FileText
} from 'lucide-react';
import DataFreshness from './components/data-freshness';
import { MOCK_RISK_SCORE, CORRIDOR_RISK_DATA, LIVE_SIGNALS } from './lib/mock-data';
import { exportToPDF, exportToCSV, printReport } from './lib/export';
import { postJSON } from './lib/api';

// Single source of truth: derive the corridor table + feed from mock-data.ts
// (same data the Citizen and Risk Intelligence views use) so scores never
// disagree across screens. Swap mock-data.ts for live endpoints in Stage 9.
const riskData = CORRIDOR_RISK_DATA.map(c => ({
  name: c.name, short: c.short, score: c.score,
  trend: c.trend, delta: c.delta, vol: c.volatility, barrels: c.barrels,
}));

const feedItems = LIVE_SIGNALS.slice(0, 4);

function RiskBar({ score }: { score: number }) {
  const color = score > 70 ? '#ef4444' : score > 45 ? '#f97316' : '#22c55e';
  return (
    <div className="risk-bar-track">
      <div className="risk-bar-fill" style={{ width: `${score}%`, background: color }} />
    </div>
  );
}

export default function Dashboard({ onNavigate }: { onNavigate?: (tab: string) => void }) {
  const [liveDate, setLiveDate] = useState('');
  const [selectedFeed, setSelectedFeed] = useState<number | null>(null);
  const [riskDataState, setRiskDataState] = useState(() => riskData);

  useEffect(() => {
    async function fetchRiskData() {
      try {
        const promises = riskData.map(async (corridor) => {
          try {
            const result = await postJSON<any>('risk', '/risk-score', { corridor: corridor.name });
            return { ...corridor, score: result.score };
          } catch (e) {
            return corridor; // fallback to mock
          }
        });
        const newRiskData = await Promise.all(promises);
        setRiskDataState(newRiskData);
      } catch (e) {
        console.error(e);
      }
    }
    fetchRiskData();
  }, []);

  useEffect(() => {
    const now = new Date();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLiveDate(now.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' }).toUpperCase());
  }, []);

  const kpis = [
    { label: 'IMPORT DEPENDENCY', val: '88%',     sub: 'Crude sourced from imports',        icon: Anchor,       variant: 'info',     color: '#3b82f6' },
    { label: 'HORMUZ TRANSIT',    val: '42%',     sub: 'Share of Indian crude imports',     icon: Activity,     variant: 'warning',  color: '#f97316' },
    { label: 'SPR COVER',         val: '9.5 days',sub: 'Strategic reserve at national demand', icon: Shield,    variant: 'warning',  color: '#eab308' },
    { label: 'COMPOSITE RISK',    val: '74/100',  sub: '+12 pts vs 7-day avg',               icon: AlertCircle, variant: 'critical', color: '#ef4444' },
  ];

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1600, margin: '0 auto' }}>

      {/* Page Header */}
      <div style={{ marginBottom: 28, paddingBottom: 24, borderBottom: '1px solid rgba(0,0,0,0.07)' }}>
        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#94a3b8', marginBottom: 6 }}>
          Situation Report · {liveDate || '9 JULY 2026'}
        </div>
        <h1 style={{ fontSize: 34, fontWeight: 800, color: '#0f172a', fontFamily: 'var(--font-display)', letterSpacing: '-0.02em', lineHeight: 1.15, marginBottom: 8 }}>
          Command Center
        </h1>
        <p style={{ fontSize: 14, color: '#64748b', lineHeight: 1.7, maxWidth: 680, fontWeight: 500 }}>
          Anticipatory intelligence for India&apos;s crude oil supply chain. Composite risk signals aggregated across corridors, suppliers, and market indicators — updated continuously.
        </p>
      </div>

      {/* KPI Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
        {kpis.map((k, i) => {
          const Icon = k.icon;
          return (
            <div key={i} className={`kpi-card ${k.variant}`}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#94a3b8' }}>
                  {k.label}
                </span>
                <div style={{ padding: 8, borderRadius: 10, background: `${k.color}14`, flexShrink: 0 }}>
                  <Icon style={{ width: 16, height: 16, color: k.color }} />
                </div>
              </div>
              <div className="kpi-value" style={{ color: k.variant === 'critical' ? '#ef4444' : k.variant === 'warning' ? (i === 2 ? '#eab308' : '#f97316') : '#0f172a' }}>
                {k.val}
              </div>
              <div style={{ fontSize: 12, color: '#64748b', fontWeight: 500 }}>{k.sub}</div>
            </div>
          );
        })}
      </div>

      {/* Map + Corridor Table */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 16, marginBottom: 24 }}>

        {/* Supply Network Map */}
        <div className="card">
          <div className="card-header">
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: '#0f172a' }}>Global Supply Network</div>
              <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2, display: 'flex', alignItems: 'center', gap: 8 }}>
                Corridors · chokepoints · vessels
                <DataFreshness as_of={MOCK_RISK_SCORE.computed_at} compact />
              </div>
            </div>
            <button
              onClick={() => onNavigate?.('risk')}
              style={{ fontSize: 11, fontWeight: 700, color: '#2563eb', background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}
            >
              Open Risk Intelligence <ChevronRight style={{ width: 14, height: 14 }} />
            </button>
          </div>

          <div style={{ background: 'linear-gradient(160deg, #dbeafe 0%, #e0f2fe 50%, #d1fae5 100%)', padding: 16, minHeight: 300, position: 'relative' }}>
            <svg viewBox="0 0 700 360" style={{ width: '100%', height: '100%', maxHeight: 280 }} fill="none" xmlns="http://www.w3.org/2000/svg">
              {/* Africa */}
              <path d="M 55,130 Q 80,120 100,145 T 120,230 T 128,330 Q 148,360 138,370 T 108,330 T 78,250 T 40,185 Z" fill="#cbd5e1" stroke="#94a3b8" strokeWidth="1" />
              {/* Middle East */}
              <path d="M 125,110 Q 148,90 192,82 T 272,96 T 298,130 T 270,190 T 205,200 T 132,158 Z" fill="#cbd5e1" stroke="#94a3b8" strokeWidth="1" />
              {/* India */}
              <path d="M 332,76 Q 375,66 408,88 T 456,132 T 426,205 Q 406,232 395,252 T 363,192 T 322,122 Z" fill="#bfdbfe" stroke="#93c5fd" strokeWidth="1.5" />
              {/* SE Asia */}
              <path d="M 468,128 Q 508,140 538,172 T 568,232 T 588,270 Q 568,280 538,252 Z" fill="#cbd5e1" stroke="#94a3b8" strokeWidth="1" />

              {/* Sea lanes */}
              <path d="M 138,340 Q 230,305 385,205" stroke="#22c55e" strokeWidth="2" strokeDasharray="6 4" opacity="0.8" />
              <path d="M 175,152 Q 248,162 385,205" stroke="#f97316" strokeWidth="2.5" strokeDasharray="6 4" opacity="0.8" />
              <path d="M 275,126 Q 326,155 385,205" stroke="#ef4444" strokeWidth="3" strokeDasharray="6 4" opacity="0.9" />
              <path d="M 553,248 Q 465,232 385,205" stroke="#22c55e" strokeWidth="2" strokeDasharray="6 4" opacity="0.8" />

              {/* Hormuz - critical */}
              <circle cx="274" cy="126" r="9" fill="#ef4444" opacity="0.9" />
              <circle cx="274" cy="126" r="18" stroke="#ef4444" strokeWidth="1.5" fill="none" opacity="0.4" className="pulse-dot" />
              <rect x="278" y="108" rx="4" ry="4" width="130" height="20" fill="#0f172a" opacity="0.85" />
              <text x="283" y="121" fill="#fca5a5" fontSize="9" fontWeight="bold" fontFamily="sans-serif">Strait of Hormuz · CRITICAL</text>

              {/* Bab-el-Mandeb */}
              <circle cx="175" cy="152" r="7" fill="#f97316" opacity="0.9" />
              <rect x="100" y="160" rx="4" ry="4" width="108" height="20" fill="#0f172a" opacity="0.85" />
              <text x="105" y="173" fill="#fdba74" fontSize="9" fontWeight="bold" fontFamily="sans-serif">Bab-el-Mandeb · HIGH</text>

              {/* Malacca */}
              <circle cx="553" cy="248" r="6" fill="#22c55e" opacity="0.9" />
              <text x="518" y="278" fill="#4ade80" fontSize="9" fontWeight="bold" fontFamily="sans-serif">Malacca · LOW</text>

              {/* Mumbai */}
              <circle cx="385" cy="205" r="10" fill="#3b82f6" opacity="0.9" />
              <circle cx="385" cy="205" r="20" stroke="#3b82f6" strokeWidth="1" fill="none" opacity="0.35" />
              <text x="400" y="210" fill="#93c5fd" fontSize="10" fontWeight="bold" fontFamily="sans-serif">Mumbai</text>
            </svg>
          </div>

          {/* Legend */}
          <div style={{ padding: '12px 20px', borderTop: '1px solid rgba(0,0,0,0.05)', display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            {[['#ef4444', 'Critical'], ['#f97316', 'High'], ['#eab308', 'Elevated'], ['#22c55e', 'Low']].map(([c, l]) => (
              <span key={l} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, fontWeight: 600, color: '#64748b' }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: c, display: 'block' }} />
                {l}
              </span>
            ))}
          </div>
        </div>

        {/* Corridor Risk Table */}
        <div className="card">
          <div className="card-header">
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: '#0f172a' }}>Corridor Risk Monitor</div>
              <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2, display: 'flex', alignItems: 'center', gap: 8 }}>
                Real-time geopolitical risk scoring
                <DataFreshness as_of={CORRIDOR_RISK_DATA[0].as_of} compact />
              </div>
            </div>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 10px', borderRadius: 20, background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)' }}>
              <span className="pulse-dot" style={{ width: 6, height: 6, borderRadius: '50%', background: '#ef4444', display: 'block' }} />
              <span style={{ fontSize: 10, fontWeight: 800, color: '#ef4444', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Red Sea Alert Active</span>
            </span>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table" style={{ tableLayout: 'auto' }}>
              <thead>
                <tr>
                  <th>Corridor</th>
                  <th>Risk Score</th>
                  <th style={{ minWidth: 140 }}>Risk Spread</th>
                  <th style={{ whiteSpace: 'nowrap' }}>24h Δ</th>
                  <th style={{ whiteSpace: 'nowrap' }}>Volatility</th>
                  <th style={{ whiteSpace: 'nowrap', minWidth: 110 }}>Throughput</th>
                  <th style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {riskDataState.map(row => (
                  <tr key={row.name} onClick={() => onNavigate?.('simulator')} style={{ cursor: 'pointer' }}>
                    <td>
                      <div style={{ fontWeight: 700, fontSize: 13, color: '#0f172a' }}>{row.name}</div>
                      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', color: '#94a3b8', marginTop: 2 }}>{row.short}</div>
                    </td>
                    <td>
                      <span style={{
                        fontFamily: 'var(--font-mono)', fontSize: 20, fontWeight: 800,
                        color: row.score > 70 ? '#ef4444' : row.score > 40 ? '#f97316' : '#22c55e'
                      }}>
                        {row.score.toFixed(1)}
                      </span>
                    </td>
                    <td style={{ width: 160 }}>
                      <RiskBar score={row.score} />
                    </td>
                    <td>
                      <span style={{
                        fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 700,
                        color: row.trend === 'up' ? '#ef4444' : row.trend === 'down' ? '#22c55e' : '#94a3b8',
                        display: 'flex', alignItems: 'center', gap: 4
                      }}>
                        {row.trend === 'up' ? '▲' : row.trend === 'down' ? '▼' : '━'} {row.delta}
                      </span>
                    </td>
                    <td>
                      <span className={`badge badge-${row.vol === 'Very High' ? 'critical' : row.vol === 'High' ? 'high' : 'low'}`}>
                        {row.vol}
                      </span>
                    </td>
                    <td style={{ fontSize: 12, fontWeight: 600, color: '#64748b' }}>{row.barrels}</td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        onClick={e => { e.stopPropagation(); onNavigate?.('simulator'); }}
                        style={{
                          fontSize: 11, fontWeight: 700, color: '#2563eb', background: 'rgba(59,130,246,0.06)',
                          border: '1px solid rgba(59,130,246,0.2)', borderRadius: 8, padding: '6px 12px',
                          cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
                          transition: 'all 0.2s', marginLeft: 'auto',
                        }}
                        onMouseEnter={e => { (e.target as HTMLElement).closest('button')!.style.background = '#2563eb'; (e.target as HTMLElement).closest('button')!.style.color = '#fff'; }}
                        onMouseLeave={e => { (e.target as HTMLElement).closest('button')!.style.background = 'rgba(59,130,246,0.06)'; (e.target as HTMLElement).closest('button')!.style.color = '#2563eb'; }}
                      >
                        Model <ChevronRight style={{ width: 12, height: 12 }} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Live Signals + Right Panel */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>

        {/* Live Signals Feed */}
        <div className="card">
          <div className="card-header">
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: '#0f172a' }}>Live Signals</div>
              <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>News · AIS · Sanctions · Market</div>
            </div>
            <span className="badge badge-critical" style={{ animation: 'pulseDot 2s ease-in-out infinite' }}>
              <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#ef4444', display: 'inline-block' }} /> Live
            </span>
          </div>
          <div>
            {feedItems.map((item, i) => (
              <div
                key={i}
                onClick={() => setSelectedFeed(selectedFeed === i ? null : i)}
                className={`feed-item ${item.color}`}
                style={{ borderBottom: i < feedItems.length - 1 ? '1px solid rgba(0,0,0,0.05)' : 'none' }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{
                      fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600, color: '#64748b',
                      background: '#f8fafc', padding: '2px 8px', borderRadius: 6, border: '1px solid rgba(0,0,0,0.07)'
                    }}>
                      {item.time}
                    </span>
                    <span style={{ fontSize: 11, fontWeight: 700, color: '#334155', letterSpacing: '0.06em' }}>{item.source}</span>
                    <span style={{ fontSize: 10, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase' }}>· {item.type}</span>
                  </div>
                  <span className={`badge badge-${item.color}`}>{item.severity}</span>
                </div>
                <p style={{ fontSize: 13, color: '#1e293b', lineHeight: 1.65, fontWeight: 500 }}>{item.text}</p>
                {selectedFeed === i && (
                  <div style={{ marginTop: 14, display: 'flex', gap: 10 }}>
                    <button className="btn-primary" onClick={e => { e.stopPropagation(); onNavigate?.('simulator'); }}>
                      <BarChart3 style={{ width: 14, height: 14 }} /> Run Scenario
                    </button>
                    <button className="btn-secondary" onClick={e => e.stopPropagation()}>
                      View Raw Intel
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Right Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Strategic Reserves Status */}
          <div className="card" style={{ flex: 1 }}>
            <div className="card-header">
              <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: '#0f172a' }}>Strategic Reserves Status</div>
            </div>
            <div style={{ padding: '8px 0' }}>
              {[
                { label: 'Refinery Slack Capacity', val: '85%',    color: '#22c55e', pct: 85 },
                { label: 'VLCC Tanker Availability', val: '92%',   color: '#22c55e', pct: 92 },
                { label: 'Emergency SPR Stock',      val: '9.5 Days', color: '#ef4444', pct: 32 },
                { label: 'Pipeline Utilization',     val: '71%',   color: '#22c55e', pct: 71 },
                { label: 'Forex Cover (Oil import)', val: '62 Days', color: '#22c55e', pct: 78 },
              ].map((m, i) => (
                <div key={i} style={{ padding: '14px 24px', borderBottom: i < 4 ? '1px solid rgba(0,0,0,0.05)' : 'none' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <span style={{ fontSize: 12, fontWeight: 600, color: '#64748b' }}>{m.label}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 800, color: m.color }}>{m.val}</span>
                  </div>
                  <div className="risk-bar-track">
                    <div className="risk-bar-fill" style={{ width: `${m.pct}%`, background: m.color }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="card" style={{ padding: 20 }}>
            <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: '#0f172a', marginBottom: 14 }}>
              Quick Actions
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <button className="btn-primary" style={{ width: '100%', justifyContent: 'space-between', padding: '13px 18px', fontSize: 13 }} onClick={() => onNavigate?.('simulator')}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <BarChart3 style={{ width: 18, height: 18 }} /> Run Shock Scenario
                </span>
                <ChevronRight style={{ width: 18, height: 18, opacity: 0.8 }} />
              </button>
              <button className="btn-secondary" style={{ width: '100%', justifyContent: 'space-between', padding: '13px 18px', fontSize: 13 }} onClick={() => onNavigate?.('spr')}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Shield style={{ width: 18, height: 18, color: '#22c55e' }} /> Optimize SPR Release
                </span>
                <ChevronRight style={{ width: 18, height: 18, opacity: 0.5 }} />
              </button>
              {/* Export PDF */}
              <button className="btn-secondary" style={{ width: '100%', justifyContent: 'space-between', padding: '13px 18px', fontSize: 13 }}
                onClick={() => exportToPDF(
                  'Situation Report',
                  [
                    { heading: 'Composite Risk Index', content: `Current score: 74/100 (+12 pts vs 7-day average). Alert Level 3 — Elevated. Primary driver: Strait of Hormuz corridor risk at 82/100 due to Iranian naval activity and AIS dark-shipping anomalies.` },
                    { heading: 'Key Indicators', content: `Import Dependency: 88% of crude sourced from imports. Hormuz Transit: 42% of Indian crude imports. SPR Cover: 9.5 days (vs IEA 90-day benchmark). Brent Crude: ₹${(84.12 * 83.42).toFixed(2)}/bbl (+2.94% 24h).` },
                    { heading: 'Active Alerts', content: `CRITICAL: Iran seizes second tanker in Hormuz within 48h; US Fifth Fleet raises posture. HIGH: Anti-ship missile fired near Bab-el-Mandeb transit zone. ELEVATED: Shipping congestion at South African bunkering ports due to diversion flows.` },
                  ],
                  { headers: ['Corridor', 'Risk Score', '24h Change', 'Volatility', 'Throughput'], rows: riskDataState.map(r => [r.name, r.score.toFixed(1), r.delta, r.vol, r.barrels]) },
                  MOCK_RISK_SCORE.reasoning_trail
                )}
              >
                <span style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <FileDown style={{ width: 18, height: 18, color: '#eab308' }} /> Export PDF Report
                </span>
                <ChevronRight style={{ width: 18, height: 18, opacity: 0.5 }} />
              </button>
              {/* Export CSV */}
              <button className="btn-secondary" style={{ width: '100%', justifyContent: 'space-between', padding: '13px 18px', fontSize: 13 }}
                onClick={() => exportToCSV('PRAVAH_Corridor_Risk', ['Corridor', 'Short', 'Risk Score', '24h Change', 'Volatility', 'Throughput'], riskDataState.map(r => [r.name, r.short, r.score.toFixed(1), r.delta, r.vol, r.barrels]))}
              >
                <span style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <FileText style={{ width: 18, height: 18, color: '#22c55e' }} /> Export CSV Data
                </span>
                <ChevronRight style={{ width: 18, height: 18, opacity: 0.5 }} />
              </button>
              {/* Print */}
              <button className="btn-secondary" style={{ width: '100%', justifyContent: 'space-between', padding: '13px 18px', fontSize: 13 }}
                onClick={() => printReport('Situation Report')}
              >
                <span style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Printer style={{ width: 18, height: 18, color: '#3b82f6' }} /> Print Report
                </span>
                <ChevronRight style={{ width: 18, height: 18, opacity: 0.5 }} />
              </button>
            </div>
          </div>

        </div>
      </div>

    </div>
  );
}
