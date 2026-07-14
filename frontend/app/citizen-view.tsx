"use client";

import { useState, useEffect } from 'react';
import { Shield, TrendingUp, Fuel, Clock, ChevronRight, Activity } from 'lucide-react';
import { ComposableMap, Geographies, Geography, Marker, Line as RSMLine, ZoomableGroup } from 'react-simple-maps';
import { MOCK_RISK_SCORE, MOCK_COORDINATOR, CORRIDOR_RISK_DATA } from './lib/mock-data';
import DataFreshness from './components/data-freshness';

const GEO_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

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

function SimpleMap() {
  const corridors = CORRIDOR_RISK_DATA;
  const getColor = (s: number) => s > 70 ? '#ef4444' : s > 40 ? '#f97316' : '#22c55e';

  const points: { label: string; coordinates: [number, number]; score: number }[] = [
    { label: 'Hormuz', coordinates: [56.5, 26.5], score: corridors[0].score },
    { label: 'Red Sea', coordinates: [38.0, 20.0], score: corridors[1].score },
    { label: 'Suez', coordinates: [32.5, 29.9], score: corridors[2].score },
    { label: 'Cape', coordinates: [20.0, -35.0], score: corridors[3].score },
    { label: 'Malacca', coordinates: [100.0, 4.0], score: corridors[4].score },
  ];

  const INDIA_COORDS: [number, number] = [78.9629, 20.5937];

  return (
    <div style={{
      borderRadius: 16, overflow: 'hidden', height: 400, width: '100%',
      background: 'linear-gradient(160deg, rgba(30,41,59,0.8) 0%, rgba(15,23,42,0.9) 100%)',
      border: '2px solid rgba(255,255,255,0.1)',
      boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
      position: 'relative'
    }}>
      <ComposableMap projection="geoMercator" projectionConfig={{ scale: 150 }} style={{ width: '100%', height: '100%' }}>
        <ZoomableGroup center={[20, 20]} zoom={1.2}>
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map((geo) => (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  fill="rgba(148,163,184,0.15)"
                  stroke="rgba(148,163,184,0.5)"
                  strokeWidth={1.5}
                  style={{
                    default: { outline: 'none' },
                    hover: { fill: "rgba(148,163,184,0.25)", outline: 'none' },
                    pressed: { outline: 'none' },
                  }}
                />
              ))
            }
          </Geographies>

          {/* Lines to India */}
          {points.map(p => (
            <RSMLine
              key={`line-${p.label}`}
              from={p.coordinates}
              to={INDIA_COORDS}
              stroke={getColor(p.score)}
              strokeWidth={1.5}
              strokeDasharray="4 4"
              style={{ opacity: 0.6 }}
            />
          ))}

          {/* India Marker */}
          <Marker coordinates={INDIA_COORDS}>
            <circle r={6} fill="#3b82f6" opacity={0.9} />
            <circle r={14} stroke="#3b82f6" strokeWidth={1} fill="none" opacity={0.3} />
          </Marker>

          {/* Chokepoints */}
          {points.map(p => {
            const c = getColor(p.score);
            return (
              <Marker key={p.label} coordinates={p.coordinates}>
                <circle r={p.score > 70 ? 7 : 5} fill={c} opacity={0.9} />
                {p.score > 60 && (
                  <circle r={14} stroke={c} strokeWidth={1} fill="none" opacity={0.35} className="pulse-dot" />
                )}
                <text x={12} y={4} fill={c} fontSize={9} fontWeight="bold" fontFamily="sans-serif" opacity={0.9}>
                  {p.label} · {p.score}
                </text>
              </Marker>
            );
          })}
        </ZoomableGroup>
      </ComposableMap>
      <div style={{ position: 'absolute', top: 16, left: 16, fontSize: 11, fontWeight: 800, color: '#f8fafc', letterSpacing: '0.1em', textTransform: 'uppercase', background: 'rgba(0,0,0,0.5)', padding: '6px 12px', borderRadius: 8, backdropFilter: 'blur(4px)' }}>
        Global Risk Corridors
      </div>
    </div>
  );
}

/* ─── Main Citizen View ──────────────────────── */
export default function CitizenView({ onGoDeeper }: { onGoDeeper: () => void }) {
  const risk = MOCK_RISK_SCORE;
  const coord = MOCK_COORDINATOR;
  const [time, setTime] = useState('');

  useEffect(() => {
    const update = () => setTime(new Date().toLocaleTimeString('en-IN', { hour12: false }));
    update();
    const t = setInterval(update, 1000);
    return () => clearInterval(t);
  }, []);

  const getHeadline = (score: number) => {
    if (score > 75) return { text: 'critical risk', color: '#ef4444', bg: 'rgba(239,68,68,0.08)' };
    if (score > 50) return { text: 'high risk', color: '#f97316', bg: 'rgba(249,115,22,0.08)' };
    if (score > 30) return { text: 'elevated risk', color: '#eab308', bg: 'rgba(234,179,8,0.08)' };
    return { text: 'low risk', color: '#22c55e', bg: 'rgba(34,197,94,0.08)' };
  };
  const headline = getHeadline(risk.score);

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
          <DataFreshness as_of={risk.computed_at} source="Live Pipeline" />
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
          <RiskGauge score={risk.score} />
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
            {' '}due to Strait of Hormuz tensions
          </h1>
          <p style={{
            fontSize: 14, color: 'rgba(148,163,184,0.7)', marginTop: 14,
            lineHeight: 1.8, fontWeight: 500,
          }}>
            India sources 42% of crude via the Strait of Hormuz. A critical disruption could push Brent to ₹8,008–₹9,343/bbl, adding ₹1.2 Lakh Cr to the annual import bill and raising pump prices by ₹7.7/litre.
          </p>
        </div>

        {/* Map */}
        <div className="fade-in" style={{ width: '100%', marginBottom: 32, animationDelay: '0.3s' }}>
          <SimpleMap />
        </div>

        {/* KPI Row */}
        <div className="fade-in" style={{
          display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12,
          width: '100%', marginBottom: 40, animationDelay: '0.45s',
        }}>
          {[
            { icon: TrendingUp, label: 'Brent Crude', value: `₹${(84.12 * 83.42).toFixed(2)}`, sub: '+6.1% 24h', color: '#ef4444' },
            { icon: Fuel, label: 'Import Dependency', value: '88%', sub: 'Crude oil', color: '#3b82f6' },
            { icon: Shield, label: 'SPR Cover', value: '9.5 days', sub: 'vs 90-day IEA', color: '#eab308' },
            { icon: Activity, label: 'Import Bill', value: `₹${((137 * 83.42) / 10).toFixed(1)}L Cr`, sub: 'FY 2024-25', color: '#8b5cf6' },
          ].map(kpi => {
            const Icon = kpi.icon;
            return (
              <div key={kpi.label} style={{
                padding: '18px 16px', borderRadius: 14,
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.06)',
                display: 'flex', flexDirection: 'column', gap: 6,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Icon style={{ width: 13, height: 13, color: kpi.color }} />
                  <span style={{
                    fontSize: 9, fontWeight: 700, letterSpacing: '0.1em',
                    textTransform: 'uppercase', color: 'rgba(148,163,184,0.5)',
                  }}>{kpi.label}</span>
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
          {['EIA', 'GDELT', 'AIS Tracking', 'OFAC'].map(src => (
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
