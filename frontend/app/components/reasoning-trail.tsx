"use client";

import { useState } from 'react';
import { ChevronDown, ChevronUp, Cpu, Info } from 'lucide-react';
import type { RiskSignal } from '../lib/mock-data';

interface ReasoningTrailProps {
  signals: RiskSignal[];
  reasoning: string;
  model: string;
  confidence: number;
  as_of: string;
  defaultOpen?: boolean;
  variant?: 'light' | 'dark';
}

const SOURCE_COLORS: Record<string, string> = {
  GDELT: '#f97316',
  aisstream: '#3b82f6',
  OFAC: '#ef4444',
  EIA: '#22c55e',
};

const TYPE_LABELS: Record<string, string> = {
  geo_event: 'Geopolitical',
  ais_anomaly: 'AIS Anomaly',
  sanctions: 'Sanctions',
  price: 'Price Signal',
};

export default function ReasoningTrail({
  signals, reasoning, model, confidence, as_of, defaultOpen = false, variant = 'light'
}: ReasoningTrailProps) {
  const [open, setOpen] = useState(defaultOpen);
  const isDark = variant === 'dark';

  const totalWeight = signals.reduce((sum, s) => sum + s.weight, 0);

  return (
    <div style={{
      borderRadius: 12,
      border: `1px solid ${isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.07)'}`,
      background: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(248,250,252,0.8)',
      overflow: 'hidden',
      transition: 'all 0.3s ease',
    }}>
      {/* Toggle Header */}
      <button
        onClick={() => setOpen(!open)}
        style={{
          width: '100%', padding: '12px 16px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          background: 'none', border: 'none', cursor: 'pointer',
          color: isDark ? 'rgba(255,255,255,0.6)' : '#64748b',
          fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase',
          textAlign: 'left',
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Info style={{ width: 14, height: 14 }} />
          Reasoning Trail
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {/* Confidence badge */}
          <span style={{
            fontSize: 9, fontWeight: 800, padding: '2px 6px', borderRadius: 4,
            background: confidence > 0.8 ? 'rgba(34,197,94,0.1)' : confidence > 0.6 ? 'rgba(234,179,8,0.1)' : 'rgba(239,68,68,0.1)',
            color: confidence > 0.8 ? '#22c55e' : confidence > 0.6 ? '#eab308' : '#ef4444',
            border: `1px solid ${confidence > 0.8 ? 'rgba(34,197,94,0.2)' : confidence > 0.6 ? 'rgba(234,179,8,0.2)' : 'rgba(239,68,68,0.2)'}`,
          }}>
            {(confidence * 100).toFixed(0)}% CONF
          </span>
          {open ? <ChevronUp style={{ width: 14, height: 14 }} /> : <ChevronDown style={{ width: 14, height: 14 }} />}
        </span>
      </button>

      {open && (
        <div style={{ padding: '0 16px 16px' }}>
          {/* Signal Weight Breakdown — Stacked Bar */}
          <div style={{ marginBottom: 16 }}>
            <div style={{
              fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase',
              color: isDark ? 'rgba(255,255,255,0.4)' : '#94a3b8', marginBottom: 8,
            }}>
              Signal Weights
            </div>
            <div style={{ display: 'flex', height: 8, borderRadius: 4, overflow: 'hidden', gap: 2 }}>
              {signals.map((s, i) => (
                <div key={i} style={{
                  width: `${(s.weight / totalWeight) * 100}%`,
                  background: SOURCE_COLORS[s.source] || '#64748b',
                  borderRadius: 2,
                  transition: 'width 0.5s ease',
                }} />
              ))}
            </div>
            <div style={{ display: 'flex', gap: 12, marginTop: 8, flexWrap: 'wrap' }}>
              {signals.map((s, i) => (
                <span key={i} style={{
                  display: 'flex', alignItems: 'center', gap: 4,
                  fontSize: 10, fontWeight: 600,
                  color: isDark ? 'rgba(255,255,255,0.6)' : '#64748b',
                }}>
                  <span style={{
                    width: 6, height: 6, borderRadius: 2,
                    background: SOURCE_COLORS[s.source] || '#64748b',
                    display: 'block',
                  }} />
                  {TYPE_LABELS[s.type] || s.type} ({(s.weight * 100).toFixed(0)}%)
                </span>
              ))}
            </div>
          </div>

          {/* Signal Details */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
            {signals.map((s, i) => (
              <div key={i} style={{
                padding: '10px 12px', borderRadius: 8,
                background: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
                borderLeft: `3px solid ${SOURCE_COLORS[s.source] || '#64748b'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{
                    fontSize: 9, fontWeight: 800, letterSpacing: '0.08em', textTransform: 'uppercase',
                    color: SOURCE_COLORS[s.source] || '#64748b',
                  }}>
                    {s.source} · {TYPE_LABELS[s.type] || s.type}
                  </span>
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
                    color: isDark ? 'rgba(255,255,255,0.5)' : '#94a3b8',
                  }}>
                    w={s.weight.toFixed(1)}
                  </span>
                </div>
                <p style={{
                  fontSize: 12, lineHeight: 1.5, margin: 0,
                  color: isDark ? 'rgba(255,255,255,0.7)' : '#334155',
                  fontWeight: 500,
                }}>
                  {s.detail}
                </p>
              </div>
            ))}
          </div>

          {/* Reasoning Text */}
          <div style={{
            padding: '14px 16px', borderRadius: 10,
            background: isDark ? 'rgba(59,130,246,0.06)' : 'rgba(59,130,246,0.04)',
            border: `1px solid ${isDark ? 'rgba(59,130,246,0.15)' : 'rgba(59,130,246,0.12)'}`,
            marginBottom: 12,
          }}>
            <p style={{
              fontSize: 13, lineHeight: 1.7, margin: 0,
              color: isDark ? 'rgba(255,255,255,0.8)' : '#1e293b',
              fontWeight: 500,
            }}>
              {reasoning}
            </p>
          </div>

          {/* Footer: Model + Timestamp */}
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            fontSize: 10, color: isDark ? 'rgba(255,255,255,0.35)' : '#94a3b8',
            fontFamily: 'var(--font-mono)', fontWeight: 600,
          }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <Cpu style={{ width: 11, height: 11 }} />
              {model}
            </span>
            <span>
              {new Date(as_of).toLocaleTimeString('en-IN', { hour12: false })} IST
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
