import { useState, useEffect, useCallback } from 'react';
import { loadMarket, loadCorridors, compositeIndex } from './live-data';
import type { MarketData, LiveCorridor } from './live-data';

export interface GlobalDataState {
  market: MarketData | null;
  corridors: LiveCorridor[];
  compositeRisk: number;
  marketLive: boolean;
  corridorsLive: boolean;
  loading: boolean;
  error: string | null;
  lastUpdated: string | null;
}

export function useLiveData(pollingIntervalMs = 60000) {
  const [state, setState] = useState<GlobalDataState>({
    market: null,
    corridors: [],
    compositeRisk: 0,
    marketLive: false,
    corridorsLive: false,
    loading: true,
    error: null,
    lastUpdated: null
  });

  const refresh = useCallback(async () => {
    setState(s => ({ ...s, loading: true, error: null }));
    try {
      const [marketRes, corridorsRes] = await Promise.all([
        loadMarket(),
        loadCorridors()
      ]);

      const composite = corridorsRes.data.length ? compositeIndex(corridorsRes.data) : 0;

      setState({
        market: marketRes.data,
        corridors: corridorsRes.data,
        compositeRisk: composite,
        marketLive: marketRes.is_live,
        corridorsLive: corridorsRes.is_live,
        loading: false,
        error: null,
        lastUpdated: new Date().toISOString()
      });
    } catch (err: any) {
      setState(s => ({
        ...s,
        loading: false,
        error: err.message || "Failed to load live data",
      }));
    }
  }, []);

  useEffect(() => {
    refresh();
    const intervalId = setInterval(refresh, pollingIntervalMs);
    return () => clearInterval(intervalId);
  }, [refresh, pollingIntervalMs]);

  return { ...state, refresh };
}
