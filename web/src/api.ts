import type { RegionPayload } from './types'

const BASE = ((import.meta.env.VITE_API_URL as string | undefined) ?? '').replace(/\/$/, '')
const KEY = 'bulwark-token'

export const tokenStore = {
  get: () => { try { return localStorage.getItem(KEY) } catch { return null } },
  set: (t: string) => { try { localStorage.setItem(KEY, t) } catch { /* private mode */ } },
  clear: () => { try { localStorage.removeItem(KEY) } catch { /* ignore */ } },
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) { super(message); this.status = status }
}

async function req<T>(path: string, o: { method?: string; body?: unknown; token?: string | null; timeoutMs?: number } = {}): Promise<T> {
  const ctl = new AbortController()
  const timer = setTimeout(() => ctl.abort(), o.timeoutMs ?? 20000)
  try {
    const res = await fetch(`${BASE}${path}`, {
      method: o.method ?? 'GET', signal: ctl.signal,
      headers: { 'Content-Type': 'application/json', ...(o.token ? { Authorization: `Bearer ${o.token}` } : {}) },
      body: o.body ? JSON.stringify(o.body) : undefined,
    })
    const json = await res.json().catch(() => ({}))
    if (!res.ok) throw new ApiError(res.status, (json as { error?: string }).error ?? `HTTP ${res.status}`)
    return json as T
  } finally { clearTimeout(timer) }
}

export type Config = {
  stripe: boolean; testMode: boolean; demo: boolean; mail: boolean
  price: { amount: number; currency: string; interval: string }
  regions: { id: string; name: string; currency: string; asof: string }[]
}
export type Session = { token: string; plan: 'demo' | 'premium'; email?: string | null }

/** The free Render tier sleeps; the first request can take ~1 minute. Retry while telling the UI we're waking it. */
export async function getConfig(onWaking: () => void): Promise<Config> {
  const started = Date.now()
  for (let i = 0; ; i++) {
    try { return await req<Config>('/api/config', { timeoutMs: 15000 }) }
    catch (e) {
      if (e instanceof ApiError && e.status < 500 && e.status !== 0) throw e
      if (Date.now() - started > 100000) throw e
      onWaking()
      await new Promise((r) => setTimeout(r, 2500))
    }
  }
}

export const api = {
  demo: () => req<Session>('/api/demo/start', { method: 'POST' }),
  checkout: (email?: string) => req<{ url: string }>('/api/checkout', { method: 'POST', body: { email } }),
  confirm: (session_id: string) => req<Session>('/api/checkout/confirm', { method: 'POST', body: { session_id } }),
  loginLink: (email: string) => req<{ ok: boolean }>('/api/login-link', { method: 'POST', body: { email } }),
  verify: (token: string) => req<Session>('/api/login/verify', { method: 'POST', body: { token } }),
  region: (id: string, token: string) => req<RegionPayload>(`/api/region/${id}`, { token, timeoutMs: 30000 }),
  portal: (token: string) => req<{ url: string }>('/api/portal', { method: 'POST', token }),
}
