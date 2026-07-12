// ═══════════════════════════════════════════════
//  PRAVAH — Central API client
//  One place that knows every microservice's base URL. URLs come from
//  NEXT_PUBLIC_* env vars (see .env.example); defaults match docker-compose.
//  Every module fetches through here instead of hardcoding host:port, so
//  ports/deploy targets change in ONE place and every call has a fallback.
// ═══════════════════════════════════════════════

import { fetchWithFallback } from './mock-data';

export type Service = 'risk' | 'scenario' | 'procurement' | 'spr' | 'coordinator';

// Defaults align with docker-compose.yml host port mappings.
// A standalone `uvicorn` agent defaults to :8000 — override per-service via env.
const SERVICE_BASE: Record<Service, string> = {
  risk:        process.env.NEXT_PUBLIC_RISK_URL        ?? 'http://127.0.0.1:8001',
  scenario:    process.env.NEXT_PUBLIC_SCENARIO_URL    ?? 'http://127.0.0.1:8002',
  procurement: process.env.NEXT_PUBLIC_PROCUREMENT_URL ?? 'http://127.0.0.1:8003',
  spr:         process.env.NEXT_PUBLIC_SPR_URL         ?? 'http://127.0.0.1:8004',
  coordinator: process.env.NEXT_PUBLIC_COORDINATOR_URL ?? 'http://127.0.0.1:8005',
};

/** Build a fully-qualified URL for a service endpoint. */
export function serviceUrl(service: Service, path: string): string {
  const base = SERVICE_BASE[service].replace(/\/$/, '');
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
