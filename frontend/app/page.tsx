"use client";

import { useState, useEffect } from 'react';
import {
  LayoutDashboard,
  ShieldAlert,
  Activity,
  Briefcase,
  Shield,
  Globe,
  Lock,
  TrendingUp,
  ChevronRight,
  Radio,
  Cpu,
} from 'lucide-react';
import Dashboard from './dashboard';
import ScenarioSimulator from './simulator';
import SPROptimizer from './spr';

const TABS = [
  { id: 'dashboard',    label: 'Command Center',     icon: LayoutDashboard },
  { id: 'risk',         label: 'Risk Intelligence',   icon: ShieldAlert },
  { id: 'simulator',    label: 'Scenario Modeller',   icon: Activity },
  { id: 'procurement',  label: 'Procurement',         icon: Briefcase },
  { id: 'spr',          label: 'Strategic Reserves',  icon: Shield },
  { id: 'twin',         label: 'Digital Twin',        icon: Globe, disabled: true },
];

const TICKER_ITEMS = [
  { sym: 'BRENT', val: '$84.12', chg: '+2.94%', up: true },
  { sym: 'WTI',   val: '$80.55', chg: '+2.39%', up: true },
  { sym: 'USD/INR', val: '₹83.42', chg: '-0.14%', up: false },
  { sym: 'INDIA-IMP', val: '$81.04', chg: '+2.17%', up: true },
  { sym: 'NAT-GAS', val: '$2.81', chg: '-1.06%', up: false },
  { sym: 'DUBAI', val: '$82.90', chg: '+2.60%', up: true },
  { sym: 'OMAN',  val: '$83.15', chg: '+2.40%', up: true },
];

function ComingSoon({ label }: { label: string }) {
  return (
    <div className="flex-1 flex items-center justify-center" style={{ background: '#f0f2f7', minHeight: 'calc(100vh - 142px)' }}>
      <div className="text-center p-14 bg-white rounded-2xl shadow-sm" style={{ border: '1px solid rgba(0,0,0,0.07)', maxWidth: 440 }}>
        <div className="mx-auto mb-6 w-16 h-16 rounded-2xl flex items-center justify-center" style={{ background: 'rgba(59,130,246,0.08)' }}>
          <Lock style={{ width: 28, height: 28, color: '#3b82f6' }} />
        </div>
        <div className="text-[10px] font-bold uppercase tracking-widest mb-3" style={{ color: '#94a3b8' }}>
          MODULE OFFLINE
        </div>
        <div className="text-2xl font-bold mb-3" style={{ color: '#0f172a', fontFamily: 'var(--font-display)' }}>
          {label}
        </div>
        <p className="text-sm leading-relaxed mb-6" style={{ color: '#64748b' }}>
          This geopolitical assessment module is currently locked or undergoing calibration for the next operational cycle.
        </p>
        <span className="badge badge-info">
          <Lock style={{ width: 10, height: 10 }} /> Secure Intel Feed
        </span>
      </div>
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [time, setTime] = useState('');

  useEffect(() => {
    const update = () => setTime(new Date().toLocaleTimeString('en-IN', { hour12: false }));
    update();
    const t = setInterval(update, 1000);
    return () => clearInterval(t);
  }, []);

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

          {/* Live status pill */}
          <div style={{ padding: '12px 20px', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '7px 12px',
              borderRadius: 8,
              background: 'rgba(239,68,68,0.12)',
              border: '1px solid rgba(239,68,68,0.2)',
            }}>
              <span className="pulse-dot" style={{
                width: 7, height: 7, borderRadius: '50%',
                background: '#ef4444', display: 'block', flexShrink: 0,
              }} />
              <span style={{ fontSize: 10, fontWeight: 700, color: '#fca5a5', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                Alert Level 3 · Elevated
              </span>
            </div>
          </div>

          {/* Navigation */}
          <div style={{ padding: '20px 12px' }}>
            <div className="label-caps" style={{ padding: '0 10px', marginBottom: 10 }}>
              Modules
            </div>
            <nav style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {TABS.map((tab) => {
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

          {/* Composite Risk Index widget */}
          <div style={{ margin: '4px 12px', padding: '16px', borderRadius: 12, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div className="label-caps" style={{ marginBottom: 8 }}>Composite Risk Index</div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginBottom: 10 }}>
              <span style={{ fontSize: 28, fontWeight: 800, color: '#fbbf24', fontFamily: 'var(--font-mono)' }}>74</span>
              <span style={{ fontSize: 13, color: 'rgba(148,163,184,0.6)', fontWeight: 600 }}>/100</span>
            </div>
            <div style={{ height: 5, borderRadius: 5, background: 'rgba(255,255,255,0.07)', overflow: 'hidden', marginBottom: 8 }}>
              <div style={{
                height: '100%', width: '74%', borderRadius: 5,
                background: 'linear-gradient(90deg, #eab308, #ef4444)',
                transition: 'width 1s ease',
              }} />
            </div>
            <div style={{ fontSize: 10, color: 'rgba(148,163,184,0.5)', fontWeight: 600 }}>+12 pts vs 7-day avg</div>
          </div>
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
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 12,
              fontWeight: 600,
              color: '#64748b',
              background: '#f8fafc',
              padding: '5px 12px',
              borderRadius: 8,
              border: '1px solid rgba(0,0,0,0.07)',
              letterSpacing: '0.05em',
            }}>
              {time} IST
            </div>
          </div>

          {/* Alert bar */}
          <div className="alert-bar-critical" style={{
            height: 38,
            padding: '0 28px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, fontSize: 11, fontWeight: 700, color: 'white', letterSpacing: '0.04em' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#fff', display: 'inline-block', animation: 'pulseDot 1.5s ease-in-out infinite' }} />
                ALERT LEVEL 3 · ELEVATED
              </span>
              <span style={{ color: 'rgba(255,255,255,0.4)' }}>|</span>
              <span>
                Composite Risk Index:{' '}
                <span style={{ fontFamily: 'var(--font-mono)', color: '#fde68a', fontWeight: 800 }}>74/100</span>
              </span>
              <span style={{ color: 'rgba(255,255,255,0.4)' }}>|</span>
              <span>
                Brent Crude Spot:{' '}
                <span style={{ fontFamily: 'var(--font-mono)', color: '#86efac', fontWeight: 800 }}>$84.12{' '}
                  <span style={{ color: '#4ade80' }}>↑ +2.94%</span>
                </span>
              </span>
            </div>

            {/* Ticker strip */}
            <div style={{ overflow: 'hidden', maxWidth: 340, maskImage: 'linear-gradient(90deg, transparent, black 15%, black 85%, transparent)' }}>
              <div className="ticker-track" style={{ display: 'flex', gap: 32, whiteSpace: 'nowrap' }}>
                {[...TICKER_ITEMS, ...TICKER_ITEMS].map((t, i) => (
                  <span key={i} style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'rgba(255,255,255,0.8)', fontWeight: 600 }}>
                    <span style={{ color: 'rgba(255,255,255,0.5)', fontWeight: 700 }}>{t.sym}</span>
                    {' '}{t.val}
                    {' '}
                    <span style={{ color: t.up ? '#86efac' : '#fca5a5' }}>{t.chg}</span>
                  </span>
                ))}
              </div>
            </div>
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
          {activeTab === 'risk'        && <ComingSoon label="Risk Intelligence Center" />}
          {activeTab === 'procurement' && <ComingSoon label="Procurement Module" />}
        </main>
      </div>
    </div>
  );
}
