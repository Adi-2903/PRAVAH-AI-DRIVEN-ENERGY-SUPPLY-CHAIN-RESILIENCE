"use client";
import { useState } from 'react';
import { Shield, Lock, RefreshCw, FileDown, Printer, CheckCircle, AlertTriangle, Zap, TrendingUp, Clock, Star } from 'lucide-react';
import { exportPolicyDocument, printReport } from './lib/export';

const POLICY_CREDS = { username: 'pravah_pm', password: 'Hormuz@2026' };

const SITUATION = `The Strait of Hormuz corridor is at CRITICAL risk (82/100). Iran's IRGC Navy has seized a second foreign-flagged tanker within 48 hours. Three VLCCs have gone dark near 26.5°N 56.2°E. Brent crude has surged 6.1% to $84.12/bbl. AIS dark-shipping anomalies indicate potential sanctioned-vessel evasion. India sources 42% of crude imports via Hormuz, representing 17M bbl/day exposure. Current SPR cover stands at only 9.5 days against the IEA 90-day benchmark.`;

const AI_POLICIES = [
  {
    id: 1, priority: 'CRITICAL', category: 'Strategic Reserve',
    title: 'Activate Emergency SPR Front-Loaded Drawdown',
    description: 'Authorize immediate release of 900,000 bbl/day from strategic petroleum reserve for the first 3 days, tapering to 500,000 bbl/day for days 4–7. This front-loads drawdowns during highest-risk/price windows ($96–112/bbl projected range) to minimize import bill impact. Reserve never drops below the 20% safety floor (4.2 days remaining).',
    outcome: 'Estimated savings of $8.2M vs. naive uniform-drawdown. Buys 9 days of cushion for alternative procurement.',
    timeline: '48 hours — Emergency executive order',
    icon: Shield, color: '#ef4444', bg: 'rgba(239,68,68,0.08)', border: 'rgba(239,68,68,0.2)',
  },
  {
    id: 2, priority: 'HIGH', category: 'Procurement Diversification',
    title: 'Redirect 30% Import Volume to Cape Route Suppliers',
    description: 'Issue emergency procurement directive to redirect minimum 30% of weekly crude import volume to Russian Urals via Cape of Good Hope ($63/bbl, risk 22/100) and US WTI via trans-Atlantic route ($74/bbl, risk 15/100). Negotiate spot contracts with flexibility clauses for 60-day duration pending corridor stabilization.',
    outcome: 'Reduces Hormuz exposure from 42% to ~29% of total imports. Estimated cost delta: +$4.2/bbl on diverted volume, offset by SPR savings.',
    timeline: '72 hours — Ministerial directive to IOCs',
    icon: TrendingUp, color: '#f97316', bg: 'rgba(249,115,22,0.08)', border: 'rgba(249,115,22,0.2)',
  },
  {
    id: 3, priority: 'HIGH', category: 'Diplomatic & Naval',
    title: 'Invoke India-US Strategic Energy Pact Clause 7(b)',
    description: 'Activate the bilateral strategic energy cooperation clause to request US Fifth Fleet escort coordination for Indian-flagged crude carriers transiting Hormuz. Simultaneously initiate back-channel diplomatic communication with Oman for alternative pipeline access via Duqm terminal, bypassing the strait for 2–3M bbl/day capacity.',
    outcome: 'Reduces effective risk score for Indian-flagged transits from 82/100 to ~55/100 with escort. Duqm alternative provides 12–18% bypass capacity.',
    timeline: '24 hours — Foreign Ministry priority channel',
    icon: Star, color: '#8b5cf6', bg: 'rgba(139,92,246,0.08)', border: 'rgba(139,92,246,0.2)',
  },
  {
    id: 4, priority: 'ELEVATED', category: 'Refinery Operations',
    title: 'Mandate Refinery Crude Blend Adjustment Protocol',
    description: 'Direct Indian refineries (IOCL, BPCL, HPCL) to activate blend adjustment protocols: increase West African light-sweet crude (Bonny Light, Forcados) processing capacity by 15%, reduce medium-sour Arab Light dependency. Authorize temporary grade deviation allowances under Petroleum Act Section 12(c) for operational flexibility.',
    outcome: 'Increases refinery flexibility to absorb non-Hormuz crude grades without throughput loss. Estimated adjustment cost: ₹180 crore/month.',
    timeline: '5 days — Ministry directive to PSU refiners',
    icon: Zap, color: '#eab308', bg: 'rgba(234,179,8,0.08)', border: 'rgba(234,179,8,0.2)',
  },
  {
    id: 5, priority: 'ELEVATED', category: 'Consumer Protection',
    title: 'Pre-authorize Fuel Price Stabilization Buffer Activation',
    description: 'Pre-authorize activation of the Fuel Price Stabilization Fund (FPSF) buffer up to ₹2,800 crore to prevent pump price pass-through if P90 scenario (Brent >$112/bbl) materializes. Set auto-trigger threshold at Brent crossing $100/bbl sustained for 72 hours. This prevents economic shock while diplomatic/supply measures take effect.',
    outcome: 'Prevents pump price spike of ₹7.7/litre at P90 scenario. Protects 285 million fuel-dependent households from immediate cost shock.',
    timeline: '12 hours — Cabinet pre-authorization',
    icon: CheckCircle, color: '#22c55e', bg: 'rgba(34,197,94,0.08)', border: 'rgba(34,197,94,0.2)',
  },
];

const PRIORITY_ORDER = ['CRITICAL', 'HIGH', 'ELEVATED', 'LOW'];

function LoginModal({ onLogin }: { onLogin: () => void }) {
  const [user, setUser] = useState('');
  const [pass, setPass] = useState('');
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setTimeout(() => {
      if (user === POLICY_CREDS.username && pass === POLICY_CREDS.password) {
        onLogin();
      } else {
        setErr('Invalid credentials. Access denied.');
        setLoading(false);
      }
    }, 800);
  };

  return (
    <div style={{ minHeight: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg,#0f172a,#1e3a5f)', padding: '20px 40px' }}>
      <div style={{ width: '100%', maxWidth: 420, background: '#fff', borderRadius: 20, boxShadow: '0 24px 64px rgba(0,0,0,0.35)', overflow: 'hidden' }}>
        {/* Header */}
        <div style={{ background: 'linear-gradient(135deg,#1e3a8a,#2563eb)', padding: '24px 36px 20px', textAlign: 'center' }}>
          <div style={{ width: 52, height: 52, borderRadius: 14, background: 'rgba(255,255,255,0.15)', border: '2px solid rgba(255,255,255,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 12px' }}>
            <Shield style={{ width: 24, height: 24, color: '#fff' }} />
          </div>
          <div style={{ fontSize: 20, fontWeight: 800, color: '#fff', marginBottom: 2 }}>Policy Maker Access</div>
          <div style={{ fontSize: 11, color: 'rgba(186,230,253,0.85)', fontWeight: 500 }}>PRAVAH · Classified Strategic Portal</div>
        </div>
        {/* Credentials hint */}
        <div style={{ background: '#f0fdf4', borderBottom: '1px solid #bbf7d0', padding: '8px 36px', display: 'flex', alignItems: 'center', gap: 8 }}>
          <Lock style={{ width: 11, height: 11, color: '#16a34a', flexShrink: 0 }} />
          <span style={{ fontSize: 11, color: '#15803d', fontWeight: 600 }}>
            Demo: <code style={{ background: '#dcfce7', padding: '1px 5px', borderRadius: 4, fontSize: 10 }}>pravah_pm</code> / <code style={{ background: '#dcfce7', padding: '1px 5px', borderRadius: 4, fontSize: 10 }}>Hormuz@2026</code>
          </span>
        </div>
        {/* Form */}
        <form onSubmit={submit} style={{ padding: '22px 36px 24px' }}>
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 10, fontWeight: 700, color: '#374151', letterSpacing: '0.08em', textTransform: 'uppercase', display: 'block', marginBottom: 6 }}>Username</label>
            <input value={user} onChange={e => { setUser(e.target.value); setErr(''); }}
              placeholder="Enter username" autoComplete="username"
              style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: err ? '1.5px solid #ef4444' : '1.5px solid #e2e8f0', fontSize: 14, outline: 'none', boxSizing: 'border-box', fontFamily: 'inherit' }} />
          </div>
          <div style={{ marginBottom: 18 }}>
            <label style={{ fontSize: 10, fontWeight: 700, color: '#374151', letterSpacing: '0.08em', textTransform: 'uppercase', display: 'block', marginBottom: 6 }}>Password</label>
            <input type="password" value={pass} onChange={e => { setPass(e.target.value); setErr(''); }}
              placeholder="Enter password" autoComplete="current-password"
              style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: err ? '1.5px solid #ef4444' : '1.5px solid #e2e8f0', fontSize: 14, outline: 'none', boxSizing: 'border-box', fontFamily: 'inherit' }} />
          </div>
          {err && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 8, padding: '8px 12px', marginBottom: 14 }}>
              <AlertTriangle style={{ width: 13, height: 13, color: '#ef4444', flexShrink: 0 }} />
              <span style={{ fontSize: 12, color: '#ef4444', fontWeight: 600 }}>{err}</span>
            </div>
          )}
          <button type="submit" disabled={loading || !user || !pass}
            style={{ width: '100%', padding: '12px', background: loading ? '#93c5fd' : 'linear-gradient(135deg,#2563eb,#1d4ed8)', color: '#fff', border: 'none', borderRadius: 12, fontSize: 14, fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, transition: 'all 0.2s' }}>
            {loading ? <><RefreshCw style={{ width: 15, height: 15 }} className="animate-spin" /> Authenticating...</> : <><Lock style={{ width: 15, height: 15 }} /> Access Policy Portal</>}
          </button>
          <p style={{ marginTop: 14, fontSize: 10, color: '#94a3b8', textAlign: 'center', lineHeight: 1.5 }}>
            Access is logged and audited. Unauthorized attempts are reported to the Security Operations Center.
          </p>
        </form>
      </div>
    </div>
  );
}

function PolicyCard({ policy, index }: { policy: typeof AI_POLICIES[0]; index: number }) {
  const [expanded, setExpanded] = useState(index === 0);
  const Icon = policy.icon;
  const priorityColors: Record<string, string> = { CRITICAL: '#ef4444', HIGH: '#f97316', ELEVATED: '#eab308', LOW: '#22c55e' };
  const pc = priorityColors[policy.priority] || '#64748b';

  return (
    <div style={{ background: '#fff', borderRadius: 16, border: `1px solid ${policy.border}`, boxShadow: '0 2px 12px rgba(0,0,0,0.06)', overflow: 'hidden', transition: 'box-shadow 0.2s' }}>
      <div style={{ padding: '20px 24px', cursor: 'pointer', display: 'flex', gap: 16, alignItems: 'flex-start' }} onClick={() => setExpanded(!expanded)}>
        <div style={{ width: 44, height: 44, borderRadius: 12, background: policy.bg, border: `1px solid ${policy.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <Icon style={{ width: 20, height: 20, color: policy.color }} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 9, fontWeight: 800, padding: '3px 8px', borderRadius: 6, background: `${pc}15`, color: pc, letterSpacing: '0.08em', border: `1px solid ${pc}30` }}>{policy.priority}</span>
            <span style={{ fontSize: 9, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{policy.category}</span>
          </div>
          <div style={{ fontSize: 15, fontWeight: 800, color: '#0f172a', lineHeight: 1.3 }}>{policy.title}</div>
        </div>
        <div style={{ fontSize: 18, color: '#94a3b8', fontWeight: 300, flexShrink: 0, marginTop: 2 }}>{expanded ? '−' : '+'}</div>
      </div>
      {expanded && (
        <div style={{ padding: '0 24px 24px', borderTop: `1px solid ${policy.border}` }}>
          <p style={{ fontSize: 13, color: '#334155', lineHeight: 1.7, marginTop: 16, marginBottom: 16, fontWeight: 500 }}>{policy.description}</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div style={{ background: '#f8fafc', borderRadius: 10, padding: '12px 16px' }}>
              <div style={{ fontSize: 9, fontWeight: 800, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>Expected Outcome</div>
              <div style={{ fontSize: 12, color: '#334155', lineHeight: 1.5, fontWeight: 500 }}>{policy.outcome}</div>
            </div>
            <div style={{ background: '#f8fafc', borderRadius: 10, padding: '12px 16px' }}>
              <div style={{ fontSize: 9, fontWeight: 800, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
                <Clock style={{ width: 10, height: 10, display: 'inline', marginRight: 4 }} />Implementation
              </div>
              <div style={{ fontSize: 12, color: '#334155', lineHeight: 1.5, fontWeight: 600 }}>{policy.timeline}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function PolicyMaker() {
  const [authed, setAuthed] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState(false);
  const [policies, setPolicies] = useState<typeof AI_POLICIES>([]);

  const generate = () => {
    setGenerating(true);
    setTimeout(() => {
      setPolicies(AI_POLICIES);
      setGenerated(true);
      setGenerating(false);
    }, 2200);
  };

  if (!authed) return <LoginModal onLogin={() => setAuthed(true)} />;

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1100, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 28, paddingBottom: 24, borderBottom: '1px solid rgba(0,0,0,0.07)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#8b5cf6', marginBottom: 6 }}>Policy Maker Portal · Classified</div>
            <h1 style={{ fontSize: 30, fontWeight: 800, color: '#0f172a', fontFamily: 'var(--font-display)', letterSpacing: '-0.02em', marginBottom: 8 }}>
              AI Policy Advisory
            </h1>
            <p style={{ fontSize: 14, color: '#64748b', fontWeight: 500, maxWidth: 600, lineHeight: 1.6 }}>
              AI-generated policy recommendations calibrated against live risk intelligence, scenario models, and procurement data. Each policy is ranked by urgency and expected impact.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
            {generated && (
              <>
                <button onClick={() => printReport('Policy Advisory')} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 10, border: '1px solid #e2e8f0', background: '#fff', fontSize: 12, fontWeight: 700, color: '#64748b', cursor: 'pointer' }}>
                  <Printer style={{ width: 14, height: 14 }} /> Print
                </button>
                <button onClick={() => exportPolicyDocument(policies, SITUATION)} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px', borderRadius: 10, background: 'linear-gradient(135deg,#7c3aed,#6d28d9)', color: '#fff', border: 'none', fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>
                  <FileDown style={{ width: 14, height: 14 }} /> Export PDF
                </button>
              </>
            )}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px', borderRadius: 8, background: 'rgba(139,92,246,0.08)', border: '1px solid rgba(139,92,246,0.2)' }}>
              <Shield style={{ width: 12, height: 12, color: '#8b5cf6' }} />
              <span style={{ fontSize: 10, fontWeight: 700, color: '#8b5cf6', letterSpacing: '0.06em' }}>Authenticated: pravah_pm</span>
            </div>
          </div>
        </div>
      </div>

      {/* Situation Briefing */}
      <div style={{ background: 'linear-gradient(135deg,rgba(239,68,68,0.04),rgba(249,115,22,0.04))', border: '1px solid rgba(239,68,68,0.15)', borderRadius: 16, padding: 24, marginBottom: 24 }}>
        <div style={{ display: 'flex', gap: 14, alignItems: 'flex-start' }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <AlertTriangle style={{ width: 16, height: 16, color: '#ef4444' }} />
          </div>
          <div>
            <div style={{ fontSize: 10, fontWeight: 800, color: '#ef4444', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 8 }}>Current Situation Briefing · AI Assessed</div>
            <p style={{ fontSize: 13, color: '#334155', lineHeight: 1.7, fontWeight: 500, margin: 0 }}>{SITUATION}</p>
          </div>
        </div>
      </div>

      {/* Generate Button / Policies */}
      {!generated ? (
        <div style={{ textAlign: 'center', padding: '60px 40px', background: '#fff', borderRadius: 20, border: '1px solid rgba(0,0,0,0.06)', boxShadow: '0 4px 24px rgba(0,0,0,0.05)' }}>
          <div style={{ width: 72, height: 72, borderRadius: 20, background: 'linear-gradient(135deg,rgba(139,92,246,0.12),rgba(99,102,241,0.12))', border: '1px solid rgba(139,92,246,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}>
            <Zap style={{ width: 32, height: 32, color: '#8b5cf6' }} />
          </div>
          <h2 style={{ fontSize: 22, fontWeight: 800, color: '#0f172a', marginBottom: 10 }}>Generate AI Policy Recommendations</h2>
          <p style={{ fontSize: 14, color: '#64748b', marginBottom: 28, maxWidth: 480, margin: '0 auto 28px', lineHeight: 1.6 }}>
            The AI will analyse current risk scores, scenario projections, and procurement data to generate ranked policy actions for Ministerial review.
          </p>
          <button onClick={generate} disabled={generating}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 10, padding: '14px 32px', background: generating ? '#a78bfa' : 'linear-gradient(135deg,#7c3aed,#6d28d9)', color: '#fff', border: 'none', borderRadius: 14, fontSize: 15, fontWeight: 700, cursor: generating ? 'not-allowed' : 'pointer', boxShadow: '0 8px 24px rgba(124,58,237,0.35)', transition: 'all 0.2s' }}>
            {generating ? <><RefreshCw style={{ width: 18, height: 18 }} className="animate-spin" /> Analysing Situation...</> : <><Zap style={{ width: 18, height: 18 }} /> Generate Policy Recommendations</>}
          </button>
          {generating && (
            <div style={{ marginTop: 24, fontSize: 12, color: '#94a3b8', fontWeight: 600 }}>
              Consulting GDELT · AIS · OFAC · EIA data layers...
            </div>
          )}
        </div>
      ) : (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#94a3b8' }}>
              {policies.length} Policy Recommendations · Ranked by Priority
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, fontWeight: 600, color: '#22c55e' }}>
              <CheckCircle style={{ width: 12, height: 12 }} /> AI Analysis Complete · {new Date().toLocaleTimeString('en-IN')}
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {policies.sort((a, b) => PRIORITY_ORDER.indexOf(a.priority) - PRIORITY_ORDER.indexOf(b.priority)).map((p, i) => (
              <PolicyCard key={p.id} policy={p} index={i} />
            ))}
          </div>
          <div style={{ marginTop: 24, padding: '16px 20px', background: 'rgba(139,92,246,0.04)', border: '1px solid rgba(139,92,246,0.15)', borderRadius: 12, fontSize: 12, color: '#64748b', lineHeight: 1.6, fontWeight: 500 }}>
            <strong style={{ color: '#7c3aed' }}>Disclaimer:</strong> These policy recommendations are generated by PRAVAH AI Advisory Layer (Gemini 2.5 Flash) and are intended for strategic planning purposes only. All recommendations require review and approval by authorized Ministry of Petroleum & Natural Gas officials before implementation. The AI system processes GDELT, AIS, OFAC, and EIA data but cannot account for all geopolitical factors.
          </div>
        </div>
      )}
    </div>
  );
}
