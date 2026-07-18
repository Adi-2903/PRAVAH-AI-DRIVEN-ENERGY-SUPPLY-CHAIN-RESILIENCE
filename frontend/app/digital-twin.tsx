"use client";

import React, { useState, useEffect } from 'react';
import { ComposableMap, Geographies, Geography, Marker, Line as RSMLine, ZoomableGroup } from 'react-simple-maps';
import { Activity, Shield, Droplet, Anchor, Server, Zap, Radio, AlertTriangle, Cpu, Network, CheckCircle2, Navigation } from 'lucide-react';
import DataFreshness from './components/data-freshness';
import { serviceUrl } from './lib/api';
import { useLiveData } from './lib/use-live-data';

const geoUrl = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

interface Asset {
  id: string;
  name: string;
  type: 'refinery' | 'spr' | 'port' | 'vessel';
  coordinates: [number, number];
  status: 'optimal' | 'warning' | 'critical' | 'offline';
  capacity: string;
  utilization: number;
}

const FALLBACK_ASSETS: Asset[] = [
  // Refineries
  { id: 'ref-jamnagar', name: 'Jamnagar Complex', type: 'refinery', coordinates: [69.96, 22.34], status: 'optimal', capacity: '1.24M bpd', utilization: 92 },
  { id: 'ref-mumbai', name: 'Mumbai Refinery', type: 'refinery', coordinates: [72.87, 19.07], status: 'warning', capacity: '240K bpd', utilization: 78 },
  { id: 'ref-kochi', name: 'Kochi Refinery', type: 'refinery', coordinates: [76.35, 9.96], status: 'optimal', capacity: '310K bpd', utilization: 88 },
  // SPRs
  { id: 'spr-mangalore', name: 'Mangalore SPR', type: 'spr', coordinates: [74.85, 12.87], status: 'optimal', capacity: '11M bbl', utilization: 95 },
  { id: 'spr-padur', name: 'Padur SPR', type: 'spr', coordinates: [74.78, 13.16], status: 'warning', capacity: '18M bbl', utilization: 60 },
  { id: 'spr-vizag', name: 'Visakhapatnam SPR', type: 'spr', coordinates: [83.31, 17.68], status: 'optimal', capacity: '9M bbl', utilization: 100 },
  // Ports
  { id: 'port-sikka', name: 'Sikka Ports & Terminals', type: 'port', coordinates: [69.82, 22.43], status: 'optimal', capacity: '4x VLCC', utilization: 85 },
  // Vessels
  { id: 'ves-oceanic', name: 'VLCC Oceanic', type: 'vessel', coordinates: [63.2, 24.1], status: 'optimal', capacity: '2M bbl', utilization: 100 },
  { id: 'ves-horizon', name: 'Suezmax Horizon', type: 'vessel', coordinates: [52.1, 14.5], status: 'critical', capacity: '1M bbl', utilization: 100 },
  { id: 'ves-pacific', name: 'Aframax Pacific', type: 'vessel', coordinates: [95.2, 5.8], status: 'optimal', capacity: '600K bbl', utilization: 100 },
];

const FALLBACK_ROUTES = [
  { from: [50.1, 26.5], to: [69.82, 22.43], id: 'route-hormuz' }, // Ras Tanura to Sikka
  { from: [43.2, 12.5], to: [72.87, 19.07], id: 'route-bab' }, // Bab-el-Mandeb to Mumbai
  { from: [100.1, 3.2], to: [83.31, 17.68], id: 'route-malacca' }, // Malacca to Vizag
];

export default function DigitalTwin() {
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [telemetryTick, setTelemetryTick] = useState(0);
  const [assets, setAssets] = useState<Asset[]>(FALLBACK_ASSETS);
  const [routes, setRoutes] = useState<any[]>(FALLBACK_ROUTES);

  const { corridors, lastUpdated, loading: liveLoading } = useLiveData();

  useEffect(() => {
    let active = true;
    const fetchData = async () => {
      try {
        const token = localStorage.getItem('pravah_access_token');
        const headers: Record<string, string> = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;
        
        const [graphRes, fleetRes] = await Promise.all([
          fetch(serviceUrl('shared', '/graph'), { headers, signal: AbortSignal.timeout(4000) }).catch(() => null),
          fetch(serviceUrl('shared', '/fleet'), { headers, signal: AbortSignal.timeout(4000) }).catch(() => null)
        ]);
        
        let newAssets: Asset[] = [];
        let newRoutes: any[] = [];
        const nodeCoordsMap = new Map<string, [number, number]>();

        if (graphRes?.ok) {
          const graphData = await graphRes.json();
          graphData.nodes?.forEach((n: any) => {
            if (n.lat !== undefined && n.lon !== undefined) {
              nodeCoordsMap.set(n.id, [n.lon, n.lat]);
              let type: Asset['type'] = 'vessel'; // default fallback for strict type, replaced below
              if (n.type === 'supplier' || n.type === 'port' || n.type === 'refinery' || n.type === 'spr') type = n.type as Asset['type'];
              else type = 'vessel'; // server not allowed by Asset type, let's just use vessel or refinery. Actually Asset allows 'refinery' | 'spr' | 'port' | 'vessel'
              
              if (n.type === 'supplier') type = 'port';
              
              newAssets.push({
                id: n.id,
                name: n.display || n.id,
                type: type,
                coordinates: [n.lon, n.lat],
                status: 'optimal',
                capacity: n.capacity ? String(n.capacity) : 'N/A',
                utilization: n.current_utilization || 0
              });
            }
          });
          
          graphData.edges?.forEach((e: any) => {
            const f = nodeCoordsMap.get(e.source);
            const t = nodeCoordsMap.get(e.target);
            if (f && t) {
              newRoutes.push({ from: f, to: t, id: `${e.source}-${e.target}` });
            }
          });
        }
        
        if (fleetRes?.ok) {
          const fleetData = await fleetRes.json();
          fleetData.fleet?.forEach((v: any) => {
            newAssets.push({
              id: v.id,
              name: v.id,
              type: 'vessel',
              coordinates: [v.lon, v.lat],
              status: v.risk > 60 ? 'critical' : (v.risk > 40 ? 'warning' : 'optimal'),
              capacity: '2M bbl',
              utilization: 100
            });
          });
        }
        
        if (active && newAssets.length > 0) {
          setAssets(newAssets);
          if (newRoutes.length > 0) setRoutes(newRoutes);
        }
      } catch (e) {
        console.warn("Telemetry fetch failed", e);
      }
    };
    
    fetchData();
    const t = setInterval(fetchData, 30000);
    return () => { active = false; clearInterval(t); };
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setTelemetryTick(t => t + 1);
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: Asset['status']) => {
    switch (status) {
      case 'optimal': return '#34d399';
      case 'warning': return '#fbbf24';
      case 'critical': return '#ef4444';
      case 'offline': return '#64748b';
      default: return '#3b82f6';
    }
  };

  const getIcon = (type: Asset['type'], color: string) => {
    switch (type) {
      case 'refinery': return <Activity style={{ width: 14, height: 14, color }} />;
      case 'spr': return <Shield style={{ width: 14, height: 14, color }} />;
      case 'port': return <Anchor style={{ width: 14, height: 14, color }} />;
      case 'vessel': return <Navigation style={{ width: 14, height: 14, color }} fill={color} />;
      default: return <Server style={{ width: 14, height: 14, color }} />;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#020617', color: '#f8fafc', overflow: 'hidden' }}>
      
      {/* Header */}
      <div style={{ padding: '24px 32px', borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(2,6,23,0.8)', backdropFilter: 'blur(12px)', zIndex: 10 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, fontFamily: 'var(--font-display)', display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Cpu style={{ width: 20, height: 20, color: '#3b82f6' }} />
            </div>
            Digital Twin Telemetry
          </h1>
          <p style={{ fontSize: 13, color: '#94a3b8', marginTop: 8, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 8 }}>
            Real-time geospatial state mirror of physical infrastructure and logistics. <span className="badge badge-info" style={{ marginLeft: 6 }}>{telemetryTick % 2 === 0 ? 'SYNCING...' : 'SYNCED'}</span>
          </p>
        </div>
        <div style={{ display: 'flex', gap: 16 }}>
          {['optimal', 'warning', 'critical'].map(s => (
            <div key={s} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'rgba(255,255,255,0.6)' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: getStatusColor(s as any) }} />
              {s}
            </div>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        
        {/* Sidebar */}
        <div style={{ width: 340, background: '#0f172a', borderRight: '1px solid rgba(255,255,255,0.06)', overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '20px 24px', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#64748b', marginBottom: 16 }}>System Node Status</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {assets.map((asset) => (
                <div 
                  key={asset.id} 
                  onClick={() => setSelectedAsset(asset)}
                  style={{ 
                    padding: 12, borderRadius: 10, background: selectedAsset?.id === asset.id ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.02)', 
                    border: `1px solid ${selectedAsset?.id === asset.id ? 'rgba(255,255,255,0.2)' : 'rgba(255,255,255,0.05)'}`,
                    cursor: 'pointer', transition: 'all 0.2s',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{ width: 32, height: 32, borderRadius: 8, background: `${getStatusColor(asset.status)}20`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      {getIcon(asset.type, getStatusColor(asset.status))}
                    </div>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc' }}>{asset.name}</div>
                      <div style={{ fontSize: 11, color: '#94a3b8', textTransform: 'capitalize', marginTop: 2 }}>{asset.type}</div>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 12, fontWeight: 800, fontFamily: 'var(--font-mono)', color: getStatusColor(asset.status) }}>{asset.utilization}%</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          {selectedAsset && (
            <div style={{ padding: 24, flex: 1, background: 'linear-gradient(180deg, rgba(15,23,42,1) 0%, rgba(2,6,23,1) 100%)' }}>
              <div style={{ fontSize: 10, fontWeight: 800, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#60a5fa', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
                <Radio style={{ width: 12, height: 12 }} /> Live Telemetry
              </div>
              <h3 style={{ fontSize: 20, fontWeight: 800, color: '#fff', marginBottom: 4 }}>{selectedAsset.name}</h3>
              <p style={{ fontSize: 12, color: '#94a3b8', textTransform: 'capitalize', marginBottom: 20 }}>{selectedAsset.type} Node</p>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 24 }}>
                <div style={{ background: 'rgba(255,255,255,0.03)', padding: 12, borderRadius: 8, border: '1px solid rgba(255,255,255,0.05)' }}>
                  <div style={{ fontSize: 10, color: '#64748b', fontWeight: 600, textTransform: 'uppercase', marginBottom: 4 }}>Status</div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: getStatusColor(selectedAsset.status), textTransform: 'uppercase' }}>{selectedAsset.status}</div>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.03)', padding: 12, borderRadius: 8, border: '1px solid rgba(255,255,255,0.05)' }}>
                  <div style={{ fontSize: 10, color: '#64748b', fontWeight: 600, textTransform: 'uppercase', marginBottom: 4 }}>Capacity</div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc', fontFamily: 'var(--font-mono)' }}>{selectedAsset.capacity}</div>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.03)', padding: 12, borderRadius: 8, border: '1px solid rgba(255,255,255,0.05)', gridColumn: 'span 2' }}>
                  <div style={{ fontSize: 10, color: '#64748b', fontWeight: 600, textTransform: 'uppercase', marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
                    <span>Utilization</span>
                    <span>{selectedAsset.utilization}%</span>
                  </div>
                  <div className="risk-bar-track" style={{ height: 6, background: 'rgba(255,255,255,0.1)' }}>
                    <div style={{ width: `${selectedAsset.utilization}%`, height: '100%', background: getStatusColor(selectedAsset.status), borderRadius: 10, transition: 'width 1s ease-in-out' }} />
                  </div>
                </div>
              </div>
              
              {selectedAsset.status === 'critical' && (
                <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)', padding: 16, borderRadius: 10 }}>
                  <div style={{ display: 'flex', gap: 10, color: '#f87171', fontSize: 12, fontWeight: 600, lineHeight: 1.5 }}>
                    <AlertTriangle style={{ width: 16, height: 16, flexShrink: 0 }} />
                    Anomaly detected. Asset operating outside safety envelope. Requires immediate operator intervention.
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Map Container */}
        <div style={{ flex: 1, position: 'relative', background: 'radial-gradient(circle at center, #0f172a 0%, #020617 100%)' }}>
          
          <ComposableMap projection="geoMercator" projectionConfig={{ scale: 150 }} style={{ width: '100%', height: '100%' }}>
            <ZoomableGroup center={[20, 20]} zoom={1.2}>
              <Geographies geography={geoUrl}>
                {({ geographies }) =>
                  geographies.map((geo) => (
                    <Geography 
                      key={geo.rsmKey} 
                      geography={geo} 
                      fill="#1e293b" 
                      stroke="#475569" 
                      strokeWidth={1.5} 
                      style={{
                        default: { outline: 'none' },
                        hover: { fill: '#334155', outline: 'none' },
                        pressed: { outline: 'none' },
                      }}
                    />
                  ))
                }
              </Geographies>

              {/* Shipping Routes */}
              {routes.map((route) => (
                <RSMLine
                  key={route.id}
                  from={route.from as [number, number]}
                  to={route.to as [number, number]}
                  stroke="rgba(52, 211, 153, 0.4)"
                  strokeWidth={2}
                  strokeDasharray="4 4"
                  strokeLinecap="round"
                />
              ))}

              {/* Assets / Nodes */}
              {assets.map((asset) => {
                const color = getStatusColor(asset.status);
                const isSelected = selectedAsset?.id === asset.id;
                return (
                  <Marker key={asset.id} coordinates={asset.coordinates} onClick={() => setSelectedAsset(asset)} style={{ default: { cursor: 'pointer' }, hover: { cursor: 'pointer' }, pressed: { cursor: 'pointer' } }}>
                    {isSelected && (
                      <circle cx={0} cy={0} r={12} fill="none" stroke={color} strokeWidth={1} strokeDasharray="2 2" className="animate-spin-slow" />
                    )}
                    <circle cx={0} cy={0} r={5} fill={color} stroke="#020617" strokeWidth={1.5} />
                    {asset.status === 'critical' && (
                      <circle cx={0} cy={0} r={9} fill="none" stroke={color} strokeWidth={1.5} className="pulse-dot" />
                    )}
                    <text 
                      textAnchor="middle" 
                      y={-12} 
                      style={{ 
                        fontFamily: 'system-ui', fontSize: isSelected ? 12 : 9, fill: isSelected ? '#fff' : 'rgba(255,255,255,0.6)', 
                        fontWeight: isSelected ? 800 : 600, pointerEvents: 'none', filter: 'drop-shadow(0px 2px 4px rgba(0,0,0,0.8))'
                      }}
                    >
                      {asset.name}
                    </text>
                  </Marker>
                );
              })}
            </ZoomableGroup>
          </ComposableMap>

          {/* HUD Overlay */}
          <div style={{ position: 'absolute', top: 24, right: 24, background: 'rgba(15,23,42,0.8)', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.1)', padding: 16, borderRadius: 12, width: 220 }}>
            <div style={{ fontSize: 10, fontWeight: 800, textTransform: 'uppercase', color: '#94a3b8', marginBottom: 12 }}>Network Health</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 12, color: '#f8fafc', fontWeight: 600 }}>Data Integrity</span>
                <span style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: '#34d399', fontWeight: 700 }}>99.9%</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 12, color: '#f8fafc', fontWeight: 600 }}>Latency</span>
                <span style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: '#60a5fa', fontWeight: 700 }}>24ms</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 12, color: '#f8fafc', fontWeight: 600 }}>Active Nodes</span>
                <span style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: '#f8fafc', fontWeight: 700 }}>1,204</span>
              </div>
            </div>
          </div>

        </div>
      </div>
      
      {/* Footer / Telemetry stream */}
      <div style={{ height: 32, background: '#020617', borderTop: '1px solid rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', padding: '0 24px', fontSize: 10, fontFamily: 'var(--font-mono)', color: '#64748b', gap: 24 }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#34d399' }}><CheckCircle2 style={{ width: 12, height: 12 }} /> SECURE CONNECTION</span>
        {/* eslint-disable-next-line react-hooks/purity */}
        <span>ID: TWIN-{Math.random().toString(36).substring(2,8).toUpperCase()}</span>
        <span>UPTIME: 99.99%</span>
        <span>LAT: 22.34 LON: 69.96</span>
        <span style={{ flex: 1, textAlign: 'right', color: '#3b82f6' }}>AWAITING COMMAND OVERRIDE...</span>
      </div>
    </div>
  );
}
