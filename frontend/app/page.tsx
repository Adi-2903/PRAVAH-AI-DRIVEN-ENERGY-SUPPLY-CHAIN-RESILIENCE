"use client";

import { useState, useEffect, useCallback } from 'react';
import {
  LayoutDashboard, ShieldAlert, Activity, Briefcase, Shield,
  Globe, Lock, TrendingUp, ChevronRight, Eye, Users, ChevronDown,
  FileText, RefreshCw, Printer, FileDown,
} from 'lucide-react';
import Dashboard from './dashboard';
import ScenarioSimulator from './simulator';
import SPROptimizer from './spr';
import ProcurementModule from './procurement';
import RiskIntelligence from './risk-intelligence';
import CitizenView from './citizen-view';
import PolicyMaker from './policy-maker';
import DigitalTwin from './digital-twin';
import { printReport, exportToPDF } from './lib/export';
import { CORRIDOR_RISK_DATA, MOCK_RISK_SCORE } from './lib/mock-data';

type ViewTier = 'citizen' | 'analyst' | 'policy';

const TABS = [
  { id: 'dashboard',    label: 'Command Center',     icon: LayoutDashboard },
  { id: 'risk',         label: 'Risk Intelligence',  icon: ShieldAlert },
  { id: 'simulator',    label: 'Scenario Modeller',  icon: Activity },
  { id: 'procurement',  label: 'Procurement',        icon: Briefcase },
  { id: 'spr',          label: 'Strategic Reserves', icon: Shield },
  { id: 'policy',       label: 'Policy Maker',       icon: FileText, policyOnly: true },
  { id: 'twin',         label: 'Digital Twin',       icon: Globe },
];

// Live ticker — values drift slightly every 10 s to simulate live feed
const BASE_TICKERS = [
  { sym: 'BRENT',     base: 84.12, prefix: '$',  suffix: '/bbl', decimals: 2 },
  { sym: 'WTI',       base: 80.55, prefix: '$',  suffix: '/bbl', decimals: 2 },
  { sym: 'USD/INR',   base: 83.42, prefix: '₹',  suffix: '',     decimals: 2 },
  { sym: 'INDIA-IMP', base: 81.04, prefix: '$',  suffix: '/bbl', decimals: 2 },
  { sym: 'NAT-GAS',   base: 2.81,  prefix: '$',  suffix: '/mmbtu', decimals: 2 },
  { sym: 'DUBAI',     base: 82.90, prefix: '$',  suffix: '/bbl', decimals: 2 },
  { sym: 'OMAN',      base: 83.15, prefix: '$',  suffix: '/bbl', decimals: 2 },
];

function useLiveTicker() {
  const [tickers, setTickers] = useState(BASE_TICKERS.map(t => ({ ...t, val: t.base, chg: 0, up: true })));
  useEffect(() => {
    const tick = () => {
      setTickers(prev => prev.map(t => {
        const delta = (Math.random() - 0.49) * t.base * 0.004;
        const newVal = Math.max(t.base * 0.8, t.val + delta);
        const chg = ((newVal - t.base) / t.base) * 100;
        return { ...t, val: newVal, chg, up: chg >= 0 };
      }));
    };
    const id = setInterval(tick, 8000);
    return () => clearInterval(id);
  }, []);
  return tickers;
}

const TIER_CONFIG = {
  citizen: { label: 'Citizen',       icon: Eye,    color: '#22c55e', desc: 'Quick risk overview' },
  analyst: { label: 'Analyst',       icon: Users,  color: '#3b82f6', desc: 'Deep analysis tools' },
  policy:  { label: 'Policy Maker',  icon: Shield, color: '#8b5cf6', desc: 'Strategic planning' },
};

function TierSwitcher({ tier, onSwitch }: { tier: ViewTier; onSwitch: (t: ViewTier) => void }) {
  const [open, setOpen] = useState(false);
  const cfg = TIER_CONFIG[tier];
  const Icon = cfg.icon;
  return (
    <div style={{ position: 'relative' }}>
      <button onClick={() => setOpen(!open)} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 12px', borderRadius: 8, background: `${cfg.color}12`, border: `1px solid ${cfg.color}30`, fontSize: 11, fontWeight: 700, color: cfg.color, cursor: 'pointer', letterSpacing: '0.04em' }}>
        <Icon style={{ width: 13, height: 13 }} />{cfg.label} View<ChevronDown style={{ width: 12, height: 12, opacity: 0.6 }} />
      </button>
      {open && (
        <div style={{ position: 'absolute', top: '100%', right: 0, marginTop: 6, background: '#fff', borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)', boxShadow: '0 12px 40px rgba(0,0,0,0.15)', overflow: 'hidden', zIndex: 50, minWidth: 200 }}>
          {(Object.keys(TIER_CONFIG) as ViewTier[]).map(t => {
            const tc = TIER_CONFIG[t]; const TIcon = tc.icon; const isActive = t === tier;
            return (
              <button key={t} onClick={() => { onSwitch(t); setOpen(false); }} style={{ display: 'flex', alignItems: 'center', gap: 10, width: '100%', padding: '12px 16px', background: isActive ? `${tc.color}08` : 'transparent', border: 'none', cursor: 'pointer', textAlign: 'left', borderBottom: '1px solid rgba(0,0,0,0.04)' }}>
                <div style={{ width: 28, height: 28, borderRadius: 8, background: `${tc.color}12`, border: `1px solid ${tc.color}25`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <TIcon style={{ width: 14, height: 14, color: tc.color }} />
                </div>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: isActive ? tc.color : '#0f172a' }}>{tc.label}</div>
                  <div style={{ fontSize: 10, color: '#94a3b8', fontWeight: 500 }}>{tc.desc}</div>
                </div>
                {isActive && <div style={{ marginLeft: 'auto', width: 6, height: 6, borderRadius: '50%', background: tc.color }} />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

const riskData = CORRIDOR_RISK_DATA.map(c => ({ name: c.name, short: c.short, score: c.score, trend: c.trend, delta: c.delta, vol: c.volatility, barrels: c.barrels }));

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [viewTier, setViewTier] = useState<ViewTier>('citizen');
  const [time, setTime] = useState('');
  const [riskScore, setRiskScore] = useState(74);
  const tickers = useLiveTicker();

  // Live clock
  useEffect(() => {
    const u = () => setTime(new Date().toLocaleTimeString('en-IN', { hour12: false }));
    u(); const t = setInterval(u, 1000); return () => clearInterval(t);
  }, []);

  // Risk score drifts slightly to simulate live updates
  useEffect(() => {
    const id = setInterval(() => {
      setRiskScore(prev => Math.min(99, Math.max(60, prev + Math.round((Math.random() - 0.45) * 2))));
    }, 15000);
    return () => clearInterval(id);
  }, []);

  // When switching to policy tier, navigate to policy tab
  const handleTierSwitch = (t: ViewTier) => {
    setViewTier(t);
    if (t === 'policy') setActiveTab('policy');
    else if (activeTab === 'policy') setActiveTab('dashboard');
  };

  const handleExportReport = useCallback(async () => {
    await exportToPDF(
      'Situation Report',
      [
        { heading: 'Composite Risk Index', content: `Current score: ${riskScore}/100 (+12 pts vs 7-day average). Alert Level: 3 — Elevated. Primary driver: Strait of Hormuz corridor risk at 82/100 due to Iranian naval activity and AIS dark-shipping anomalies.` },
        { heading: 'Key Indicators', content: `Import Dependency: 88% of crude sourced from imports. Hormuz Transit: 42% of Indian crude imports. SPR Cover: 9.5 days (vs IEA 90-day benchmark). Brent Crude: $${tickers[0]?.val?.toFixed(2) ?? '84.12'}/bbl.` },
        { heading: 'Active Alerts', content: `CRITICAL: Iran seizes second tanker in Hormuz within 48h; US Fifth Fleet raises posture. HIGH: Anti-ship missile fired near Bab-el-Mandeb transit zone. ELEVATED: Shipping congestion at South African bunkering ports due to diversion flows.` },
      ],
      {
        headers: ['Corridor', 'Risk Score', '24h Change', 'Volatility', 'Throughput'],
        rows: riskData.map(r => [r.name, r.score.toFixed(1), r.delta, r.vol, r.barrels]),
      },
      MOCK_RISK_SCORE.reasoning_trail
    );
  }, [riskScore, tickers]);

  if (viewTier === 'citizen') {
    return <CitizenView onGoDeeper={() => { setViewTier('analyst'); setActiveTab('dashboard'); }} />;
  }

  const visibleTabs = TABS.filter(t => !t.policyOnly || viewTier === 'policy');

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden', background: '#f0f2f7' }}>

      {/* ─── LEFT SIDEBAR ─── */}
      <aside style={{ width: 256, background: 'var(--sidebar-bg)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', borderRight: '1px solid rgba(255,255,255,0.06)', flexShrink: 0, userSelect: 'none', position: 'relative', zIndex: 10 }}>
        <div style={{ position: 'absolute', inset: 0, opacity: 0.025, pointerEvents: 'none', backgroundImage: 'radial-gradient(circle, #fff 1px, transparent 1px)', backgroundSize: '20px 20px' }} />
        <div style={{ position: 'relative' }}>
          {/* Logo */}
          <div style={{ padding: '24px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{ width: 42, height: 42, borderRadius: 12, background: 'linear-gradient(135deg, #2563eb, #1d4ed8)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontSize: 20, fontWeight: 900, fontFamily: 'var(--font-display)', boxShadow: '0 4px 16px rgba(37,99,235,0.4)', flexShrink: 0 }}>P</div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 800, letterSpacing: '0.14em', color: '#f8fafc', lineHeight: 1.1 }}>PRAVAH</div>
              <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'rgba(148,163,184,0.7)', marginTop: 4 }}>Energy Supply Resilience</div>
            </div>
          </div>

          {/* Live status pill */}
          <div style={{ padding: '12px 20px', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '7px 12px', borderRadius: 8, background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.2)' }}>
              <span className="pulse-dot" style={{ width: 7, height: 7, borderRadius: '50%', background: '#ef4444', display: 'block', flexShrink: 0 }} />
              <span style={{ fontSize: 10, fontWeight: 700, color: '#fca5a5', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Alert Level 3 · Elevated</span>
            </div>
          </div>

          {/* Navigation */}
          <div style={{ padding: '20px 12px' }}>
            <div className="label-caps" style={{ padding: '0 10px', marginBottom: 10 }}>Modules</div>
            <nav style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {visibleTabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`nav-item ${isActive ? 'active' : ''}`}>
                    <Icon className="nav-icon" style={{ width: 16, height: 16, flexShrink: 0, color: isActive ? (tab.id === 'policy' ? '#c4b5fd' : '#60a5fa') : 'rgba(148,163,184,0.6)', transition: 'color 0.2s' }} />
                    <span>{tab.label}</span>
                    {tab.id === 'policy' && (
                      <span style={{ marginLeft: 'auto', fontSize: 8, fontWeight: 800, padding: '2px 6px', borderRadius: 4, background: 'rgba(139,92,246,0.25)', color: '#c4b5fd', letterSpacing: '0.06em' }}>NEW</span>
                    )}
                    {tab.id === 'simulator' && activeTab !== 'simulator' && (
                      <span className="pulse-dot-blue" style={{ marginLeft: 'auto', width: 7, height: 7, borderRadius: '50%', background: '#3b82f6', display: 'block' }} />
                    )}
                  </button>
                );
              })}
            </nav>          
            {/* Composite Risk Index widget — live */}
            <div style={{ margin: '4px 12px', padding: '14px 16px', borderRadius: 12, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
              <div style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'rgba(148,163,184,0.6)', marginBottom: 10 }}>Composite Risk Index</div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, marginBottom: 8 }}>
                <span style={{ fontSize: 30, fontWeight: 800, color: riskScore > 70 ? '#fbbf24' : '#22c55e', fontFamily: 'var(--font-mono)', transition: 'color 0.5s', lineHeight: 1 }}>{riskScore}</span>
                <span style={{ fontSize: 12, color: 'rgba(148,163,184,0.5)', fontWeight: 600 }}>/100</span>
              </div>
              <div style={{ height: 4, borderRadius: 4, background: 'rgba(255,255,255,0.07)', overflow: 'hidden', marginBottom: 6 }}>
                <div style={{ height: '100%', width: `${riskScore}%`, borderRadius: 4, background: riskScore > 70 ? 'linear-gradient(90deg, #eab308, #ef4444)' : '#22c55e', transition: 'width 1s ease' }} />
              </div>
              <div style={{ fontSize: 9, color: 'rgba(148,163,184,0.45)', fontWeight: 600 }}>Live · auto-refreshes</div>
            </div>
          </div>

          {/* Export quick actions */}
          <div style={{ margin: '8px 12px', padding: '12px', borderRadius: 12, background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
            <div className="label-caps" style={{ marginBottom: 8 }}>Quick Export</div>
            <div style={{ display: 'flex', gap: 6 }}>
              <button onClick={handleExportReport} title="Export PDF Report" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4, padding: '7px 6px', borderRadius: 8, background: 'rgba(59,130,246,0.12)', border: '1px solid rgba(59,130,246,0.2)', color: '#93c5fd', fontSize: 10, fontWeight: 700, cursor: 'pointer', letterSpacing: '0.04em' }}>
                <FileDown style={{ width: 11, height: 11 }} /> PDF
              </button>
              <button onClick={() => printReport('Situation Report')} title="Print Report" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4, padding: '7px 6px', borderRadius: 8, background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#94a3b8', fontSize: 10, fontWeight: 700, cursor: 'pointer', letterSpacing: '0.04em' }}>
                <Printer style={{ width: 11, height: 11 }} /> Print
              </button>
            </div>
          </div>
        </div>

        {/* Bottom classification */}
        <div style={{ padding: '16px 20px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
          <div className="label-caps" style={{ marginBottom: 4 }}>Classification</div>
          <div style={{ fontSize: 11, color: 'rgba(100,116,139,0.7)', lineHeight: 1.5 }}>Prototype · Illustrative data<br />Not for operational use</div>
        </div>
      </aside>

      {/* ─── RIGHT WORKSPACE ─── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* Top Header */}
        <header style={{ background: 'rgba(255,255,255,0.95)', backdropFilter: 'blur(10px)', borderBottom: '1px solid rgba(0,0,0,0.07)', flexShrink: 0, zIndex: 5 }}>
          {/* Ministry bar */}
          <div style={{ height: 50, padding: '0 28px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 11, fontWeight: 600, color: '#94a3b8', letterSpacing: '0.05em' }}>
              <span style={{ color: '#0f172a', fontWeight: 800, letterSpacing: '0.14em', fontSize: 12 }}>PRAVAH</span>
              <span style={{ color: '#cbd5e1' }}>·</span>
              <span style={{ textTransform: 'uppercase', letterSpacing: '0.08em' }}>Energy Supply Chain Resilience · India</span>
              <span style={{ color: '#cbd5e1' }}>·</span>
              <span>Ministry of Petroleum &amp; Natural Gas</span>
              <span style={{ color: '#cbd5e1' }}>·</span>
              <span style={{ background: 'rgba(59,130,246,0.08)', color: '#2563eb', border: '1px solid rgba(59,130,246,0.2)', borderRadius: 6, padding: '2px 8px', fontSize: 9, fontWeight: 800, letterSpacing: '0.1em', textTransform: 'uppercase' }}>Prototype Build</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <TierSwitcher tier={viewTier} onSwitch={handleTierSwitch} />
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600, color: '#64748b', background: '#f8fafc', padding: '5px 12px', borderRadius: 8, border: '1px solid rgba(0,0,0,0.07)', letterSpacing: '0.05em' }}>
                {time} IST
              </div>
            </div>
          </div>

          {/* Alert bar with live ticker — two zones: left static info, right scrolling ticker */}
          <div className="alert-bar-critical" style={{ height: 38, padding: '0 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
            {/* Left: critical status + key metrics */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: 11, fontWeight: 700, color: 'white', letterSpacing: '0.04em', flexShrink: 0, whiteSpace: 'nowrap' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#fff', display: 'inline-block', animation: 'pulseDot 1.5s ease-in-out infinite', flexShrink: 0 }} />
                <span>ALERT L3</span>
              </span>
              <span style={{ color: 'rgba(255,255,255,0.35)' }}>|</span>
              <span>CRI: <span style={{ fontFamily: 'var(--font-mono)', color: '#fde68a' }}>{riskScore}/100</span></span>
              <span style={{ color: 'rgba(255,255,255,0.35)' }}>|</span>
              <span>Brent: <span style={{ fontFamily: 'var(--font-mono)', color: tickers[0]?.up ? '#86efac' : '#fca5a5' }}>${tickers[0]?.val?.toFixed(2) ?? '84.12'} {tickers[0]?.up ? '▲' : '▼'}</span></span>
            </div>
            {/* Right: scrolling ticker strip */}
            <div style={{ flex: 1, overflow: 'hidden', maxWidth: 560, maskImage: 'linear-gradient(90deg, transparent, black 8%, black 92%, transparent)' }}>
              <div className="ticker-track" style={{ display: 'flex', gap: 28, whiteSpace: 'nowrap' }}>
                {[...tickers, ...tickers].map((t, i) => (
                  <span key={i} style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'rgba(255,255,255,0.8)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                    <span style={{ color: 'rgba(255,255,255,0.45)', fontWeight: 700, fontSize: 9 }}>{t.sym}</span>
                    <span>{t.prefix}{t.val?.toFixed(t.decimals)}</span>
                    <span style={{ color: t.up ? '#86efac' : '#fca5a5', fontSize: 9 }}>{t.up ? '+' : ''}{t.chg?.toFixed(2)}%</span>
                  </span>
                ))}
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="fade-in" key={activeTab} style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden', background: '#f0f2f7' }}>
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
