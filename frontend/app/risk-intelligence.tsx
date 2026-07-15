"use client";

import { useState, useEffect } from 'react';
import {
  AlertTriangle, Radio, Ship, Gavel, TrendingUp,
  Filter, ChevronDown, ChevronUp, AlertCircle, Wifi, WifiOff, RefreshCw
} from 'lucide-react';
import type { LiveSignal } from './lib/mock-data';
import { loadCorridors, feedFromCorridors } from './lib/live-data';
import type { LiveCorridor } from './lib/live-data';
import DataFreshness from './components/data-freshness';
import ReasoningTrail from './components/reasoning-trail';

/* ─── Corridor Risk Card ──────────────────────── */
function CorridorCard({ data, isSelected, onClick }: {
  data: LiveCorridor; isSelected: boolean; onClick: () => void;
}) {
  const getColor = (s: number) => s > 70 ? '#ef4444' : s > 40 ? '#f97316' : s > 25 ? '#eab308' : '#22c55e';
  const color = getColor(data.score);
  const totalWeight = data.signals.reduce((s, sig) => s + sig.weight, 0) || 1;

  return (
    <div
      onClick={onClick}
      className="card"
      style={{
        cursor: 'pointer',
        borderColor: isSelected ? `${color}44` : undefined,
        boxShadow: isSelected ? `0 4px 20px ${color}15, var(--card-shadow)` : undefined,
        transition: 'all 0.25s ease',
      }}
    >
      {/* Top accent */}
      <div style={{ height: 3, background: `linear-gradient(90deg, ${color}, ${color}66)` }} />

      <div style={{ padding: '20px 22px' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 800, color: '#0f172a', marginBottom: 2 }}>
              {data.name}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{
                fontSize: 9, fontWeight: 800, letterSpacing: '0.1em',
                textTransform: 'uppercase', color: '#94a3b8',
              }}>{data.short}</span>
              {data.throughput && (
                <span style={{ fontSize: 10, fontWeight: 600, color: '#94a3b8' }}>· {data.throughput}</span>
              )}
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: 28, fontWeight: 900,
              color, lineHeight: 1, letterSpacing: '-0.03em',
            }}>
              {data.score.toFixed(1)}
            </div>
            <div className={`badge badge-${data.alert_level}`} style={{ marginTop: 4 }}>
              {data.alert_level}
            </div>
          </div>
        </div>

        {/* Risk bar */}
        <div className="risk-bar-track" style={{ marginBottom: 12 }}>
          <div className="risk-bar-fill" style={{ width: `${data.score}%`, background: color }} />
        </div>

        {/* Volatility + Freshness */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <span className={`badge badge-${data.volatility === 'Very High' ? 'critical' : data.volatility === 'High' ? 'high' : data.volatility === 'Moderate' ? 'elevated' : 'low'}`}>
            {data.volatility} volatility
          </span>
          <DataFreshness as_of={data.as_of} compact />
        </div>

        {/* Signal weight bars */}
        {data.signals.length > 0 && (
          <div style={{ marginBottom: 12 }}>
            <div style={{
              fontSize: 9, fontWeight: 700, letterSpacing: '0.08em',
              textTransform: 'uppercase', color: '#94a3b8', marginBottom: 6,
            }}>Signal composition ({data.signals.length})</div>
            <div style={{ display: 'flex', height: 6, borderRadius: 3, overflow: 'hidden', gap: 1 }}>
              {data.signals.map((s, i) => {
                const sColors: Record<string, string> = { GDELT: '#f97316', aisstream: '#3b82f6', OFAC: '#ef4444', EIA: '#22c55e' };
                return (
                  <div key={i} style={{
                    width: `${(s.weight / totalWeight) * 100}%`,
                    background: sColors[s.source] || '#64748b',
                    borderRadius: 1,
                  }} />
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Signal Feed Item ────────────────────────── */
function SignalItem({ signal }: { signal: LiveSignal }) {
  const sourceIcons: Record<string, typeof AlertTriangle> = {
    GDELT: Radio, AIS: Ship, OFAC: Gavel, MARKET: TrendingUp, REUTERS: AlertTriangle,
  };
  const Icon = sourceIcons[signal.source] || AlertCircle;

  return (
    <div className={`feed-item ${signal.color}`} style={{
      borderBottom: '1px solid rgba(0,0,0,0.05)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Icon style={{ width: 12, height: 12, color: '#64748b' }} />
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 600, color: '#64748b',
            background: '#f8fafc', padding: '2px 6px', borderRadius: 4,
            border: '1px solid rgba(0,0,0,0.07)',
          }}>{signal.time}</span>
          <span style={{ fontSize: 10, fontWeight: 700, color: '#334155', letterSpacing: '0.05em' }}>{signal.source}</span>
          <span style={{ fontSize: 9, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase' }}>· {signal.type}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {signal.is_dark_shipping && (
            <span style={{
              fontSize: 8, fontWeight: 800, padding: '2px 6px', borderRadius: 4,
              background: 'rgba(239,68,68,0.08)', color: '#ef4444',
              border: '1px solid rgba(239,68,68,0.2)',
              letterSpacing: '0.06em', textTransform: 'uppercase',
            }}>⚠ DARK SHIPPING</span>
          )}
          <span className={`badge badge-${signal.color}`}>{signal.severity}</span>
        </div>
      </div>
      <p style={{ fontSize: 13, color: '#1e293b', lineHeight: 1.65, fontWeight: 500, margin: 0 }}>
        {signal.text}
      </p>
      <div style={{
        fontSize: 9, fontWeight: 600, color: '#94a3b8', marginTop: 6,
        textTransform: 'uppercase', letterSpacing: '0.06em',
      }}>
        {signal.corridor}
      </div>
    </div>
  );
}

/* ─── Main Risk Intelligence View ────────────── */
export default function RiskIntelligence() {
  const [corridors, setCorridors] = useState<LiveCorridor[]>([]);
  const [feed, setFeed] = useState<LiveSignal[]>([]);
  const [isLive, setIsLive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [selectedCorridor, setSelectedCorridor] = useState(0);
  const [sourceFilter, setSourceFilter] = useState<string>('ALL');
  const [filterOpen, setFilterOpen] = useState(false);

  const refresh = async () => {
    setLoading(true);
    const { data, is_live } = await loadCorridors();
    setCorridors(data);
    setFeed(feedFromCorridors(data));
    setIsLive(is_live);
    setSelectedCorridor(0);
    setLoading(false);
  };

  useEffect(() => { refresh(); }, []);

  const selected = corridors[selectedCorridor];

  const filteredSignals = feed.filter(s => sourceFilter === 'ALL' || s.source === sourceFilter);
  const sources = ['ALL', ...Array.from(new Set(feed.map(s => s.source)))];

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1600, margin: '0 auto' }}>

      {/* Page Header */}
      <div style={{ marginBottom: 28, paddingBottom: 24, borderBottom: '1px solid rgba(0,0,0,0.07)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{
              fontSize: 10, fontWeight: 700, letterSpacing: '0.12em',
              textTransform: 'uppercase', color: '#94a3b8', marginBottom: 6,
            }}>
              Intelligence Module
            </div>
            <h1 style={{
              fontSize: 28, fontWeight: 800, color: '#0f172a',
              fontFamily: 'var(--font-display)', letterSpacing: '-0.02em',
              lineHeight: 1.15, marginBottom: 8,
            }}>
              Risk Intelligence Center
            </h1>
            <p style={{ fontSize: 14, color: '#64748b', lineHeight: 1.7, maxWidth: 600, fontWeight: 500 }}>
              Corridor risk scored by the backend from geopolitical events (GDELT), with the reasoning
              trail and contributing signals the model actually used.
            </p>
          </div>

          {/* Live/offline + alert counts + refresh */}
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span className={`badge ${isLive ? 'badge-low' : 'badge-elevated'}`} style={{ padding: '6px 10px' }}>
              {isLive ? <><Wifi style={{ width: 12, height: 12 }} /> Live backend</> : <><WifiOff style={{ width: 12, height: 12 }} /> Offline (sample)</>}
            </span>
            {['critical', 'high', 'elevated'].map(level => {
              const count = feed.filter(s => s.color === level).length;
              if (count === 0) return null;
              return (
                <div key={level} className={`badge badge-${level}`} style={{ padding: '6px 10px' }}>
                  {count} {level}
                </div>
              );
            })}
            <button onClick={refresh} disabled={loading} className="btn-secondary" style={{ padding: '6px 12px' }}>
              <RefreshCw className={loading ? 'animate-spin' : ''} style={{ width: 13, height: 13 }} /> Refresh
            </button>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>

        {/* ─── Left: Corridor Cards ─── */}
        <div>
          <div style={{
            fontSize: 10, fontWeight: 700, letterSpacing: '0.1em',
            textTransform: 'uppercase', color: '#94a3b8', marginBottom: 12,
          }}>
            Corridor Risk Scores ({corridors.length} monitored)
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {corridors.map((data, i) => (
              <CorridorCard
                key={data.corridor_id}
                data={data}
                isSelected={selectedCorridor === i}
                onClick={() => setSelectedCorridor(i)}
              />
            ))}
            {loading && corridors.length === 0 && (
              [1, 2, 3, 4].map(i => <div key={i} style={{ height: 150, background: '#f1f5f9', borderRadius: 12, opacity: 0.6 }} />)
            )}
          </div>

          {/* Reasoning Trail for Selected Corridor */}
          {selected && (
            <div style={{ marginTop: 16 }}>
              <ReasoningTrail
                signals={selected.signals}
                reasoning={selected.reasoning_trail}
                model={selected.model}
                confidence={selected.confidence}
                as_of={selected.as_of}
                defaultOpen={true}
              />
            </div>
          )}
        </div>

        {/* ─── Right: Live Signal Feed ─── */}
        <div>
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            marginBottom: 12,
          }}>
            <div style={{
              fontSize: 10, fontWeight: 700, letterSpacing: '0.1em',
              textTransform: 'uppercase', color: '#94a3b8',
            }}>
              Intelligence Feed ({filteredSignals.length})
            </div>

            {/* Filter */}
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => setFilterOpen(!filterOpen)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  padding: '5px 10px', borderRadius: 8,
                  background: '#fff', border: '1px solid rgba(0,0,0,0.1)',
                  fontSize: 11, fontWeight: 600, color: '#64748b',
                  cursor: 'pointer',
                }}
              >
                <Filter style={{ width: 12, height: 12 }} />
                {sourceFilter === 'ALL' ? 'All Sources' : sourceFilter}
                {filterOpen ? <ChevronUp style={{ width: 12, height: 12 }} /> : <ChevronDown style={{ width: 12, height: 12 }} />}
              </button>
              {filterOpen && (
                <div style={{
                  position: 'absolute', top: '100%', right: 0, marginTop: 4,
                  background: '#fff', borderRadius: 10, border: '1px solid rgba(0,0,0,0.1)',
                  boxShadow: '0 8px 32px rgba(0,0,0,0.12)', overflow: 'hidden', zIndex: 20,
                  minWidth: 140,
                }}>
                  {sources.map(s => (
                    <button
                      key={s}
                      onClick={() => { setSourceFilter(s); setFilterOpen(false); }}
                      style={{
                        display: 'block', width: '100%', padding: '8px 14px',
                        background: sourceFilter === s ? 'rgba(59,130,246,0.06)' : 'transparent',
                        border: 'none', cursor: 'pointer', textAlign: 'left',
                        fontSize: 12, fontWeight: sourceFilter === s ? 700 : 500,
                        color: sourceFilter === s ? '#2563eb' : '#334155',
                      }}
                    >{s}</button>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="card" style={{ maxHeight: 'calc(100vh - 260px)', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div className="card-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{
                  fontSize: 12, fontWeight: 700, letterSpacing: '0.06em',
                  textTransform: 'uppercase', color: '#0f172a',
                }}>Scoring Events</span>
              </div>
              <span className={`badge ${isLive ? 'badge-low' : 'badge-elevated'}`}>
                {isLive ? 'From backend' : 'Sample feed'}
              </span>
            </div>

            <div style={{ flex: 1, overflowY: 'auto' }}>
              {filteredSignals.map((signal, i) => (
                <SignalItem key={i} signal={signal} />
              ))}
              {filteredSignals.length === 0 && (
                <div style={{ padding: 40, textAlign: 'center', color: '#94a3b8', fontSize: 13 }}>
                  {loading ? 'Loading events…' : 'No signals match the selected filter.'}
                </div>
              )}
            </div>

            {/* Methodology callout */}
            <div style={{
              padding: '14px 20px', borderTop: '1px solid rgba(0,0,0,0.06)',
              background: 'rgba(59,130,246,0.04)',
              display: 'flex', gap: 10, alignItems: 'flex-start',
            }}>
              <AlertCircle style={{ width: 16, height: 16, color: '#3b82f6', flexShrink: 0, marginTop: 2 }} />
              <div style={{ fontSize: 12, color: '#64748b', lineHeight: 1.6, fontWeight: 500 }}>
                <strong style={{ color: '#2563eb', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                  How this is scored:
                </strong>{' '}
                Each corridor starts from a baseline, then recency-weighted event pressure and conflict-tone
                adjustment are added. The events above are exactly what fed the displayed score — open a corridor&apos;s
                reasoning trail to see the full breakdown.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
