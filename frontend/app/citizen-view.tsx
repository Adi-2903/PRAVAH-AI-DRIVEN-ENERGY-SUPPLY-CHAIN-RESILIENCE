"use client";

import { useState, useEffect } from 'react';
import { Shield, TrendingUp, Fuel, Clock, ChevronRight, Activity } from 'lucide-react';
import { MOCK_COORDINATOR } from './lib/mock-data';
import type { CoordinatorResponse } from './lib/mock-data';
import { postWithFallback } from './lib/api';
import { loadCorridors, loadMarket, compositeIndex } from './lib/live-data';
import type { LiveCorridor, MarketData } from './lib/live-data';
import DataFreshness from './components/data-freshness';

/* ─── Animated Risk Gauge ──────────────────────── */
function RiskGauge({ score, size = 220 }: { score: number; size?: number }) {
  const [animatedScore, setAnimatedScore] = useState(0);
  useEffect(() => {
    let frame: number;
    const start = performance.now();
    const animate = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / 1200, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setAnimatedScore(Math.round(score * eased));
      if (progress < 1) frame = requestAnimationFrame(animate);
    };
    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, [score]);

  const r = (size - 24) / 2;
  const circumference = 2 * Math.PI * r * 0.75;
  const offset = circumference - (animatedScore / 100) * circumference;

  const getColor = (s: number) => {
    if (s > 75) return '#ef4444';
    if (s > 50) return '#f97316';
    if (s > 30) return '#eab308';
    return '#22c55e';
  };
  const color = getColor(animatedScore);
  const getLabel = (s: number) => {
    if (s > 75) return 'CRITICAL';
    if (s > 50) return 'HIGH';
    if (s > 30) return 'ELEVATED';
    return 'LOW';
  };

  return (
    <div style={{ position: 'relative', width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Background arc */}
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={12}
          strokeDasharray={`${circumference} ${2 * Math.PI * r * 0.25}`}
          strokeLinecap="round"
          transform={`rotate(135 ${size / 2} ${size / 2})`}
        />
        {/* Score arc */}
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke={color} strokeWidth={12}
          strokeDasharray={`${circumference} ${2 * Math.PI * r}`}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform={`rotate(135 ${size / 2} ${size / 2})`}
          style={{
            transition: 'stroke-dashoffset 1.2s cubic-bezier(0.16, 1, 0.3, 1), stroke 0.3s',
            filter: `drop-shadow(0 0 12px ${color}66)`,
          }}
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
      }}>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 56, fontWeight: 900,
          color: '#fff', lineHeight: 1, letterSpacing: '-0.04em',
        }}>
          {animatedScore}
        </div>
        <div style={{ fontSize: 13, fontWeight: 700, color: 'rgba(255,255,255,0.5)', marginTop: 2 }}>
          / 100
        </div>
        <div style={{
          marginTop: 8, padding: '4px 12px', borderRadius: 20,
          background: `${color}1a`, border: `1px solid ${color}33`,
          fontSize: 10, fontWeight: 800, letterSpacing: '0.12em',
          color, textTransform: 'uppercase',
        }}>
          {getLabel(animatedScore)}
        </div>
      </div>
    </div>
  );
}

/* ─── Simplified Map (driven by live corridor scores) ─────────── */
const MAP_POS: Record<string, { label: string; x: number; y: number }> = {
  hormuz: { label: 'Hormuz', x: 274, y: 126 },
  redsea: { label: 'Red Sea', x: 175, y: 152 },
  cape:   { label: 'Cape', x: 138, y: 320 },
};

function SimpleMap({ corridors }: { corridors: LiveCorridor[] }) {
  const getColor = (s: number) => s > 70 ? '#ef4444' : s > 40 ? '#f97316' : '#22c55e';
  const points = corridors
    .filter(c => MAP_POS[c.corridor_id])
    .map(c => ({ ...MAP_POS[c.corridor_id], score: c.score }));

  return (
    <div style={{
      borderRadius: 16, overflow: 'hidden',
      background: 'linear-gradient(160deg, rgba(30,41,59,0.8) 0%, rgba(15,23,42,0.9) 100%)',
      border: '1px solid rgba(255,255,255,0.06)',
      padding: 16,
    }}>
      <svg viewBox="0 0 700 380" style={{ width: '100%', maxHeight: 280 }} fill="none">
        {/* Continents — simplified */}
        <path d="M 55,130 Q 80,120 100,145 T 120,230 T 128,330 Q 148,360 138,370 T 108,330 T 78,250 T 40,185 Z" fill="rgba(148,163,184,0.15)" stroke="rgba(148,163,184,0.25)" strokeWidth="0.8" />
        <path d="M 125,110 Q 148,90 192,82 T 272,96 T 298,130 T 270,190 T 205,200 T 132,158 Z" fill="rgba(148,163,184,0.15)" stroke="rgba(148,163,184,0.25)" strokeWidth="0.8" />
        <path d="M 332,76 Q 375,66 408,88 T 456,132 T 426,205 Q 406,232 395,252 T 363,192 T 322,122 Z" fill="rgba(96,165,250,0.12)" stroke="rgba(96,165,250,0.3)" strokeWidth="1" />
        <path d="M 468,128 Q 508,140 538,172 T 568,232 T 588,270 Q 568,280 538,252 Z" fill="rgba(148,163,184,0.15)" stroke="rgba(148,163,184,0.25)" strokeWidth="0.8" />

        {/* Sea lanes to India */}
        <path d="M 138,340 Q 230,305 385,205" stroke="rgba(34,197,94,0.4)" strokeWidth="1.5" strokeDasharray="4 3" />
        <path d="M 175,152 Q 248,162 385,205" stroke="rgba(249,115,22,0.5)" strokeWidth="2" strokeDasharray="4 3" />
        <path d="M 275,126 Q 326,155 385,205" stroke="rgba(239,68,68,0.6)" strokeWidth="2.5" strokeDasharray="4 3" />

        {/* India marker */}
        <circle cx="385" cy="205" r="6" fill="#3b82f6" opacity="0.9" />
        <circle cx="385" cy="205" r="14" stroke="#3b82f6" strokeWidth="1" fill="none" opacity="0.3" />

        {/* Chokepoint markers */}
        {points.map(p => {
          const c = getColor(p.score);
          return (
            <g key={p.label}>
              <circle cx={p.x} cy={p.y} r={p.score > 70 ? 7 : 5} fill={c} opacity="0.9" />
              {p.score > 60 && (
                <circle cx={p.x} cy={p.y} r={14} stroke={c} strokeWidth="1" fill="none" opacity="0.35" className="pulse-dot" />
              )}
              <text x={p.x + 12} y={p.y + 4} fill={c} fontSize="9" fontWeight="bold" fontFamily="sans-serif" opacity="0.9">
                {p.label} · {p.score.toFixed(0)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

/* ─── Main Citizen View ──────────────────────── */
export default function CitizenView({ onGoDeeper }: { onGoDeeper: () => void }) {
  const [coord, setCoord] = useState<CoordinatorResponse>(MOCK_COORDINATOR);
  const [corridors, setCorridors] = useState<LiveCorridor[]>([]);
  const [market, setMarket] = useState<MarketData | null>(null);
  const [time, setTime] = useState('');

  useEffect(() => {
    // Coordinator blend for the plain-English summary; corridors for the index+map; market for prices.
    postWithFallback<CoordinatorResponse>('coordinator', '/final-recommendation', { corridor: 'hormuz' }, MOCK_COORDINATOR)
      .then(({ data }) => setCoord(data));
    loadCorridors().then(({ data }) => setCorridors(data));
    loadMarket().then(({ data }) => setMarket(data));
  }, []);

  useEffect(() => {
    const update = () => setTime(new Date().toLocaleTimeString('en-IN', { hour12: false }));
    update();
    const t = setInterval(update, 1000);
    return () => clearInterval(t);
  }, []);

  // National index = throughput-weighted composite of live corridor scores
  // (falls back to the coordinator's corridor score before corridors load).
  const composite = corridors.length ? compositeIndex(corridors) : Math.round(coord.risk.score);
  const topCorridor = corridors.length
    ? corridors.reduce((a, b) => (b.score > a.score ? b : a))
    : null;
  const asOf = corridors[0]?.as_of ?? coord.risk.computed_at;

  const getHeadline = (score: number) => {
    if (score > 75) return { text: 'critical risk', color: '#ef4444', bg: 'rgba(239,68,68,0.08)' };
    if (score > 50) return { text: 'high risk', color: '#f97316', bg: 'rgba(249,115,22,0.08)' };
    if (score > 30) return { text: 'moderate risk', color: '#eab308', bg: 'rgba(234,179,8,0.08)' };
    return { text: 'low risk', color: '#22c55e', bg: 'rgba(34,197,94,0.08)' };
  };
  const headline = getHeadline(composite);
  const driverName = topCorridor?.name ?? 'Strait of Hormuz';

  return (
    <div style={{
      minHeight: '100vh', width: '100%',
      background: 'linear-gradient(160deg, #020617 0%, #0f172a 40%, #1e293b 100%)',
      display: 'flex', flexDirection: 'column',
      fontFamily: "'Inter', system-ui, sans-serif",
    }}>

      {/* ─── Subtle Branded Header ─── */}
      <header style={{
        padding: '16px 32px', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        borderBottom: '1px solid rgba(255,255,255,0.04)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: 'linear-gradient(135deg, #2563eb, #1d4ed8)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: 'white', fontSize: 14, fontWeight: 900, fontFamily: 'var(--font-display)',
            boxShadow: '0 2px 8px rgba(37,99,235,0.4)',
          }}>P</div>
          <span style={{ fontSize: 13, fontWeight: 800, color: '#f8fafc', letterSpacing: '0.14em' }}>PRAVAH</span>
          <span style={{ fontSize: 10, color: 'rgba(148,163,184,0.5)', fontWeight: 600 }}>· Energy Supply Chain Resilience</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <DataFreshness as_of={asOf} source="Live Pipeline" />
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600,
            color: 'rgba(148,163,184,0.6)', background: 'rgba(255,255,255,0.04)',
            padding: '4px 10px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.06)',
          }}>{time} IST</span>
        </div>
      </header>

      {/* ─── Main Content ─── */}
      <main style={{
        flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', padding: '40px 32px 60px',
        maxWidth: 900, margin: '0 auto', width: '100%',
      }}>

        {/* Risk Score Gauge */}
        <div className="fade-in" style={{ marginBottom: 32, textAlign: 'center' }}>
          <div style={{
            fontSize: 10, fontWeight: 700, letterSpacing: '0.14em', textTransform: 'uppercase',
            color: 'rgba(148,163,184,0.5)', marginBottom: 20,
          }}>
            India Energy Supply Risk Index
          </div>
          <RiskGauge score={composite} />
        </div>

        {/* Plain-English Headline */}
        <div className="fade-in" style={{
          textAlign: 'center', marginBottom: 40, animationDelay: '0.15s',
          maxWidth: 640,
        }}>
          <h1 style={{
            fontSize: 26, fontWeight: 700, color: '#f1f5f9',
            lineHeight: 1.5, letterSpacing: '-0.01em',
          }}>
            India&apos;s energy supply faces{' '}
            <span style={{
              color: headline.color,
              padding: '2px 8px', borderRadius: 6,
              background: headline.bg,
            }}>
              {headline.text}
            </span>
            {' '}— top driver: {driverName}
          </h1>
          <p style={{
            fontSize: 14, color: 'rgba(148,163,184,0.7)', marginTop: 14,
            lineHeight: 1.8, fontWeight: 500,
          }}>
            {coord.summary.split('.').slice(0, 2).join('.')}.
          </p>
        </div>

        {/* Map */}
        <div className="fade-in" style={{ width: '100%', marginBottom: 32, animationDelay: '0.3s' }}>
          <SimpleMap corridors={corridors} />
        </div>

        {/* KPI Row — one LIVE price + three published reference figures */}
        <div className="fade-in" style={{
          display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12,
          width: '100%', marginBottom: 16, animationDelay: '0.45s',
        }}>
          {[
            { icon: TrendingUp, label: 'Brent Crude', value: market ? `$${market.brent_usd.toFixed(2)}` : '—', sub: 'EIA reference spot', color: '#ef4444', live: false },
            { icon: Fuel, label: 'Import Dependency', value: '88%', sub: 'PPAC FY24-25', color: '#3b82f6', live: false },
            { icon: Shield, label: 'SPR Cover', value: '9.5 days', sub: 'ISPRL', color: '#eab308', live: false },
            { icon: Activity, label: 'Crude Import Bill', value: '$137B', sub: 'PPAC FY24-25', color: '#8b5cf6', live: false },
          ].map(kpi => {
            const Icon = kpi.icon;
            return (
              <div key={kpi.label} style={{
                padding: '18px 16px', borderRadius: 14,
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.06)',
                display: 'flex', flexDirection: 'column', gap: 6,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'space-between' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Icon style={{ width: 13, height: 13, color: kpi.color }} />
                    <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'rgba(148,163,184,0.5)' }}>{kpi.label}</span>
                  </span>
                  <span style={{ fontSize: 7, fontWeight: 800, letterSpacing: '0.06em', color: kpi.live ? '#22c55e' : 'rgba(148,163,184,0.5)', background: kpi.live ? 'rgba(34,197,94,0.1)' : 'rgba(148,163,184,0.1)', padding: '1px 4px', borderRadius: 3 }}>{kpi.live ? 'LIVE' : 'REF'}</span>
                </div>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: 22, fontWeight: 800,
                  color: '#f1f5f9', letterSpacing: '-0.02em',
                }}>{kpi.value}</div>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'rgba(148,163,184,0.5)' }}>{kpi.sub}</div>
              </div>
            );
          })}
        </div>
        <div className="fade-in" style={{ fontSize: 9, color: 'rgba(148,163,184,0.4)', marginBottom: 40, textAlign: 'center', animationDelay: '0.5s' }}>
          Risk index computed live from corridor scores · reference figures per PPAC / ISPRL · illustrative prototype
        </div>

        {/* Go Deeper CTA */}
        <div className="fade-in" style={{ animationDelay: '0.6s' }}>
          <button
            onClick={onGoDeeper}
            className="btn-primary"
            style={{
              padding: '14px 32px', fontSize: 14, borderRadius: 12,
              boxShadow: '0 4px 24px rgba(37,99,235,0.4)',
              gap: 10,
            }}
          >
            Go deeper — Analyst View
            <ChevronRight style={{ width: 18, height: 18 }} />
          </button>
        </div>

        {/* Data Sources Footer */}
        <div className="fade-in" style={{
          marginTop: 40, display: 'flex', alignItems: 'center', gap: 16,
          animationDelay: '0.75s',
        }}>
          <span style={{
            fontSize: 9, fontWeight: 700, letterSpacing: '0.1em',
            textTransform: 'uppercase', color: 'rgba(148,163,184,0.3)',
          }}>Powered by</span>
          {['EIA', 'GDELT', 'PPAC', 'ISPRL'].map(src => (
            <span key={src} style={{
              fontSize: 10, fontWeight: 700, color: 'rgba(148,163,184,0.4)',
              padding: '3px 8px', borderRadius: 4,
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.04)',
            }}>{src}</span>
          ))}
        </div>
      </main>
    </div>
  );
}
