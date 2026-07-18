"use client";

import React, { useState, useEffect, useCallback } from "react";
import { ComposableMap, Geographies, Geography, Marker, Line, ZoomableGroup } from "react-simple-maps";
import { ArrowDown, ArrowUp, Zap, ShieldAlert, Clock, RefreshCw, ChevronRight, ChevronLeft, Wifi, WifiOff, Trophy, Medal, Award, FileDown } from "lucide-react";
import { exportProcurementReport } from './lib/export';
import { serviceUrl, postJSON } from './lib/api';
import { useLiveData } from './lib/use-live-data';

const GEO_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

// Geo coords keyed by graph node IDs (fallback)
const FALLBACK_NODE_COORDS: Record<string, [number, number]> = {
  SAU_ARAMCO:  [49.0, 24.0],
  IRQ_SOMO:    [47.8, 31.0],
  UAE_ADNOC:   [54.4, 23.4],
  RUS_ROSNEFT: [60.0, 55.0],
  USA_WTI:     [-100.0, 38.0],
  NGA_NNPC:    [8.0, 9.0],
  KWT_KPC:     [47.5, 29.4],
  MEX_PEMEX:   [-99.0, 19.4],
  // Routes
  hormuz_saudi:  [56.5, 26.5],
  hormuz_iraq:   [57.0, 25.8],
  hormuz_uae:    [57.5, 25.2],
  hormuz_kuwait: [56.8, 26.2],
  basra_direct:  [55.0, 22.0],
  red_sea_suez:  [38.0, 20.0],
  cape_russia:   [18.5, -34.0],
  cape_nigeria:  [16.0, -33.0],
  cape_mexico:   [14.0, -32.0],
  pacific_india: [90.0, 10.0],
  // Ports
  PORT_VADINAR:   [69.8, 22.5],
  PORT_KANDLA:    [70.2, 23.0],
  PORT_MUMBAI:    [72.8, 18.9],
  PORT_PARADIP:   [86.6, 20.3],
  PORT_MANGALORE: [74.8, 12.9],
  PORT_VIZAG:     [83.3, 17.7],
  // Refineries
  REF_JAMNAGAR:   [70.1, 22.4],
  REF_VADINAR:    [69.9, 22.3],
  REF_PARADIP:    [86.7, 20.2],
  REF_MANGALORE:  [74.9, 12.8],
  REF_VIZAG:      [83.4, 17.6],
};

const FALLBACK_NODE_LABELS: Record<string, string> = {
  SAU_ARAMCO: "Saudi Aramco", IRQ_SOMO: "Iraq SOMO", UAE_ADNOC: "UAE ADNOC",
  RUS_ROSNEFT: "Russia", USA_WTI: "USA WTI", NGA_NNPC: "Nigeria",
  KWT_KPC: "Kuwait", MEX_PEMEX: "Mexico",
  PORT_VADINAR: "Vadinar", PORT_KANDLA: "Kandla", PORT_MUMBAI: "Mumbai",
  PORT_PARADIP: "Paradip", PORT_MANGALORE: "Mangalore", PORT_VIZAG: "Vizag",
  REF_JAMNAGAR: "Jamnagar Ref", REF_VADINAR: "Vadinar Ref",
  REF_PARADIP: "Paradip Ref", REF_MANGALORE: "Mangalore Ref", REF_VIZAG: "Vizag Ref",
};

const ROUTE_LABELS: Record<string, string> = {
  hormuz_saudi: "Hormuz", hormuz_iraq: "Hormuz", hormuz_uae: "Hormuz",
  hormuz_kuwait: "Hormuz", basra_direct: "Basra Direct",
  red_sea_suez: "Red Sea/Suez", cape_russia: "Cape Route",
  cape_nigeria: "Cape Route", cape_mexico: "Trans-Atlantic", pacific_india: "Pacific",
};

type Rec = {
  supplier: string; route: string; port: string;
  grade_compatibility_score: number;
  estimated_cost_usd_per_bbl: number;
  transit_days: number; corridor_risk_score: number;
  composite_score: number; rank: number; reasoning: string;
};
type Baseline = {
  supplier: string; estimated_cost_usd_per_bbl: number;
  transit_days: number; corridor_risk_score: number; composite_score: number;
};
type Market = { brent_usd: number; wti_usd: number; usd_inr: number; is_live: boolean; };

const RANK_ICONS = [<Trophy key="t" size={13}/>, <Medal key="m" size={13}/>, <Award key="a" size={13}/>];
const RANK_COLORS = ["#f59e0b", "#94a3b8", "#cd7f32"];
const RANK_BG = ["#fffbeb", "#f8fafc", "#fff8f3"];
const RANK_BORDER = ["#fde68a", "#e2e8f0", "#fed7aa"];

// Bundled sample data — used when the procurement-agent backend is unreachable
// so the view is never a blank screen (mirrors the fallback simulator/spr already have).
// Node/route/port IDs match NODE_COORDS so the map still renders paths.
const PROCUREMENT_FALLBACK: {
  recommendations: Rec[]; current_supplier_baseline: Baseline; market_data: Market; computed_at: string;
} = {
  recommendations: [
    { supplier: "RUS_ROSNEFT", route: "cape_russia",  port: "PORT_VADINAR", grade_compatibility_score: 0.90, estimated_cost_usd_per_bbl: 63.0, transit_days: 24, corridor_risk_score: 21, composite_score: 0.81, rank: 1, reasoning: "Lowest corridor risk via Cape of Good Hope (21/100). ~$21/bbl discount vs. Arab Light baseline. 24-day transit is longer but acceptable for strategic diversification. 90% grade compatibility with Jamnagar (medium-sour blend)." },
    { supplier: "USA_WTI",     route: "cape_mexico",   port: "PORT_MUMBAI",  grade_compatibility_score: 0.78, estimated_cost_usd_per_bbl: 74.0, transit_days: 40, corridor_risk_score: 15, composite_score: 0.68, rank: 2, reasoning: "Near-zero corridor risk via trans-Atlantic/Cape route. ~$10/bbl premium offsets the risk reduction. Longest transit (40d). Light-sweet grade needs blending at medium-sour-optimised refineries." },
    { supplier: "NGA_NNPC",    route: "cape_nigeria",  port: "PORT_PARADIP", grade_compatibility_score: 0.72, estimated_cost_usd_per_bbl: 85.2, transit_days: 28, corridor_risk_score: 18, composite_score: 0.62, rank: 3, reasoning: "Low-risk African route via Cape. Premium pricing but high-quality light-sweet crude. 28-day transit. Limited refinery grade compatibility for Indian downstream needs." },
    { supplier: "IRQ_SOMO",    route: "hormuz_iraq",   port: "PORT_VADINAR", grade_compatibility_score: 0.95, estimated_cost_usd_per_bbl: 79.1, transit_days: 9,  corridor_risk_score: 60, composite_score: 0.55, rank: 4, reasoning: "Best grade match (95%) and competitive $79/bbl pricing, but shares Hormuz transit risk (60/100) — only partial diversification. 9-day transit is fastest." },
    { supplier: "UAE_ADNOC",   route: "hormuz_uae",    port: "PORT_VADINAR", grade_compatibility_score: 0.88, estimated_cost_usd_per_bbl: 82.9, transit_days: 7,  corridor_risk_score: 78, composite_score: 0.42, rank: 5, reasoning: "Shortest transit (7d) and good grade match (88%), but fully exposed to Hormuz corridor risk (78/100) — same chokepoint as the current Saudi baseline. No diversification benefit." },
  ],
  current_supplier_baseline: { supplier: "SAU_ARAMCO", estimated_cost_usd_per_bbl: 82.0, transit_days: 8, corridor_risk_score: 78, composite_score: 0.40 },
  market_data: { brent_usd: 84.12, wti_usd: 80.55, usd_inr: 83.42, is_live: false },
  computed_at: "",
};

export default function ProcurementModule() {
  const [costWeight, setCostWeight] = useState(0.5);
  const [riskWeight, setRiskWeight] = useState(0.3);
  const [transitWeight, setTransitWeight] = useState(0.2);
  const [recs, setRecs] = useState<Rec[]>([]);
  const [baseline, setBaseline] = useState<Baseline | null>(null);
  
  const { market, corridors, refresh, loading: liveLoading, error: liveError, lastUpdated } = useLiveData();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isOffline, setIsOffline] = useState(false);
  const [rightOpen, setRightOpen] = useState(true);
  const [selectedRec, setSelectedRec] = useState(0);
  const [nodeCoords, setNodeCoords] = useState<Record<string, [number, number]>>(FALLBACK_NODE_COORDS);
  const [nodeLabels, setNodeLabels] = useState<Record<string, string>>({ ...FALLBACK_NODE_LABELS, ...ROUTE_LABELS });

  const handleWeight = (type: string, val: number) => {
    let c = costWeight, r = riskWeight, t = transitWeight;
    if (type === "cost")    { c = val; const rem = 1-c, o = r+t; r = o>0?(r/o)*rem:rem/2; t = o>0?(t/o)*rem:rem/2; }
    else if (type === "risk")  { r = val; const rem = 1-r, o = c+t; c = o>0?(c/o)*rem:rem/2; t = o>0?(t/o)*rem:rem/2; }
    else                     { t = val; const rem = 1-t, o = c+r; c = o>0?(c/o)*rem:rem/2; r = o>0?(r/o)*rem:rem/2; }
    setCostWeight(c); setRiskWeight(r); setTransitWeight(t);
  };

  const fetchData = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const liveHormuzRisk = corridors.find(c => c.corridor_id === 'hormuz')?.score ?? 78;
      
      const data = await postJSON<any>('procurement', '/recommend', {
          current_supplier: "SAU_ARAMCO",
          current_corridor_risk_score: liveHormuzRisk,
          target_refinery: "REF_JAMNAGAR",
          required_crude_grade: "GRADE_MEDIUM_SOUR",
          cost_weight: costWeight,
          risk_weight: riskWeight,
          transit_time_weight: transitWeight,
          max_alternatives: 5,
          market_data: market || undefined
        });
      setRecs(data.recommendations || []);
      setBaseline(data.current_supplier_baseline);
      setSelectedRec(0);
      setIsOffline(false);
      
      try {
        const token = localStorage.getItem('pravah_access_token');
        const headers: Record<string, string> = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;
        
        const graphRes = await fetch(serviceUrl('procurement', '/graph'), { headers, signal: AbortSignal.timeout(4000) });
        if (graphRes.ok) {
          const graphData = await graphRes.json();
          const newCoords = { ...FALLBACK_NODE_COORDS };
          const newLabels = { ...FALLBACK_NODE_LABELS, ...ROUTE_LABELS };
          graphData.nodes?.forEach((n: any) => {
            if (n.lat !== undefined && n.lon !== undefined) newCoords[n.id] = [n.lon, n.lat];
            if (n.display) newLabels[n.id] = n.display;
          });
          setNodeCoords(newCoords);
          setNodeLabels(newLabels);
        }
      } catch (e) {
        console.warn("Failed to fetch graph coords", e);
      }
    } catch (err: any) {
      if (err.status === 401 || (err.message && err.message.includes('401'))) {
        alert("Session expired or unauthorized. Please log in again.");
        window.location.href = "/";
        return;
      }
      // Backend unreachable — degrade to bundled sample data (never a blank screen).
      setRecs(PROCUREMENT_FALLBACK.recommendations);
      setBaseline(PROCUREMENT_FALLBACK.current_supplier_baseline);
      setSelectedRec(0);
      setIsOffline(true);
    } finally { setLoading(false); }
  }, [costWeight, riskWeight, transitWeight, market, corridors]);

  useEffect(() => {
    if (!liveLoading) {
      const t = setTimeout(fetchData, 500); 
      return () => clearTimeout(t);
    }
  }, [fetchData, liveLoading]);

  const active = recs[selectedRec];

  const recPath: [string, string][] = active
    ? [[active.supplier, active.route], [active.route, active.port], [active.port, "REF_JAMNAGAR"]]
    : [];
  const basePath: [string, string][] = baseline
    ? [[baseline.supplier, "hormuz_saudi"], ["hormuz_saudi", "PORT_VADINAR"], ["PORT_VADINAR", "REF_JAMNAGAR"]]
    : [];

  const recSet = new Set(recPath.flatMap(([a,b]) => [a,b]));
  const baseSet = new Set(basePath.flatMap(([a,b]) => [a,b]));

  const delta = (key: keyof Rec) =>
    active && baseline ? (active[key] as number) - (baseline[key as keyof Baseline] as number) : 0;

  return (
    <div style={{ display:"flex", height:"calc(100vh - 88px)", overflow:"hidden", background:"#f0f2f7", fontFamily:"'Inter',system-ui,sans-serif" }}>

      {/* LEFT: Weights */}
      <div style={{ width:240, minWidth:240, background:"#fff", borderRight:"1px solid #e2e8f0", display:"flex", flexDirection:"column", padding:"20px 16px", boxShadow:"2px 0 8px rgba(0,0,0,0.04)" }}>
        <div style={{ fontSize:11, fontWeight:700, color:"#94a3b8", textTransform:"uppercase", letterSpacing:"0.08em", marginBottom:20 }}>Optimization Weights</div>

        {[
          { key:"cost",    label:"Cost Efficiency", val:costWeight,    color:"#3b82f6", Icon:Zap },
          { key:"risk",    label:"Security / Risk",  val:riskWeight,    color:"#ef4444", Icon:ShieldAlert },
          { key:"transit", label:"Transit Speed",    val:transitWeight, color:"#8b5cf6", Icon:Clock },
        ].map(({ key, label, val, color, Icon }) => (
          <div key={key} style={{ marginBottom:24 }}>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:8 }}>
              <span style={{ display:"flex", alignItems:"center", gap:5, color, fontWeight:600, fontSize:12 }}>
                <Icon size={12}/> {label}
              </span>
              <span style={{ fontWeight:700, color:"#0f172a", fontSize:13, fontVariantNumeric:"tabular-nums" }}>{(val*100).toFixed(0)}%</span>
            </div>
            <input type="range" min="0" max="1" step="0.01" value={val}
              onChange={e => handleWeight(key, parseFloat(e.target.value))}
              style={{ width:"100%", accentColor:color, cursor:"pointer" }}/>
          </div>
        ))}

        {/* Market Badge */}
        {market && (
          <div style={{ marginTop:8, padding:"10px 12px", borderRadius:10, background:"#f8fafc", border:"1px solid #e2e8f0" }}>
            <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:6 }}>
              {market.is_live ? <Wifi size={10} color="#10b981"/> : <WifiOff size={10} color="#94a3b8"/>}
              <span style={{ fontSize:9, fontWeight:700, color: market.is_live?"#10b981":"#94a3b8", textTransform:"uppercase", letterSpacing:"0.07em" }}>
                {market.is_live ? "Live Prices" : "Static Prices"}
              </span>
              <button onClick={refresh} disabled={liveLoading} style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 4, background: "none", border: "none", cursor: "pointer", color: "#64748b", fontSize: 9, fontWeight: 700 }}>
                <Clock size={10} className={liveLoading ? "animate-spin" : ""} /> Refresh
              </button>
            </div>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:4 }}>
              {[
                { label:"Brent", val:`$${market.brent_usd.toFixed(2)}` },
                { label:"WTI",   val:`$${market.wti_usd.toFixed(2)}` },
                { label:"USD/INR", val:`₹${market.usd_inr.toFixed(2)}` },
              ].map(({ label, val }) => (
                <div key={label}>
                  <div style={{ fontSize:9, color:"#94a3b8", fontWeight:600 }}>{label}</div>
                  <div style={{ fontSize:11, fontWeight:700, color:"#0f172a", fontVariantNumeric:"tabular-nums" }}>{val}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Legend */}
        <div style={{ marginTop:"auto", paddingTop:16, borderTop:"1px solid #f1f5f9" }}>
          <div style={{ fontSize:10, fontWeight:700, color:"#94a3b8", textTransform:"uppercase", letterSpacing:"0.07em", marginBottom:10 }}>Map Legend</div>
          {[
            { color:"#2563eb", label:"Selected Alt. Path", solid:true },
            { color:"#94a3b8", label:"Current Baseline",   solid:false },
          ].map(({ color, label, solid }) => (
            <div key={label} style={{ display:"flex", alignItems:"center", gap:8, marginBottom:8, fontSize:11, color:"#64748b" }}>
              <div style={{ width:10, height:10, borderRadius:"50%", background:solid?color:"transparent", border:solid?"none":`2px dashed ${color}` }}/>
              {label}
            </div>
          ))}
        </div>
      </div>

      {/* CENTER: Map */}
      <div style={{ flex:1, position:"relative", overflow:"hidden", background:"#eef0f6" }}>
        <div style={{ position:"absolute", inset:0 }}>
          <ComposableMap projection="geoMercator" projectionConfig={{ scale:150 }} style={{ width:"100%", height:"100%" }}>
            <ZoomableGroup center={[20, 20]} zoom={1.2}>
              <Geographies geography={GEO_URL}>
                {({ geographies }) => geographies.map(geo => (
                  <Geography key={geo.rsmKey} geography={geo}
                    style={{ default:{ fill:"#dde3ec", stroke:"#94a3b8", strokeWidth:1.5, outline:"none" },
                             hover:{ fill:"#cbd5e1", outline:"none" }, pressed:{ fill:"#cbd5e1", outline:"none" } }}/>
                ))}
              </Geographies>
  
              {/* Baseline path */}
              {basePath.map(([f,t], i) => {
                const fc=nodeCoords[f], tc=nodeCoords[t];
                return fc&&tc ? <Line key={`b${i}`} from={fc} to={tc} stroke="#94a3b8" strokeWidth={1.5} strokeDasharray="5,4"/> : null;
              })}
  
              {/* Recommended path */}
              {recPath.map(([f,t], i) => {
                const fc=nodeCoords[f], tc=nodeCoords[t];
                return fc&&tc ? <Line key={`r${i}`} from={fc} to={tc} stroke="#2563eb" strokeWidth={3} strokeLinecap="round"/> : null;
              })}
  
              {/* Markers */}
              {Object.keys(nodeCoords).map(id => {
                const coords = nodeCoords[id];
                const isRec  = recSet.has(id);
                const isBase = baseSet.has(id);
                const r    = isRec ? 7 : isBase ? 5 : 3;
                const fill = isRec ? "#2563eb" : isBase ? "#94a3b8" : "#cbd5e1";
                const stroke = isRec ? "#93c5fd" : "#e2e8f0";
                const label = nodeLabels[id];
                return (
                  <Marker key={id} coordinates={coords}>
                    <circle r={r} fill={fill} stroke={stroke} strokeWidth={1.5}
                      style={{ filter: isRec ? "drop-shadow(0 0 6px #3b82f6)" : "none" }}/>
                    {(isRec || isBase) && label && (
                      <text textAnchor="middle" y={r+11}
                        style={{ fontSize: isRec?10:9, fill: isRec?"#1e40af":"#64748b", fontWeight: isRec?700:500, pointerEvents:"none", fontFamily:"Inter,sans-serif" }}>
                        {label}
                      </text>
                    )}
                  </Marker>
                );
              })}
            </ZoomableGroup>
          </ComposableMap>
        </div>

        {/* Loading spinner */}
        {loading && (
          <div style={{ position:"absolute", top:12, left:"50%", transform:"translateX(-50%)", background:"rgba(255,255,255,0.92)", backdropFilter:"blur(8px)", borderRadius:8, padding:"6px 14px", fontSize:11, color:"#2563eb", fontWeight:600, display:"flex", alignItems:"center", gap:6, border:"1px solid rgba(37,99,235,0.2)", boxShadow:"0 2px 8px rgba(0,0,0,0.08)" }}>
            <RefreshCw size={11} className="animate-spin"/> Recalculating...
          </div>
        )}

        {/* Error */}
        {(error || liveError) && !loading && (
          <div style={{ position:"absolute", top:12, left:"50%", transform:"translateX(-50%)", background:"#fef2f2", border:"1px solid #fecaca", borderRadius:8, padding:"8px 16px", fontSize:11, color:"#dc2626", fontWeight:600, maxWidth:400, textAlign:"center" }}>
            ⚠ Backend error: {error || liveError}
          </div>
        )}

        {/* Impact HUD */}
        {baseline && active && (
          <div style={{ position:"absolute", bottom:16, left:16, background:"rgba(255,255,255,0.94)", backdropFilter:"blur(12px)", border:"1px solid rgba(37,99,235,0.15)", borderRadius:14, padding:"12px 16px", minWidth:280, boxShadow:"0 8px 32px rgba(15,23,42,0.12)" }}>
            <div style={{ fontSize:9, fontWeight:700, color:"#6b7280", textTransform:"uppercase", letterSpacing:"0.08em", marginBottom:8 }}>
              Impact: <span style={{ color:"#64748b" }}>{nodeLabels[baseline.supplier]||baseline.supplier}</span> → <span style={{ color:"#2563eb" }}>{nodeLabels[active.supplier]||active.supplier}</span>
            </div>
            <div style={{ display:"flex", gap:14 }}>
              {[
                { label:"Cost/bbl Δ", val:delta("estimated_cost_usd_per_bbl") * (market?.usd_inr || 83.42), fmt:(v:number)=>`${v<0?'-':'+'}₹${Math.abs(v).toFixed(2)}` },
                { label:"Risk Δ",     val:delta("corridor_risk_score"),         fmt:(v:number)=>`${v<0?'-':'+'}${Math.abs(v).toFixed(0)} pts` },
                { label:"Transit Δ",  val:delta("transit_days"),                fmt:(v:number)=>`${v<0?'-':'+'}${Math.abs(v)}d` },
              ].map(({ label, val, fmt }) => (
                <div key={label} style={{ display:"flex", flexDirection:"column", gap:2 }}>
                  <span style={{ fontSize:9, color:"#64748b", fontWeight:600 }}>{label}</span>
                  <div style={{ display:"flex", alignItems:"center", gap:3, fontWeight:700, fontSize:13, color:val<0?"#10b981":"#ef4444", fontVariantNumeric:"tabular-nums" }}>
                    {val<0 ? <ArrowDown size={11}/> : <ArrowUp size={11}/>} {fmt(val)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Timestamp */}
        {lastUpdated && (
          <div style={{ position:"absolute", top:12, right:12, background:"rgba(255,255,255,0.85)", backdropFilter:"blur(6px)", borderRadius:6, padding:"4px 8px", fontSize:9, color:"#94a3b8", border:"1px solid #e2e8f0" }}>
            Last Updated: {new Date(lastUpdated).toLocaleTimeString('en-IN', { hour12: false })} IST
          </div>
        )}
      </div>

      {/* RIGHT: Recommendations */}
      <div style={{ position:"relative", display:"flex" }}>
        <button onClick={() => setRightOpen(o=>!o)}
          style={{ position:"absolute", left:-20, top:"50%", transform:"translateY(-50%)", zIndex:10, width:20, height:48, background:"#ffffff", border:"1px solid #e2e8f0", borderRight:"none", borderRadius:"6px 0 0 6px", display:"flex", alignItems:"center", justifyContent:"center", cursor:"pointer", color:"#94a3b8" }}>
          {rightOpen ? <ChevronRight size={13}/> : <ChevronLeft size={13}/>}
        </button>

        <div style={{ width:rightOpen?360:0, overflow:"hidden", transition:"width 0.25s ease", background:"#fff", borderLeft:"1px solid #e2e8f0", display:"flex", flexDirection:"column", boxShadow:"-2px 0 8px rgba(0,0,0,0.04)" }}>
          <div style={{ width:360, height:"100%", overflowY:"auto", padding:"20px 16px" }}>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:16 }}>
              <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                <div style={{ fontSize:11, fontWeight:700, color:"#94a3b8", textTransform:"uppercase", letterSpacing:"0.08em" }}>Ranked Alternatives</div>
                {isOffline && (
                  <span style={{ display:"inline-flex", alignItems:"center", gap:4, fontSize:8, fontWeight:800, letterSpacing:"0.06em", textTransform:"uppercase", color:"#f59e0b", background:"rgba(245,158,11,0.1)", border:"1px solid rgba(245,158,11,0.25)", borderRadius:4, padding:"2px 6px" }}>
                    <WifiOff size={9}/> Sample data
                  </span>
                )}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {recs.length > 0 && (
                  <>
                    <button
                      onClick={() => exportProcurementReport(recs, baseline)}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 4,
                        padding: '4px 8px', borderRadius: 6,
                        background: 'rgba(59,130,246,0.06)', border: '1px solid rgba(59,130,246,0.15)',
                        color: '#2563eb', fontSize: 9, fontWeight: 700,
                        cursor: 'pointer', letterSpacing: '0.04em',
                      }}
                    >
                      <FileDown size={10} /> PDF
                    </button>
                    <div style={{ fontSize:10, color:"#64748b", fontWeight:600 }}>{recs.length} found</div>
                  </>
                )}
              </div>
            </div>

            {loading && recs.length === 0 ? (
              [1,2,3].map(i => <div key={i} style={{ height:130, background:"#f1f5f9", borderRadius:10, marginBottom:12, opacity:0.7 }}/>)
            ) : recs.length === 0 && !loading ? (
              <div style={{ textAlign:"center", padding:"40px 0", color:"#94a3b8", fontSize:12 }}>
                {error ? "Backend unavailable" : "No alternatives found"}
              </div>
            ) : (
              recs.map((rec, idx) => {
                const isSelected = idx === selectedRec;
                const rankColor  = RANK_COLORS[idx] || "#64748b";
                const RankIcon   = RANK_ICONS[idx] || null;
                return (
                  <div key={`${rec.supplier}-${rec.route}`}
                    onClick={() => setSelectedRec(idx)}
                    style={{ padding:"14px", borderRadius:12, marginBottom:10, cursor:"pointer",
                      background: isSelected ? RANK_BG[idx]||"#f8fafc" : "#fafafa",
                      border: `1px solid ${isSelected ? RANK_BORDER[idx]||"#e2e8f0" : "#f1f5f9"}`,
                      boxShadow: isSelected ? `0 4px 20px ${rankColor}22` : "0 1px 4px rgba(0,0,0,0.04)",
                      transition:"all 0.2s" }}>

                    {/* Header row */}
                    <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:10 }}>
                      <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                        <div style={{ width:26, height:26, borderRadius:"50%", display:"flex", alignItems:"center", justifyContent:"center", background: isSelected?rankColor:"#e2e8f0", color: isSelected?"#fff":"#94a3b8", fontSize:11, fontWeight:800 }}>
                          {RankIcon && isSelected ? React.cloneElement(RankIcon, { color:"#fff" }) : <span>{rec.rank}</span>}
                        </div>
                        <div>
                          <div style={{ fontSize:13, fontWeight:700, color:"#0f172a" }}>
                            {NODE_LABELS[rec.supplier] || rec.supplier}
                          </div>
                          <div style={{ fontSize:9, color:"#94a3b8", fontWeight:600, marginTop:1 }}>
                            via {ROUTE_LABELS[rec.route] || rec.route} → {NODE_LABELS[rec.port] || rec.port}
                          </div>
                        </div>
                      </div>
                      <div style={{ textAlign:"right" }}>
                        <div style={{ fontSize:20, fontWeight:800, color: isSelected?rankColor:"#0f172a", fontVariantNumeric:"tabular-nums" }}>
                          {rec.composite_score.toFixed(3)}
                        </div>
                        <div style={{ fontSize:8, color:"#94a3b8", textTransform:"uppercase", letterSpacing:"0.07em" }}>score</div>
                      </div>
                    </div>

                    {/* Metrics grid */}
                    <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:6, marginBottom:10 }}>
                      {[
                        { Icon:Zap,         label:"Cost/bbl", val:`₹${(rec.estimated_cost_usd_per_bbl * (market?.usd_inr || 83.42)).toFixed(2)}/bbl`, color:"#3b82f6" },
                        { Icon:ShieldAlert, label:"Risk",     val:`${rec.corridor_risk_score.toFixed(0)}/100`,          color: rec.corridor_risk_score>60?"#ef4444":rec.corridor_risk_score>30?"#f59e0b":"#10b981" },
                        { Icon:Clock,       label:"Transit",  val:`${rec.transit_days}d`,                               color:"#8b5cf6" },
                      ].map(({ Icon, label, val, color }) => (
                        <div key={label} style={{ background:"#f8fafc", padding:"7px 8px", borderRadius:7, border:"1px solid #f1f5f9" }}>
                          <div style={{ display:"flex", alignItems:"center", gap:3, fontSize:9, color:"#94a3b8", marginBottom:3 }}>
                            <Icon size={9} color={color}/> {label}
                          </div>
                          <div style={{ fontSize:12, fontWeight:700, color:"#0f172a", fontVariantNumeric:"tabular-nums" }}>{val}</div>
                        </div>
                      ))}
                    </div>

                    {/* Reasoning */}
                    <p style={{ fontSize:10, lineHeight:1.6, color:"#64748b", margin:0, borderTop:"1px solid #f1f5f9", paddingTop:8 }}>
                      {rec.reasoning}
                    </p>
                  </div>
                );
              })
            )}

            {/* Baseline comparison card */}
            {baseline && (
              <div style={{ marginTop:8, padding:"12px 14px", borderRadius:12, background:"#f8fafc", border:"1px dashed #cbd5e1" }}>
                <div style={{ fontSize:9, fontWeight:700, color:"#94a3b8", textTransform:"uppercase", letterSpacing:"0.07em", marginBottom:8 }}>Current Baseline</div>
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                  <div>
                    <div style={{ fontSize:12, fontWeight:700, color:"#374151" }}>{NODE_LABELS[baseline.supplier]||baseline.supplier}</div>
                    <div style={{ fontSize:9, color:"#94a3b8", marginTop:2 }}>Score: {baseline.composite_score.toFixed(3)}</div>
                  </div>
                  <div style={{ display:"flex", gap:10, fontSize:11, color:"#64748b", fontVariantNumeric:"tabular-nums" }}>
                    <span>₹{(baseline.estimated_cost_usd_per_bbl * (market?.usd_inr || 83.42)).toFixed(2)}/bbl</span>
                    <span>Risk {baseline.corridor_risk_score}</span>
                    <span>{baseline.transit_days}d</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
