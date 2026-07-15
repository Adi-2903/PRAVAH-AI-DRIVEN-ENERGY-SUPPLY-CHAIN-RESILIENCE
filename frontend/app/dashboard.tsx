"use client";

import { useState, useEffect } from 'react';
import {
  ChevronRight, Activity, BarChart3, Shield, Anchor, AlertCircle, Zap, Wifi, WifiOff, RefreshCw
} from 'lucide-react';
import DataFreshness from './components/data-freshness';
import { loadCorridors, loadMarket, compositeIndex, alertLevelFor, feedFromCorridors } from './lib/live-data';
import type { LiveCorridor, MarketData } from './lib/live-data';
import type { LiveSignal } from './lib/mock-data';
import { exportToPDF } from './lib/export';

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
  const [corridors, setCorridors] = useState<LiveCorridor[]>([]);
  const [feed, setFeed] = useState<LiveSignal[]>([]);
  const [market, setMarket] = useState<MarketData | null>(null);
  const [isLive, setIsLive] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const now = new Date();
    setLiveDate(now.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' }).toUpperCase());
  }, []);

  const refresh = async () => {
    setLoading(true);
    const [c, m] = await Promise.all([loadCorridors(), loadMarket()]);
    setCorridors(c.data);
    setFeed(feedFromCorridors(c.data));
    setMarket(m.data);
    setIsLive(c.is_live);
    setLoading(false);
  };

  useEffect(() => { refresh(); }, []);

  const composite = corridors.length ? compositeIndex(corridors) : 0;
  const compositeAlert = alertLevelFor(composite);
  const criticalCount = corridors.filter(c => c.alert_level === 'critical').length;
  const topCorridor = corridors.length ? corridors.reduce((a, b) => (b.score > a.score ? b : a)) : null;
  const asOf = corridors[0]?.as_of ?? new Date().toISOString();

  // KPIs — three published reference figures (PPAC / MoP&NG / ISPRL) + one LIVE derived index.
  const kpis = [
    { label: 'IMPORT DEPENDENCY', val: '88%', sub: 'Crude imports · PPAC FY24-25', icon: Anchor, variant: 'info', color: '#3b82f6', live: false },
    { label: 'HORMUZ TRANSIT', val: '~42%', sub: 'Share of imports via Hormuz · PPAC', icon: Activity, variant: 'warning', color: '#f97316', live: false },
    { label: 'SPR COVER', val: '9.5 days', sub: 'Strategic reserve · ISPRL', icon: Shield, variant: 'warning', color: '#eab308', live: false },
    {
      label: 'COMPOSITE RISK',
      val: `${composite}/100`,
      sub: topCorridor ? `Driver: ${topCorridor.name} (${topCorridor.score.toFixed(0)})` : 'Computing…',
      icon: AlertCircle,
      variant: composite > 70 ? 'critical' : composite > 45 ? 'warning' : 'info',
      color: composite > 70 ? '#ef4444' : composite > 45 ? '#f97316' : '#22c55e',
      live: true,
    },
  ];

  const feedItems = feed.slice(0, 4);

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1600, margin: '0 auto' }}>

      {/* Page Header */}
      <div style={{ marginBottom: 28, paddingBottom: 24, borderBottom: '1px solid rgba(0,0,0,0.07)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#94a3b8', marginBottom: 6 }}>
              Situation Report · {liveDate || '—'}
            </div>
            <h1 style={{ fontSize: 34, fontWeight: 800, color: '#0f172a', fontFamily: 'var(--font-display)', letterSpacing: '-0.02em', lineHeight: 1.15, marginBottom: 8 }}>
              Command Center
            </h1>
            <p style={{ fontSize: 14, color: '#64748b', lineHeight: 1.7, maxWidth: 680, fontWeight: 500 }}>
              Anticipatory intelligence for India&apos;s crude oil supply chain. Corridor risk is scored live by the
              backend; the composite index is a throughput-weighted blend of those scores.
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span className={`badge ${isLive ? 'badge-low' : 'badge-elevated'}`} style={{ padding: '6px 10px' }}>
              {isLive ? <><Wifi style={{ width: 12, height: 12 }} /> Live backend</> : <><WifiOff style={{ width: 12, height: 12 }} /> Offline (sample)</>}
            </span>
            <button onClick={refresh} disabled={loading} className="btn-secondary" style={{ padding: '6px 12px' }}>
              <RefreshCw className={loading ? 'animate-spin' : ''} style={{ width: 13, height: 13 }} /> Refresh
            </button>
          </div>
        </div>
      </div>

      {/* KPI Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 10 }}>
        {kpis.map((k, i) => {
          const Icon = k.icon;
          return (
            <div key={i} className={`kpi-card ${k.variant}`}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 6 }}>
                  {k.label}
                  {k.live
                    ? <span style={{ fontSize: 8, fontWeight: 800, color: '#22c55e', background: 'rgba(34,197,94,0.1)', padding: '1px 5px', borderRadius: 4, letterSpacing: '0.06em' }}>LIVE</span>
                    : <span style={{ fontSize: 8, fontWeight: 800, color: '#94a3b8', background: 'rgba(148,163,184,0.12)', padding: '1px 5px', borderRadius: 4, letterSpacing: '0.06em' }}>REF</span>}
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
      <div style={{ fontSize: 10, color: '#94a3b8', fontWeight: 500, marginBottom: 24 }}>
        <strong>LIVE</strong> = computed by the backend now · <strong>REF</strong> = published reference figure (source noted). Illustrative prototype — not for operational use.
      </div>

      {/* Map + Corridor Table */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 16, marginBottom: 24 }}>

        {/* Supply Network Map */}
        <div className="card">
          <div className="card-header">
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: '#0f172a' }}>Global Supply Network</div>
              <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2, display: 'flex', alignItems: 'center', gap: 8 }}>
                Chokepoint alert levels (live)
                <DataFreshness as_of={asOf} compact />
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

              {(() => {
                // Drive chokepoint markers from live corridor alert levels.
                const byId = Object.fromEntries(corridors.map(c => [c.corridor_id, c]));
                const col = (id: string) => {
                  const s = byId[id]?.score ?? 0;
                  return s > 70 ? '#ef4444' : s > 40 ? '#f97316' : '#22c55e';
                };
                const lvl = (id: string) => (byId[id]?.alert_level ?? '—').toUpperCase();
                const pts = [
                  { id: 'hormuz', label: 'Strait of Hormuz', x: 274, y: 126, lx: 283, ly: 121, w: 130 },
                  { id: 'redsea', label: 'Bab-el-Mandeb', x: 175, y: 152, lx: 105, ly: 173, w: 118 },
                  { id: 'cape', label: 'Cape of Good Hope', x: 138, y: 320, lx: 60, ly: 335, w: 128 },
                ];
                return pts.map(p => {
                  const s = byId[p.id]?.score ?? 0;
                  return (
                  <g key={p.id}>
                    <circle cx={p.x} cy={p.y} r={s > 70 ? 9 : 7} fill={col(p.id)} opacity="0.9" />
                    {s > 60 && (
                      <circle cx={p.x} cy={p.y} r={18} stroke={col(p.id)} strokeWidth="1.5" fill="none" opacity="0.4" className="pulse-dot" />
                    )}
                    <rect x={p.lx - 5} y={p.ly - 13} rx="4" ry="4" width={p.w} height="20" fill="#0f172a" opacity="0.85" />
                    <text x={p.lx} y={p.ly} fill="#e2e8f0" fontSize="9" fontWeight="bold" fontFamily="sans-serif">{p.label} · {lvl(p.id)}</text>
                  </g>
                  );
                });
              })()}

              {/* Mumbai */}
              <circle cx="385" cy="205" r="10" fill="#3b82f6" opacity="0.9" />
              <circle cx="385" cy="205" r="20" stroke="#3b82f6" strokeWidth="1" fill="none" opacity="0.35" />
              <text x="400" y="210" fill="#1e40af" fontSize="10" fontWeight="bold" fontFamily="sans-serif">Mumbai</text>
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
                Backend-scored geopolitical risk
                <DataFreshness as_of={asOf} compact />
              </div>
            </div>
            {criticalCount > 0 && (
              <span style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 10px', borderRadius: 20, background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)' }}>
                <span className="pulse-dot" style={{ width: 6, height: 6, borderRadius: '50%', background: '#ef4444', display: 'block' }} />
                <span style={{ fontSize: 10, fontWeight: 800, color: '#ef4444', letterSpacing: '0.08em', textTransform: 'uppercase' }}>{criticalCount} Critical Corridor{criticalCount > 1 ? 's' : ''}</span>
              </span>
            )}
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Corridor</th>
                  <th>Risk Score</th>
                  <th style={{ minWidth: 140 }}>Risk Spread</th>
                  <th>Alert</th>
                  <th>Volatility</th>
                  <th>Throughput</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {corridors.map(row => (
                  <tr key={row.corridor_id} onClick={() => onNavigate?.('simulator')} style={{ cursor: 'pointer' }}>
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
                      <span className={`badge badge-${row.alert_level}`}>{row.alert_level}</span>
                    </td>
                    <td>
                      <span className={`badge badge-${row.volatility === 'Very High' ? 'critical' : row.volatility === 'High' ? 'high' : row.volatility === 'Moderate' ? 'elevated' : 'low'}`}>
                        {row.volatility}
                      </span>
                    </td>
                    <td style={{ fontSize: 12, fontWeight: 600, color: '#64748b' }}>{row.throughput ?? '—'}</td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        onClick={e => { e.stopPropagation(); onNavigate?.('simulator'); }}
                        style={{
                          fontSize: 11, fontWeight: 700, color: '#2563eb', background: 'rgba(59,130,246,0.06)',
                          border: '1px solid rgba(59,130,246,0.2)', borderRadius: 8, padding: '6px 12px',
                          cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, marginLeft: 'auto',
                        }}
                      >
                        Model <ChevronRight style={{ width: 12, height: 12 }} />
                      </button>
                    </td>
                  </tr>
                ))}
                {corridors.length === 0 && (
                  <tr><td colSpan={7} style={{ textAlign: 'center', color: '#94a3b8', padding: 24 }}>{loading ? 'Loading corridors…' : 'No data'}</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Live Signals + Right Panel */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>

        {/* Scoring Events Feed */}
        <div className="card">
          <div className="card-header">
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: '#0f172a' }}>Scoring Events</div>
              <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>Events driving the live corridor scores</div>
            </div>
            <span className={`badge ${isLive ? 'badge-low' : 'badge-elevated'}`}>
              {isLive ? 'From backend' : 'Sample feed'}
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
                    <span style={{ fontSize: 10, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase' }}>· {item.corridor}</span>
                  </div>
                  <span className={`badge badge-${item.color}`}>{item.severity}</span>
                </div>
                <p style={{ fontSize: 13, color: '#1e293b', lineHeight: 1.65, fontWeight: 500 }}>{item.text}</p>
                {selectedFeed === i && (
                  <div style={{ marginTop: 14, display: 'flex', gap: 10 }}>
                    <button className="btn-primary" onClick={e => { e.stopPropagation(); onNavigate?.('simulator'); }}>
                      <BarChart3 style={{ width: 14, height: 14 }} /> Run Scenario
                    </button>
                    <button className="btn-secondary" onClick={e => { e.stopPropagation(); onNavigate?.('risk'); }}>
                      View in Risk Center
                    </button>
                  </div>
                )}
              </div>
            ))}
            {feedItems.length === 0 && (
              <div style={{ padding: 40, textAlign: 'center', color: '#94a3b8', fontSize: 13 }}>{loading ? 'Loading events…' : 'No scoring events'}</div>
            )}
          </div>
        </div>

        {/* Right Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Composite Risk Breakdown (derived from live corridor scores) */}
          <div className="card" style={{ flex: 1 }}>
            <div className="card-header">
              <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: '#0f172a' }}>Composite Risk Breakdown</div>
              <span className={`badge badge-${compositeAlert}`}>{composite}/100 · {compositeAlert}</span>
            </div>
            <div style={{ padding: '8px 0' }}>
              {corridors.map((c, i) => {
                const color = c.score > 70 ? '#ef4444' : c.score > 45 ? '#f97316' : c.score > 30 ? '#eab308' : '#22c55e';
                return (
                  <div key={c.corridor_id} style={{ padding: '14px 24px', borderBottom: i < corridors.length - 1 ? '1px solid rgba(0,0,0,0.05)' : 'none' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                      <span style={{ fontSize: 12, fontWeight: 600, color: '#64748b' }}>{c.name}{c.throughput ? ` · ${c.throughput}` : ''}</span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 800, color }}>{c.score.toFixed(1)}</span>
                    </div>
                    <div className="risk-bar-track">
                      <div className="risk-bar-fill" style={{ width: `${c.score}%`, background: color }} />
                    </div>
                  </div>
                );
              })}
              {corridors.length === 0 && <div style={{ padding: 24, textAlign: 'center', color: '#94a3b8', fontSize: 12 }}>—</div>}
              <div style={{ padding: '12px 24px', fontSize: 10, color: '#94a3b8', fontWeight: 500, lineHeight: 1.5 }}>
                Composite = throughput-weighted mean of maritime chokepoint scores.
              </div>
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
              <button className="btn-secondary" style={{ width: '100%', justifyContent: 'space-between', padding: '13px 18px', fontSize: 13 }}
                onClick={() => exportToPDF(
                  'Situation Report',
                  [
                    { heading: 'Composite Risk Index', content: `Throughput-weighted composite: ${composite}/100 (${compositeAlert}). Top driver: ${topCorridor ? `${topCorridor.name} at ${topCorridor.score.toFixed(1)}/100 (${topCorridor.alert_level})` : 'n/a'}. Data source: ${isLive ? 'live backend' : 'offline sample'}.` },
                    { heading: 'Reference Indicators', content: `Import Dependency: 88% (PPAC FY24-25). Hormuz Transit: ~42% of imports (PPAC). SPR Cover: 9.5 days (ISPRL). Brent: $${market?.brent_usd?.toFixed(2) ?? '—'}/bbl (${market?.is_live ? 'live FX' : 'reference'}).` },
                    { heading: 'Corridor Scores', content: corridors.map(c => `${c.name}: ${c.score.toFixed(1)}/100 (${c.alert_level})`).join('. ') + '.' },
                  ],
                  {
                    headers: ['Corridor', 'Risk Score', 'Alert', 'Volatility', 'Throughput'],
                    rows: corridors.map(r => [r.name, r.score.toFixed(1), r.alert_level, r.volatility, r.throughput ?? '—']),
                  },
                  topCorridor?.reasoning_trail ?? ''
                )}
              >
                <span style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Zap style={{ width: 18, height: 18, color: '#eab308' }} /> Export Situation Report
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
