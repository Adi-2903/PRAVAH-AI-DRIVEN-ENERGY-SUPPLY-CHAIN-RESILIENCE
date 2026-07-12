"use client";

import { useState, useEffect, useCallback } from 'react';
import {
  ComposedChart, Area, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip,
  ResponsiveContainer, ReferenceLine, Cell
} from 'recharts';
import { Zap, Clock, Activity, CheckCircle2, FileDown } from 'lucide-react';
import { exportSPRScheduleCSV } from './lib/export';
import { serviceUrl } from './lib/api';

interface DailySchedule {
  day: number;
  drawdown_days: number;
  reserve_after_days: number;
  risk_score: number;
  price_usd: number;
  rationale: string;
}

interface SPRScheduleResponse {
  schedule: DailySchedule[];
  total_drawdown_days: number;
  baseline_cost_usd: number;
  optimized_cost_usd: number;
  savings_usd: number;
  savings_pct: number;
  reserve_never_below_floor: boolean;
  computed_at: string;
}

const generateMockData = (horizon: number) => {
  const risk = Array.from({length: horizon}, (_, i) => 60 + Math.sin(i/2)*30 + (i*1.5));
  const price = Array.from({length: horizon}, (_, i) => 85 + Math.sin(i/2.5)*15 + (i*0.5));
  return { risk, price };
};

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  const data = payload[0].payload;
  
  return (
    <div className="glass-dark" style={{ padding: 16, borderRadius: 12, minWidth: 240, boxShadow: '0 8px 32px rgba(0,0,0,0.4)' }}>
      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.5)', marginBottom: 8, paddingBottom: 8, borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        Day {label}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
          <span style={{ color: '#2dd4bf', fontWeight: 600 }}>Reserve</span>
          <span style={{ fontFamily: 'var(--font-mono)', color: '#fff', fontWeight: 700 }}>{data.reserve_after_days.toFixed(2)}d</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
          <span style={{ color: '#60a5fa', fontWeight: 600 }}>Release</span>
          <span style={{ fontFamily: 'var(--font-mono)', color: '#fff', fontWeight: 700 }}>{data.drawdown_days.toFixed(2)}d</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
          <span style={{ color: '#fbbf24', fontWeight: 600 }}>Price</span>
          <span style={{ fontFamily: 'var(--font-mono)', color: '#fff', fontWeight: 700 }}>${data.price_usd.toFixed(2)}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
          <span style={{ color: '#f87171', fontWeight: 600 }}>Risk Score</span>
          <span style={{ fontFamily: 'var(--font-mono)', color: '#fff', fontWeight: 700 }}>{data.risk_score.toFixed(0)}</span>
        </div>
      </div>
      {data.drawdown_days > 0 && (
        <div style={{ marginTop: 12, paddingTop: 10, borderTop: '1px solid rgba(255,255,255,0.06)', fontSize: 11, color: 'rgba(255,255,255,0.6)', fontStyle: 'italic' }}>
          {data.rationale}
        </div>
      )}
    </div>
  );
};

export default function SPROptimizer() {
  const [horizon, setHorizon] = useState(14);
  const [floor, setFloor] = useState(3.0);
  const [maxDrawdown, setMaxDrawdown] = useState(1.0);
  const [result, setResult] = useState<SPRScheduleResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [isMock, setIsMock] = useState(false);
  
  const currentReserve = 9.5;

  const fetchOptimization = useCallback(async () => {
    setLoading(true);
    try {
      const mockInputs = generateMockData(horizon);
      const res = await fetch(serviceUrl('spr', '/spr-schedule'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          planning_horizon_days: horizon,
          current_reserve_days: currentReserve,
          min_safety_floor_days: floor,
          daily_risk_scores: mockInputs.risk,
          daily_price_forecast_usd_per_bbl: mockInputs.price,
          max_daily_drawdown_days: maxDrawdown
        }),
        signal: AbortSignal.timeout(8000)
      });
      if (!res.ok) throw new Error('API failed');
      setResult(await res.json());
      setIsMock(false);
    } catch (e) {
      try {
        const m = await fetch(serviceUrl('spr', '/spr-schedule/mock'), { signal: AbortSignal.timeout(8000) });
        setResult(await m.json());
      } catch {
        const mockInputs = generateMockData(horizon);
        const sched = [];
        let res = currentReserve;
        for(let i=0; i<horizon; i++) {
          const d = i > 4 && i < 8 ? Math.min(maxDrawdown, Math.max(0, res - floor)) : 0;
          res -= d;
          sched.push({
            day: i+1, drawdown_days: d, reserve_after_days: res,
            risk_score: mockInputs.risk[i], price_usd: mockInputs.price[i],
            rationale: d > 0 ? "Strategic release." : "Reserve held."
          });
        }
        setResult({
          schedule: sched, total_drawdown_days: currentReserve - res,
          baseline_cost_usd: 12000000, optimized_cost_usd: 9000000,
          savings_usd: 3000000, savings_pct: 25.0, reserve_never_below_floor: true,
          computed_at: new Date().toISOString()
        });
      }
      setIsMock(true);
    } finally {
      setLoading(false);
    }
  }, [horizon, floor, maxDrawdown, currentReserve]);

  useEffect(() => {
    const handler = setTimeout(fetchOptimization, 400);
    return () => clearTimeout(handler);
  }, [fetchOptimization]);

  return (
    <div style={{ background: '#020617', minHeight: '100%', padding: '28px 32px', color: '#f8fafc' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32, paddingBottom: 24, borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, fontFamily: 'var(--font-display)', display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: 'rgba(20,184,166,0.1)', border: '1px solid rgba(20,184,166,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Zap style={{ width: 20, height: 20, color: '#14b8a6' }} />
            </div>
            SPR Release Optimizer
          </h1>
          <p style={{ fontSize: 13, color: '#94a3b8', marginTop: 8, fontWeight: 500 }}>Linear Programming solver for strategic reserve drawdown</p>
        </div>
        <div style={{ display: 'flex', gap: 24, alignItems: 'center' }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#64748b', marginBottom: 4 }}>Current Reserve Cover</div>
            <div style={{ fontSize: 24, fontFamily: 'var(--font-mono)', fontWeight: 800, color: '#2dd4bf' }}>{currentReserve} Days</div>
          </div>
          {isMock && (
             <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.2)', padding: '6px 12px', borderRadius: 8, fontSize: 11, fontWeight: 700, color: '#fbbf24' }}>
               <Activity style={{ width: 14, height: 14 }} /> Offline Mode
             </div>
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 3fr', gap: 24 }}>
        
        {/* Left Rail: Controls */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          <div className="card-dark" style={{ position: 'relative' }}>
            <div style={{ position: 'absolute', top: 0, left: 0, bottom: 0, width: 3, background: '#14b8a6' }} />
            <div className="card-dark-header">
              <span className="label-caps" style={{ color: 'rgba(255,255,255,0.8)' }}>Optimization Constraints</span>
              {loading && <Clock className="animate-spin" style={{ width: 14, height: 14, color: '#2dd4bf' }} />}
            </div>
            
            <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 24 }}>
              {[
                { label: 'Planning Horizon', val: horizon, set: setHorizon, min: 7, max: 30, step: 1, format: (v: number) => `${v}d` },
                { label: 'Safety Floor', val: floor, set: setFloor, min: 0, max: 8, step: 0.5, format: (v: number) => `${v.toFixed(1)}d`, note: 'Hard constraint: Reserve will never drop below this.' },
                { label: 'Max Daily Draw', val: maxDrawdown, set: setMaxDrawdown, min: 0.1, max: 3.0, step: 0.1, format: (v: number) => `${v.toFixed(1)}d` }
              ].map(ctrl => (
                <div key={ctrl.label}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <label style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.5)' }}>{ctrl.label}</label>
                    <span style={{ fontSize: 13, fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#fff', background: 'rgba(255,255,255,0.06)', padding: '2px 8px', borderRadius: 6 }}>{ctrl.format(ctrl.val)}</span>
                  </div>
                  <input type="range" className="accent-teal" min={ctrl.min} max={ctrl.max} step={ctrl.step} value={ctrl.val} onChange={e => ctrl.set(Number(e.target.value))} />
                  {ctrl.note && <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', marginTop: 8, lineHeight: 1.4 }}>{ctrl.note}</div>}
                </div>
              ))}
            </div>
          </div>
          
          {/* Savings Callout */}
          {result && (
            <div className="card-dark" style={{ background: 'linear-gradient(135deg, rgba(15,23,42,1) 0%, rgba(2,6,23,1) 100%)' }}>
              <div style={{ padding: 24 }}>
                <h3 style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.5)', marginBottom: 8 }}>Value Optimized vs. Baseline</h3>
                <div style={{ fontSize: 36, fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#34d399', letterSpacing: '-0.03em', lineHeight: 1 }}>
                  ${(result.savings_usd / 1000000).toFixed(2)}M
                </div>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#10b981', marginTop: 8, marginBottom: 24 }}>
                  {result.savings_pct.toFixed(1)}% savings generated
                </div>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginBottom: 6 }}>
                      <span>Naive Baseline</span>
                      <span>${(result.baseline_cost_usd / 1000000).toFixed(1)}M Cost</span>
                    </div>
                    <div className="risk-bar-track" style={{ height: 6, background: 'rgba(255,255,255,0.05)' }}>
                      <div style={{ width: '100%', height: '100%', background: 'rgba(255,255,255,0.2)' }} />
                    </div>
                  </div>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#34d399', marginBottom: 6 }}>
                      <span>Optimized</span>
                      <span>${(result.optimized_cost_usd / 1000000).toFixed(1)}M Cost</span>
                    </div>
                    <div className="risk-bar-track" style={{ height: 6, background: 'rgba(255,255,255,0.05)' }}>
                      <div style={{ width: `${100 - result.savings_pct}%`, height: '100%', background: '#10b981', borderRadius: 10 }} />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Main Content */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          
          <div className="card-dark">
            <div className="card-dark-header">
              <div>
                <h2 style={{ fontSize: 16, fontWeight: 700, color: '#fff' }}>Optimal Drawdown Trajectory</h2>
                <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', marginTop: 4 }}>Reserve level and daily release overlaid with market price forecast.</p>
              </div>
              <div style={{ display: 'flex', gap: 16, fontSize: 11, fontWeight: 700, color: 'rgba(255,255,255,0.6)' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#2dd4bf' }}><div style={{ width: 12, height: 12, background: 'rgba(45,212,191,0.2)', border: '1px solid #2dd4bf', borderRadius: 2 }} /> Reserve Level</span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#60a5fa' }}><div style={{ width: 12, height: 12, background: '#3b82f6', borderRadius: 2 }} /> Daily Drawdown</span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#fbbf24' }}><div style={{ width: 12, height: 3, background: '#fbbf24' }} /> Price Forecast</span>
              </div>
            </div>

            <div style={{ height: 420, padding: '24px 24px 0 0', transition: 'opacity 0.3s', opacity: loading ? 0.3 : 1 }}>
              {result && (
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={result.schedule}>
                    <defs>
                      <linearGradient id="reserveGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#14b8a6" stopOpacity={0.25}/>
                        <stop offset="95%" stopColor="#14b8a6" stopOpacity={0.0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                    <XAxis dataKey="day" stroke="transparent" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11, fontWeight: 600 }} tickMargin={12} />
                    <YAxis yAxisId="left" stroke="transparent" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11, fontFamily: 'var(--font-mono)' }} tickFormatter={v => `${v}d`} domain={[0, currentReserve + 1]} tickMargin={12} />
                    <YAxis yAxisId="right" orientation="right" stroke="transparent" tick={{ fill: '#fbbf24', fontSize: 11, fontFamily: 'var(--font-mono)' }} tickFormatter={v => `$${v}`} domain={['auto', 'auto']} tickMargin={12} />
                    <RechartsTooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                    <ReferenceLine yAxisId="left" y={floor} stroke="#ef4444" strokeDasharray="4 4" 
                      label={{ position: 'insideBottomLeft', value: 'SAFETY FLOOR', fill: '#ef4444', fontSize: 10, fontWeight: 'bold', offset: 10 }} />
                    <Area yAxisId="left" type="stepAfter" dataKey="reserve_after_days" stroke="#14b8a6" strokeWidth={2} fill="url(#reserveGrad)" />
                    <Bar yAxisId="left" dataKey="drawdown_days" radius={[4, 4, 0, 0]} maxBarSize={40}>
                      {result.schedule.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.drawdown_days > 0 ? '#3b82f6' : 'transparent'} />
                      ))}
                    </Bar>
                    <Line yAxisId="right" type="monotone" dataKey="price_usd" stroke="#fbbf24" strokeWidth={3} dot={{ r: 4, fill: '#0f172a', stroke: '#fbbf24', strokeWidth: 2 }} />
                  </ComposedChart>
                </ResponsiveContainer>
              )}
            </div>

            {result && (
              <div style={{ margin: 24, padding: 16, background: 'rgba(52,211,153,0.06)', border: '1px solid rgba(52,211,153,0.15)', borderRadius: 12, display: 'flex', gap: 16, alignItems: 'flex-start' }}>
                <CheckCircle2 style={{ width: 24, height: 24, color: '#34d399', flexShrink: 0 }} />
                <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.7)', lineHeight: 1.6 }}>
                  <strong style={{ color: '#fff', marginRight: 6 }}>Strategy Output:</strong> The linear optimizer released <strong style={{ color: '#34d399' }}>{result.total_drawdown_days.toFixed(1)} days</strong> of SPR cover. 
                  Drawdowns were strictly front-loaded ahead of the highest-risk/price days, ensuring maximum offset value without breaching the {floor}d safety floor constraint.
                </p>
              </div>
            )}
          </div>

          {/* Schedule Table */}
          <div className="card-dark">
            <div className="card-dark-header">
              <span className="label-caps" style={{ color: '#fff' }}>Day-by-Day Release Schedule</span>
              {result && (
                <button
                  onClick={() => exportSPRScheduleCSV(result.schedule)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '5px 10px', borderRadius: 6,
                    background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)',
                    color: '#94a3b8', fontSize: 10, fontWeight: 700,
                    cursor: 'pointer', letterSpacing: '0.04em',
                  }}
                >
                  <FileDown style={{ width: 12, height: 12 }} /> Export CSV
                </button>
              )}
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table className="data-table data-table-dark">
                <thead>
                  <tr>
                    <th>Day</th>
                    <th>Drawdown</th>
                    <th>Reserve Left</th>
                    <th>Market Price</th>
                    <th>Risk</th>
                    <th>Rationale</th>
                  </tr>
                </thead>
                <tbody>
                  {result?.schedule.map((row) => (
                    <tr key={row.day}>
                      <td style={{ fontWeight: 700 }}>D+{row.day}</td>
                      <td>
                        <span style={{
                          fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 700,
                          color: row.drawdown_days > 0 ? '#60a5fa' : 'rgba(255,255,255,0.3)',
                          background: row.drawdown_days > 0 ? 'rgba(59,130,246,0.15)' : 'transparent',
                          padding: row.drawdown_days > 0 ? '4px 8px' : '0', borderRadius: 6
                        }}>
                          {row.drawdown_days > 0 ? `-${row.drawdown_days.toFixed(2)}d` : '0.00'}
                        </span>
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#2dd4bf' }}>{row.reserve_after_days.toFixed(2)}d</td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#fbbf24' }}>${row.price_usd.toFixed(2)}</td>
                      <td>
                        <span style={{
                          fontSize: 11, fontWeight: 800, padding: '4px 8px', borderRadius: 6,
                          background: row.risk_score > 90 ? 'rgba(239,68,68,0.15)' : row.risk_score > 75 ? 'rgba(245,158,11,0.15)' : 'rgba(34,197,94,0.15)',
                          color: row.risk_score > 90 ? '#f87171' : row.risk_score > 75 ? '#fbbf24' : '#4ade80'
                        }}>
                          {row.risk_score.toFixed(0)}
                        </span>
                      </td>
                      <td style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', maxWidth: 200, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{row.rationale}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
