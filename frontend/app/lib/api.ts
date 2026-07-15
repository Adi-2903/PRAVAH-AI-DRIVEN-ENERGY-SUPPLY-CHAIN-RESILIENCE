// ═══════════════════════════════════════════════
//  PRAVAH — Central API client
//  One place that knows every service's base URL. URLs come from NEXT_PUBLIC_*
//  env vars (see .env.example). In production every var points at the single
//  monolith backend (api.py); locally they default to per-agent dev ports.
//  Every module fetches through here instead of hardcoding host:port, so
//  ports/deploy targets change in ONE place and every call has a fallback.
// ═══════════════════════════════════════════════

import { fetchWithFallback } from './mock-data';

export type Service = 'risk' | 'scenario' | 'procurement' | 'spr' | 'coordinator';

// Default base is the same-origin "/api" — on Vercel the backend runs as a
// Python Function at /api/*, so with NO env config the browser calls
// /api/simulate, /api/corridors, ... (same origin ⇒ no CORS). Override any
// service via NEXT_PUBLIC_*_URL for split hosting or local dev (e.g. set them
// to http://127.0.0.1:8000 in frontend/.env.local to hit a local uvicorn).
const SERVICE_BASE: Record<Service, string> = {
  risk:        process.env.NEXT_PUBLIC_RISK_URL        ?? '/api',
  scenario:    process.env.NEXT_PUBLIC_SCENARIO_URL    ?? '/api',
  procurement: process.env.NEXT_PUBLIC_PROCUREMENT_URL ?? '/api',
  spr:         process.env.NEXT_PUBLIC_SPR_URL         ?? '/api',
  coordinator: process.env.NEXT_PUBLIC_COORDINATOR_URL ?? '/api',
};

/** Build a fully-qualified URL for a service endpoint. */
export function serviceUrl(service: Service, path: string): string {
  const base = (SERVICE_BASE[service] ?? '').replace(/\/$/, '');
  if (!base && typeof console !== 'undefined') {
    console.warn(`[api] no base URL configured for service "${service}" — falling back to a relative path.`);
  }
  return `${base}${path.startsWith('/') ? path : `/${path}`}`;
}

/**
 * POST JSON to a service, returning parsed data or throwing on non-2xx.
 * Use this when the caller wants to run its own catch/fallback logic.
 */
export async function postJSON<T>(service: Service, path: string, body: unknown): Promise<T> {
  const res = await fetch(serviceUrl(service, path), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(8000),
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try { const e = await res.json(); detail = e.detail || detail; } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

/**
 * POST with a guaranteed result: falls back to `fallback` (typically a mock
 * matching the frozen schema) on any network/HTTP error. Never throws.
 * Returns { data, is_live, as_of } so the UI can badge live vs. fallback.
 */
export async function postWithFallback<T>(
  service: Service,
  path: string,
  body: unknown,
  fallback: T,
): Promise<{ data: T; is_live: boolean; as_of: string }> {
  return fetchWithFallback<T>(serviceUrl(service, path), fallback, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

/** GET with a guaranteed result. Never throws. */
export async function getWithFallback<T>(
  service: Service,
  path: string,
  fallback: T,
): Promise<{ data: T; is_live: boolean; as_of: string }> {
  return fetchWithFallback<T>(serviceUrl(service, path), fallback);
}
