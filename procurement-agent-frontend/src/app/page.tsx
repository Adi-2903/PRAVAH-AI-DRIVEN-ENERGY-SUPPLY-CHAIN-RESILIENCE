"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import dynamic from 'next/dynamic';
import { ArrowDown, ArrowUp, Zap, ShieldAlert, Clock, RefreshCw } from "lucide-react";

// Dynamically import force graph to avoid SSR issues
const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });

type Recommendation = {
  supplier: string;
  route: string;
  port: string;
  grade_match: string;
  grade_compatibility_score: number;
  estimated_cost_usd_per_bbl: number;
  transit_days: number;
  corridor_risk_score: number;
  composite_score: number;
  rank: number;
  reasoning: string;
};

type Baseline = {
  supplier: string;
  estimated_cost_usd_per_bbl: number;
  transit_days: number;
  corridor_risk_score: number;
  composite_score: number;
};

export default function AnalystPanel() {
  const [costWeight, setCostWeight] = useState(0.5);
  const [riskWeight, setRiskWeight] = useState(0.3);
  const [transitWeight, setTransitWeight] = useState(0.2);

  const [graphData, setGraphData] = useState<{ nodes: any[], edges: any[] }>({ nodes: [], edges: [] });
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [baseline, setBaseline] = useState<Baseline | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [lastComputed, setLastComputed] = useState("");

  const handleWeightChange = (type: string, newValue: number) => {
    let newCost = costWeight;
    let newRisk = riskWeight;
    let newTransit = transitWeight;

    if (type === "cost") newCost = newValue;
    if (type === "risk") newRisk = newValue;
    if (type === "transit") newTransit = newValue;

    const total = newCost + newRisk + newTransit;
    
    // Auto-balance the others proportionally if total > 0
    if (total > 0 && total !== 1.0) {
      if (type === "cost") {
        const remaining = 1.0 - newCost;
        const oldRem = riskWeight + transitWeight;
        if (oldRem > 0) {
          newRisk = (riskWeight / oldRem) * remaining;
          newTransit = (transitWeight / oldRem) * remaining;
        } else {
          newRisk = remaining / 2;
          newTransit = remaining / 2;
        }
      } else if (type === "risk") {
        const remaining = 1.0 - newRisk;
        const oldRem = costWeight + transitWeight;
        if (oldRem > 0) {
          newCost = (costWeight / oldRem) * remaining;
          newTransit = (transitWeight / oldRem) * remaining;
        } else {
          newCost = remaining / 2;
          newTransit = remaining / 2;
        }
      } else if (type === "transit") {
        const remaining = 1.0 - newTransit;
        const oldRem = costWeight + riskWeight;
        if (oldRem > 0) {
          newCost = (costWeight / oldRem) * remaining;
          newRisk = (riskWeight / oldRem) * remaining;
        } else {
          newCost = remaining / 2;
          newRisk = remaining / 2;
        }
      }
    }

    setCostWeight(newCost);
    setRiskWeight(newRisk);
    setTransitWeight(newTransit);
  };

  const fetchGraph = async () => {
    try {
      const res = await fetch("http://localhost:8000/graph");
      if (res.ok) {
        const data = await res.json();
        setGraphData(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchRecommendations = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const res = await fetch("http://localhost:8000/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_supplier: "saudi_arabia",
          current_corridor_risk_score: 78,
          target_refinery: "jamnagar",
          required_crude_grade: "medium_sour",
          cost_weight: costWeight,
          risk_weight: riskWeight,
          transit_time_weight: transitWeight,
          max_alternatives: 5
        })
      });

      if (!res.ok) throw new Error("Failed to fetch");
      const data = await res.json();
      setRecommendations(data.recommendations);
      setBaseline(data.current_supplier_baseline);
      setLastComputed(data.computed_at);
    } catch (e) {
      console.error(e);
      setError(true);
      
      // Fallback
      try {
        const fallbackRes = await fetch("http://localhost:8000/recommend/mock");
        if (fallbackRes.ok) {
          const fallbackData = await fallbackRes.json();
          setRecommendations(fallbackData.recommendations);
          setBaseline(fallbackData.current_supplier_baseline);
          setLastComputed(fallbackData.computed_at);
        }
      } catch (err) {}
    } finally {
      setLoading(false);
    }
  }, [costWeight, riskWeight, transitWeight]);

  useEffect(() => {
    fetchGraph();
  }, []);

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      fetchRecommendations();
    }, 500);
    return () => clearTimeout(delayDebounceFn);
  }, [fetchRecommendations]);

  const topRec = recommendations[0];
  const activeNodes = new Set<string>();
  const activeEdges = new Set<string>();
  
  if (topRec) {
    activeNodes.add(topRec.supplier);
    activeNodes.add(topRec.route);
    activeNodes.add(topRec.port);
    activeNodes.add("jamnagar"); // target refinery
    activeNodes.add("medium_sour"); // target grade
    
    activeEdges.add(`${topRec.supplier}-${topRec.route}`);
    activeEdges.add(`${topRec.route}-${topRec.port}`);
    activeEdges.add(`${topRec.port}-jamnagar`);
    activeEdges.add(`jamnagar-medium_sour`);
  }

  const baselineNodes = new Set<string>();
  const baselineEdges = new Set<string>();
  if (baseline && baseline.supplier !== topRec?.supplier) {
    baselineNodes.add(baseline.supplier);
    baselineNodes.add("hormuz_strait");
    baselineNodes.add("jamnagar_port");
    baselineEdges.add(`${baseline.supplier}-hormuz_strait`);
    baselineEdges.add(`hormuz_strait-jamnagar_port`);
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-teal-500/30 flex flex-col">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/50 p-4 flex items-center justify-between sticky top-0 z-10 backdrop-blur-md">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-semibold tracking-tight text-white flex items-center gap-2">
            <RefreshCw className="w-5 h-5 text-teal-400" />
            Supply Pivot Optimizer
          </h1>
          <div className="h-6 w-px bg-slate-800 mx-2"></div>
          <div className="flex items-center gap-2 text-sm text-slate-400">
            Target: <span className="font-medium text-slate-200">Jamnagar Refinery</span>
          </div>
          <div className="flex items-center gap-2 text-sm text-slate-400">
            Current Supplier: <span className="font-medium text-slate-200 capitalize">Saudi Arabia</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {error && <div className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20">Cached Response (API Down)</div>}
          <div className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">Risk Score: 78</div>
          <span className="text-xs text-slate-500">Updated: {new Date(lastComputed).toLocaleTimeString()}</span>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Left Rail: Controls */}
        <div className="w-80 border-r border-slate-800 bg-slate-900/30 p-6 flex flex-col gap-8 overflow-y-auto shrink-0">
          <div>
            <h2 className="text-lg font-medium text-white mb-6">Optimization Weights</h2>
            <div className="space-y-8">
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="flex items-center gap-1.5 text-teal-400"><Zap className="w-4 h-4"/> Cost Efficiency</span>
                  <span className="font-medium">{(costWeight * 100).toFixed(0)}%</span>
                </div>
                <input type="range" min="0" max="1" step="0.01" value={costWeight} onChange={(e) => handleWeightChange("cost", parseFloat(e.target.value))} className="w-full accent-teal-500" />
              </div>
              
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="flex items-center gap-1.5 text-rose-400"><ShieldAlert className="w-4 h-4"/> Security / Risk</span>
                  <span className="font-medium">{(riskWeight * 100).toFixed(0)}%</span>
                </div>
                <input type="range" min="0" max="1" step="0.01" value={riskWeight} onChange={(e) => handleWeightChange("risk", parseFloat(e.target.value))} className="w-full accent-rose-500" />
              </div>

              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="flex items-center gap-1.5 text-blue-400"><Clock className="w-4 h-4"/> Transit Time</span>
                  <span className="font-medium">{(transitWeight * 100).toFixed(0)}%</span>
                </div>
                <input type="range" min="0" max="1" step="0.01" value={transitWeight} onChange={(e) => handleWeightChange("transit", parseFloat(e.target.value))} className="w-full accent-blue-500" />
              </div>
            </div>
          </div>
          
          <div className="mt-auto pt-6 border-t border-slate-800/50">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Graph Legend</h3>
            <div className="space-y-2 text-sm text-slate-300">
              <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-emerald-500"></div> Recommended Path</div>
              <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full border border-dashed border-slate-500"></div> Current Baseline</div>
              <div className="flex items-center gap-2 mt-4"><div className="w-2 h-2 rounded-full bg-slate-600"></div> Supplier</div>
              <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-sm bg-slate-600 rotate-45"></div> Route</div>
              <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-sm bg-slate-600"></div> Port / Refinery</div>
            </div>
          </div>
        </div>

        {/* Center: Graph */}
        <div className="flex-1 relative bg-slate-950 overflow-hidden">
          {graphData.nodes.length > 0 ? (
            <ForceGraph2D
              graphData={{ nodes: graphData.nodes, links: graphData.edges }}
              width={typeof window !== 'undefined' ? window.innerWidth - 720 : 800} 
              nodeLabel="id"
              nodeColor={(node: any) => {
                if (activeNodes.has(node.id)) return '#10b981'; // emerald
                if (baselineNodes.has(node.id)) return '#64748b'; // slate
                return '#1e293b'; // dim
              }}
              nodeVal={(node: any) => {
                if (activeNodes.has(node.id)) return 8;
                return 5;
              }}
              linkColor={(edge: any) => {
                const linkId = typeof edge.source === 'object' 
                  ? `${edge.source.id}-${edge.target.id}` 
                  : `${edge.source}-${edge.target}`;
                if (activeEdges.has(linkId)) return '#10b981';
                if (baselineEdges.has(linkId)) return '#475569';
                return '#0f172a';
              }}
              linkWidth={(edge: any) => {
                const linkId = typeof edge.source === 'object' 
                  ? `${edge.source.id}-${edge.target.id}` 
                  : `${edge.source}-${edge.target}`;
                if (activeEdges.has(linkId)) return 3;
                if (baselineEdges.has(linkId)) return 1.5;
                return 1;
              }}
              linkLineDash={(edge: any) => {
                const linkId = typeof edge.source === 'object' 
                  ? `${edge.source.id}-${edge.target.id}` 
                  : `${edge.source}-${edge.target}`;
                if (baselineEdges.has(linkId) && !activeEdges.has(linkId)) return [4, 4];
                return [];
              }}
              linkDirectionalParticles={(edge: any) => {
                const linkId = typeof edge.source === 'object' 
                  ? `${edge.source.id}-${edge.target.id}` 
                  : `${edge.source}-${edge.target}`;
                if (activeEdges.has(linkId)) return 3;
                return 0;
              }}
              linkDirectionalParticleSpeed={0.005}
              backgroundColor="#020617"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-slate-500">Loading Graph...</div>
          )}
          
          {/* Baseline Strip */}
          {baseline && topRec && (
            <div className="absolute bottom-6 left-6 right-6 bg-slate-900/80 backdrop-blur-md border border-slate-700/50 rounded-xl p-4 flex items-center justify-between shadow-2xl">
              <div>
                <h4 className="text-xs font-semibold text-slate-400 uppercase mb-1">Impact Analysis</h4>
                <div className="text-sm font-medium">Shifting from <span className="capitalize text-white">{baseline.supplier}</span> to <span className="capitalize text-emerald-400">{topRec.supplier}</span></div>
              </div>
              
              <div className="flex gap-8">
                <div className="flex flex-col items-end">
                  <span className="text-xs text-slate-400 mb-1">Cost Delta</span>
                  <div className={`flex items-center gap-1 font-mono ${topRec.estimated_cost_usd_per_bbl < baseline.estimated_cost_usd_per_bbl ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {topRec.estimated_cost_usd_per_bbl < baseline.estimated_cost_usd_per_bbl ? <ArrowDown className="w-4 h-4"/> : <ArrowUp className="w-4 h-4"/>}
                    ${Math.abs(topRec.estimated_cost_usd_per_bbl - baseline.estimated_cost_usd_per_bbl).toFixed(2)}/bbl
                  </div>
                </div>
                
                <div className="flex flex-col items-end">
                  <span className="text-xs text-slate-400 mb-1">Risk Delta</span>
                  <div className={`flex items-center gap-1 font-mono ${topRec.corridor_risk_score < baseline.corridor_risk_score ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {topRec.corridor_risk_score < baseline.corridor_risk_score ? <ArrowDown className="w-4 h-4"/> : <ArrowUp className="w-4 h-4"/>}
                    {Math.abs(topRec.corridor_risk_score - baseline.corridor_risk_score).toFixed(0)} pts
                  </div>
                </div>
                
                <div className="flex flex-col items-end">
                  <span className="text-xs text-slate-400 mb-1">Transit Delta</span>
                  <div className={`flex items-center gap-1 font-mono ${topRec.transit_days < baseline.transit_days ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {topRec.transit_days < baseline.transit_days ? <ArrowDown className="w-4 h-4"/> : <ArrowUp className="w-4 h-4"/>}
                    {Math.abs(topRec.transit_days - baseline.transit_days)} days
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Rail: Recommendations */}
        <div className="w-[400px] border-l border-slate-800 bg-slate-900/30 p-6 overflow-y-auto shrink-0 relative">
          <h2 className="text-lg font-medium text-white mb-6">Ranked Alternatives</h2>
          
          {loading && recommendations.length === 0 ? (
            <div className="space-y-4">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-40 bg-slate-800/50 rounded-xl animate-pulse"></div>
              ))}
            </div>
          ) : (
            <div className="space-y-4 relative">
              {loading && (
                <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-[2px] z-10 flex items-center justify-center rounded-xl">
                  <RefreshCw className="w-6 h-6 text-teal-500 animate-spin" />
                </div>
              )}
              {recommendations.map((rec, idx) => (
                <div key={idx} className={`relative p-5 rounded-xl border ${idx === 0 ? 'bg-emerald-950/20 border-emerald-500/30 shadow-[0_0_30px_-5px_rgba(16,185,129,0.15)]' : 'bg-slate-800/20 border-slate-700/50'}`}>
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex items-center gap-3">
                      <div className={`flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${idx === 0 ? 'bg-emerald-500 text-slate-950' : 'bg-slate-700 text-slate-300'}`}>
                        {rec.rank}
                      </div>
                      <h3 className="font-semibold text-lg text-slate-100 capitalize">{rec.supplier}</h3>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-light text-white font-mono">{rec.composite_score.toFixed(2)}</div>
                      <div className="text-[10px] text-slate-500 uppercase font-semibold">Composite Score</div>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-3 gap-2 mb-4">
                    <div className="bg-slate-900/50 p-2 rounded-lg border border-slate-800/80">
                      <div className="text-[10px] text-slate-400 mb-1 flex items-center gap-1"><Zap className="w-3 h-3"/> Cost</div>
                      <div className="font-mono text-sm">${rec.estimated_cost_usd_per_bbl.toFixed(2)}</div>
                    </div>
                    <div className="bg-slate-900/50 p-2 rounded-lg border border-slate-800/80">
                      <div className="text-[10px] text-slate-400 mb-1 flex items-center gap-1"><ShieldAlert className="w-3 h-3"/> Risk</div>
                      <div className="font-mono text-sm">{rec.corridor_risk_score}</div>
                    </div>
                    <div className="bg-slate-900/50 p-2 rounded-lg border border-slate-800/80">
                      <div className="text-[10px] text-slate-400 mb-1 flex items-center gap-1"><Clock className="w-3 h-3"/> Transit</div>
                      <div className="font-mono text-sm">{rec.transit_days}d</div>
                    </div>
                  </div>
                  
                  <p className="text-xs text-slate-400 leading-relaxed border-t border-slate-700/50 pt-3">
                    <span className="text-slate-300 font-medium">Reasoning:</span> {rec.reasoning}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
