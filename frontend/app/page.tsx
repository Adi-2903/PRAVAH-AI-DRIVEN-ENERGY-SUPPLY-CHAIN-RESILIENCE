"use client";

import { useState, useEffect } from 'react';
import {
  LayoutDashboard,
  ShieldAlert,
  Activity,
  Briefcase,
  Shield,
  Globe,
  TrendingUp,
  ChevronRight,
  Radio,
  Cpu,
  Eye,
  Users,
  ChevronDown,
  FileText,
} from 'lucide-react';
import Dashboard from './dashboard';
import ScenarioSimulator from './simulator';
import SPROptimizer from './spr';
import ProcurementModule from './procurement';
import RiskIntelligence from './risk-intelligence';
import CitizenView from './citizen-view';
import PolicyMaker from './policy-maker';
import DigitalTwin from './digital-twin';
import { alertLevelFor } from './lib/live-data';
import type { MarketData } from './lib/live-data';
import { useLiveData } from './lib/use-live-data';

type ViewTier = 'citizen' | 'analyst' | 'policy';

const TABS: { id: string; label: string; icon: typeof LayoutDashboard; disabled?: boolean; policyOnly?: boolean }[] = [
  { id: 'dashboard',    label: 'Command Center',     icon: LayoutDashboard },
  { id: 'risk',         label: 'Risk Intelligence',   icon: ShieldAlert },
  { id: 'simulator',    label: 'Scenario Modeller',   icon: Activity },
  { id: 'procurement',  label: 'Procurement',         icon: Briefcase },
  { id: 'spr',          label: 'Strategic Reserves',  icon: Shield },
  { id: 'policy',       label: 'Policy Maker',        icon: FileText, policyOnly: true },
  { id: 'twin',         label: 'Digital Twin',        icon: Globe },
];

// Ticker is built from the live /market response (no fabricated % changes —
// the backend does not provide day-over-day deltas, so none are shown).
function buildTicker(m: MarketData | null): { sym: string; val: string }[] {
  if (!m) return [];
  return [
    { sym: 'BRENT', val: `$${m.brent_usd.toFixed(2)}` },
    { sym: 'WTI', val: `$${m.wti_usd.toFixed(2)}` },
    { sym: 'DUBAI', val: `$${m.dubai_usd.toFixed(2)}` },
    { sym: 'OMAN', val: `$${m.oman_usd.toFixed(2)}` },
    { sym: 'USD/INR:', val: `${m.usd_inr.toFixed(2)}` },
    { sym: 'NAT-GAS', val: `$${m.nat_gas_usd.toFixed(2)}` },
  ];
}
}

const ALERT_LEVEL_NUM: Record<string, number> = { low: 1, elevated: 2, high: 3, critical: 4 };

const TIER_CONFIG = {
  citizen: { label: 'Citizen', icon: Eye, color: '#22c55e', desc: 'Quick risk overview' },
  analyst: { label: 'Analyst', icon: Users, color: '#3b82f6', desc: 'Deep analysis tools' },
  policy:  { label: 'Policy Maker', icon: Shield, color: '#8b5cf6', desc: 'Strategic planning' },
};

function TierSwitcher({ tier, onSwitch }: { tier: ViewTier; onSwitch: (t: ViewTier) => void }) {
  const [open, setOpen] = useState(false);
  const cfg = TIER_CONFIG[tier];
  const Icon = cfg.icon;

  return (
    <div style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '5px 12px', borderRadius: 8,
          background: `${cfg.color}12`, border: `1px solid ${cfg.color}30`,
          fontSize: 11, fontWeight: 700, color: cfg.color,
          cursor: 'pointer', letterSpacing: '0.04em',
        }}
      >
        <Icon style={{ width: 13, height: 13 }} />
        {cfg.label} View
        <ChevronDown style={{ width: 12, height: 12, opacity: 0.6 }} />
      </button>
      {open && (
        <div style={{
          position: 'absolute', top: '100%', right: 0, marginTop: 6,
          background: '#fff', borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)',
          boxShadow: '0 12px 40px rgba(0,0,0,0.15)', overflow: 'hidden', zIndex: 50,
          minWidth: 200,
        }}>
          {(Object.keys(TIER_CONFIG) as ViewTier[]).map(t => {
            const tc = TIER_CONFIG[t];
            const TIcon = tc.icon;
            const isActive = t === tier;
            return (
              <button
                key={t}
                onClick={() => { onSwitch(t); setOpen(false); }}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10, width: '100%',
                  padding: '12px 16px', background: isActive ? `${tc.color}08` : 'transparent',
                  border: 'none', cursor: 'pointer', textAlign: 'left',
                  borderBottom: '1px solid rgba(0,0,0,0.04)',
                }}
              >
                <div style={{
                  width: 28, height: 28, borderRadius: 8,
                  background: `${tc.color}12`, border: `1px solid ${tc.color}25`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <TIcon style={{ width: 14, height: 14, color: tc.color }} />
                </div>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: isActive ? tc.color : '#0f172a' }}>
                    {tc.label}
                  </div>
                  <div style={{ fontSize: 10, color: '#94a3b8', fontWeight: 500 }}>{tc.desc}</div>
                </div>
                {isActive && (
                  <div style={{
                    marginLeft: 'auto', width: 6, height: 6, borderRadius: '50%',
                    background: tc.color,
                  }} />
                )}
              </button>
            );
          })}
          <div style={{ padding: '8px 16px', background: '#f8fafc' }}>
            <div style={{ fontSize: 9, color: '#94a3b8', fontWeight: 600, lineHeight: 1.5 }}>
              Auth is stubbed for prototype demo.
              <br />No real login required.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [viewTier, setViewTier] = useState<ViewTier>('citizen');
  const [time, setTime] = useState('');
  const { market, compositeRisk: composite, marketLive, corridorsLive, refresh: liveRefresh, lastUpdated, error: liveError } = useLiveData();
  const isLive = marketLive && corridorsLive;

  // Switching to the Policy tier opens the Policy Maker tab; leaving it returns to the dashboard.
  const handleTierSwitch = (t: ViewTier) => {
    setViewTier(t);
    if (t === 'policy') setActiveTab('policy');
    else if (activeTab === 'policy') setActiveTab('dashboard');
  };

  useEffect(() => {
    const update = () => setTime(new Date().toLocaleTimeString('en-IN', { hour12: false }));
    update();
    const t = setInterval(update, 1000);
    return () => clearInterval(t);
  }, []);

  const compositeAlert = composite != null ? alertLevelFor(composite) : 'low';
  const alertNum = ALERT_LEVEL_NUM[compositeAlert] ?? 1;
  const ticker = buildTicker(market);

  // ─── Citizen View: Full-screen, no sidebar ───
  if (viewTier === 'citizen') {
    return (
      <CitizenView onGoDeeper={() => { setViewTier('analyst'); setActiveTab('dashboard'); }} />
    );
  }

  // ─── Analyst / Policy View: Full SPA shell ───
  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden', background: '#f0f2f7' }}>

      {/* ─── LEFT SIDEBAR ─── */}
      <aside style={{
        width: 256,
        background: 'var(--sidebar-bg)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        borderRight: '1px solid rgba(255,255,255,0.06)',
        flexShrink: 0,
        userSelect: 'none',
        position: 'relative',
        zIndex: 10,
      }}>
        {/* Subtle grid texture overlay */}
        <div style={{
          position: 'absolute', inset: 0, opacity: 0.025, pointerEvents: 'none',
          backgroundImage: 'radial-gradient(circle, #fff 1px, transparent 1px)',
          backgroundSize: '20px 20px',
        }} />

        <div style={{ position: 'relative' }}>
          {/* Logo */}
          <div style={{
            padding: '24px 20px',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
            display: 'flex',
            alignItems: 'center',
            gap: 14,
          }}>
            <div style={{
              width: 42,
              height: 42,
              borderRadius: 12,
              background: 'linear-gradient(135deg, #2563eb, #1d4ed8)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontSize: 20,
              fontWeight: 900,
              fontFamily: 'var(--font-display)',
              boxShadow: '0 4px 16px rgba(37,99,235,0.4)',
              flexShrink: 0,
            }}>
              P
            </div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 800, letterSpacing: '0.14em', color: '#f8fafc', lineHeight: 1.1 }}>
                PRAVAH
              </div>
              <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'rgba(148,163,184,0.7)', marginTop: 4 }}>
                Energy Supply Resilience
              </div>
            </div>
          </div>

          {/* Live status pill (derived from composite alert level) */}
          {(() => {
            const tone = compositeAlert === 'critical' || compositeAlert === 'high'
              ? { bg: 'rgba(239,68,68,0.12)', border: 'rgba(239,68,68,0.2)', dot: '#ef4444', text: '#fca5a5' }
              : compositeAlert === 'elevated'
                ? { bg: 'rgba(234,179,8,0.12)', border: 'rgba(234,179,8,0.2)', dot: '#eab308', text: '#fde68a' }
                : { bg: 'rgba(34,197,94,0.12)', border: 'rgba(34,197,94,0.2)', dot: '#22c55e', text: '#86efac' };
            return (
              <div style={{ padding: '12px 20px', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 8, padding: '7px 12px', borderRadius: 8,
                  background: tone.bg, border: `1px solid ${tone.border}`,
                }}>
                  <span className="pulse-dot" style={{ width: 7, height: 7, borderRadius: '50%', background: tone.dot, display: 'block', flexShrink: 0 }} />
                  <span style={{ fontSize: 10, fontWeight: 700, color: tone.text, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                    Alert Level {alertNum} · {compositeAlert}
                  </span>
                </div>
              </div>
            );
          })()}

          {/* Navigation */}
          <div style={{ padding: '20px 12px' }}>
            <div className="label-caps" style={{ padding: '0 10px', marginBottom: 10 }}>
              Modules
            </div>
            <nav style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {TABS.filter((tab) => !tab.policyOnly || viewTier === 'policy').map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => !tab.disabled && setActiveTab(tab.id)}
                    disabled={tab.disabled}
                    className={`nav-item ${isActive ? 'active' : ''} ${tab.disabled ? 'disabled' : ''}`}
                  >
                    <Icon
                      className="nav-icon"
                      style={{
                        width: 16, height: 16, flexShrink: 0,
                        color: isActive ? '#60a5fa' : 'rgba(148,163,184,0.6)',
                        transition: 'color 0.2s',
                      }}
                    />
                    <span>{tab.label}</span>
                    {tab.id === 'simulator' && activeTab !== 'simulator' && (
                      <span className="pulse-dot-blue" style={{
                        marginLeft: 'auto',
                        width: 7, height: 7, borderRadius: '50%',
                        background: '#3b82f6', display: 'block',
                      }} />
                    )}
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Composite Risk Index widget (live, throughput-weighted) */}
          {(() => {
            const val = composite ?? 0;
            const barColor = val > 70 ? '#ef4444' : val > 45 ? '#f97316' : val > 30 ? '#eab308' : '#22c55e';
            return (
              <div style={{ margin: '4px 12px', padding: '16px', borderRadius: 12, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
                <div className="label-caps" style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
                  <span>Composite Risk Index</span>
                  <span style={{ color: isLive ? '#22c55e' : 'rgba(148,163,184,0.6)' }}>{isLive ? 'LIVE' : 'OFFLINE'}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginBottom: 10 }}>
                  <span style={{ fontSize: 28, fontWeight: 800, color: barColor, fontFamily: 'var(--font-mono)' }}>{composite ?? '—'}</span>
                  <span style={{ fontSize: 13, color: 'rgba(148,163,184,0.6)', fontWeight: 600 }}>/100</span>
                </div>
                <div style={{ height: 5, borderRadius: 5, background: 'rgba(255,255,255,0.07)', overflow: 'hidden', marginBottom: 8 }}>
                  <div style={{ height: '100%', width: `${val}%`, borderRadius: 5, background: `linear-gradient(90deg, #eab308, ${barColor})`, transition: 'width 1s ease' }} />
                </div>
                <div style={{ fontSize: 10, color: 'rgba(148,163,184,0.5)', fontWeight: 600, textTransform: 'capitalize' }}>Alert level: {compositeAlert}</div>
              </div>
            );
          })()}
        </div>

        {/* Bottom classification */}
        <div style={{ padding: '16px 20px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
          <div className="label-caps" style={{ marginBottom: 4 }}>Classification</div>
          <div style={{ fontSize: 11, color: 'rgba(100,116,139,0.7)', lineHeight: 1.5 }}>
            Prototype · Illustrative data<br />Not for operational use
          </div>
        </div>
      </aside>

      {/* ─── RIGHT WORKSPACE ─── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* Top Header */}
        <header style={{
          background: 'rgba(255,255,255,0.95)',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid rgba(0,0,0,0.07)',
          flexShrink: 0,
          zIndex: 5,
        }}>
          {/* Ministry bar */}
          <div style={{
            height: 50,
            padding: '0 28px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 11, fontWeight: 600, color: '#94a3b8', letterSpacing: '0.05em' }}>
              <span style={{ color: '#0f172a', fontWeight: 800, letterSpacing: '0.14em', fontSize: 12 }}>PRAVAH</span>
              <span style={{ color: '#cbd5e1' }}>·</span>
              <span style={{ textTransform: 'uppercase', letterSpacing: '0.08em' }}>Energy Supply Chain Resilience · India</span>
              <span style={{ color: '#cbd5e1' }}>·</span>
              <span>Ministry of Petroleum &amp; Natural Gas</span>
              <span style={{ color: '#cbd5e1' }}>·</span>
              <span style={{
                background: 'rgba(59,130,246,0.08)',
                color: '#2563eb',
                border: '1px solid rgba(59,130,246,0.2)',
                borderRadius: 6,
                padding: '2px 8px',
                fontSize: 9,
                fontWeight: 800,
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
              }}>
                Prototype Build
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <TierSwitcher tier={viewTier} onSwitch={handleTierSwitch} />
              
              {/* Bloomberg-style HUD */}
              <div style={{
                display: 'flex', alignItems: 'center', gap: 16,
                background: '#f8fafc', padding: '6px 16px', borderRadius: 8,
                border: '1px solid rgba(0,0,0,0.07)', fontSize: 10, fontWeight: 700,
                color: '#64748b', letterSpacing: '0.04em', textTransform: 'uppercase'
              }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <span>Backend</span>
                  <span style={{ color: liveError ? '#ef4444' : '#10b981', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <span className={liveError ? '' : 'pulse-dot'} style={{ width: 6, height: 6, borderRadius: '50%', background: liveError ? '#ef4444' : '#10b981' }} />
                    {liveError ? 'ERROR' : 'HEALTHY'}
                  </span>
                </div>
                <div style={{ width: 1, height: 20, background: 'rgba(0,0,0,0.06)' }} />
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <span>Last Sync</span>
                  <span style={{ color: '#0f172a' }}>{lastUpdated ? new Date(lastUpdated).toLocaleTimeString('en-IN', { hour12: false }) : time}</span>
                </div>
                <div style={{ width: 1, height: 20, background: 'rgba(0,0,0,0.06)' }} />
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <span>Market</span>
                  <span style={{ color: marketLive ? '#10b981' : '#f59e0b' }}>{marketLive ? 'LIVE' : 'CACHED'}</span>
                </div>
                <div style={{ width: 1, height: 20, background: 'rgba(0,0,0,0.06)' }} />
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <span>Risk</span>
                  <span style={{ color: corridorsLive ? '#10b981' : '#f59e0b' }}>{corridorsLive ? 'LIVE' : 'CACHED'}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Alert bar (live composite + live Brent; no fabricated deltas) */}
          <div className={compositeAlert === 'critical' || compositeAlert === 'high' ? 'alert-bar-critical' : 'alert-bar-critical'} style={{
            height: 38,
            padding: '0 28px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: compositeAlert === 'critical' ? undefined
              : compositeAlert === 'high' ? 'linear-gradient(90deg,#dc2626,#b91c1c)'
              : compositeAlert === 'elevated' ? 'linear-gradient(90deg,#d97706,#b45309)'
              : 'linear-gradient(90deg,#16a34a,#15803d)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, fontSize: 11, fontWeight: 700, color: 'white', letterSpacing: '0.04em' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#fff', display: 'inline-block', animation: 'pulseDot 1.5s ease-in-out infinite' }} />
                ALERT LEVEL {alertNum} · {compositeAlert.toUpperCase()}
              </span>
              <span style={{ color: 'rgba(255,255,255,0.4)' }}>|</span>
              <span>
                Composite Risk Index:{' '}
                <span style={{ fontFamily: 'var(--font-mono)', color: '#fde68a', fontWeight: 800 }}>{composite ?? '—'}/100</span>
              </span>
              <span style={{ color: 'rgba(255,255,255,0.4)' }}>|</span>
              <span>
                Brent Crude Spot:{' '}
                <span style={{ fontFamily: 'var(--font-mono)', color: '#86efac', fontWeight: 800 }}>
                  {market ? `$${market.brent_usd.toFixed(2)}/bbl` : '—'}
                </span>
                <span style={{ color: 'rgba(255,255,255,0.55)', fontWeight: 600, marginLeft: 6 }}>· EIA ref</span>
              </span>
              {market && (
                <>
                  <span style={{ color: 'rgba(255,255,255,0.4)' }}>|</span>
                  <span>
                    USD/INR:{' '}
                    <span style={{ fontFamily: 'var(--font-mono)', color: '#86efac', fontWeight: 800 }}>{market.usd_inr.toFixed(2)}</span>
                    <span style={{ color: 'rgba(255,255,255,0.55)', fontWeight: 600, marginLeft: 6 }}>{market.is_live ? '· live' : '· ref'}</span>
                  </span>
                </>
              )}
            </div>

            {/* Ticker strip (live /market) */}
            {ticker.length > 0 && (
              <div style={{ overflow: 'hidden', maxWidth: 340, maskImage: 'linear-gradient(90deg, transparent, black 15%, black 85%, transparent)' }}>
                <div className="ticker-track" style={{ display: 'flex', gap: 32, whiteSpace: 'nowrap' }}>
                  {[...ticker, ...ticker].map((t, i) => (
                    <span key={i} style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'rgba(255,255,255,0.8)', fontWeight: 600 }}>
                      <span style={{ color: 'rgba(255,255,255,0.5)', fontWeight: 700 }}>{t.sym}</span>
                      {' '}{t.val}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </header>

        {/* Page content */}
        <main
          className="fade-in"
          key={activeTab}
          style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden', background: '#f0f2f7' }}
        >
          {activeTab === 'dashboard'   && <Dashboard onNavigate={setActiveTab} />}
          {activeTab === 'simulator'   && <ScenarioSimulator />}
          {activeTab === 'spr'         && <SPROptimizer />}
          {activeTab === 'risk'        && <RiskIntelligence />}
          {activeTab === 'procurement' && <ProcurementModule />}
          {activeTab === 'policy'      && <PolicyMaker />}
          {activeTab === 'twin'        && <DigitalTwin />}
        </main>
      </div>
    </div>
  );
}
