import type { ChannelAccount, ChannelsResponse, Company, CompanyDetail, Session, User } from '../types'

const ACCESS_KEY = 'icrm.access'
const REFRESH_KEY = 'icrm.refresh'

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

function read(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

export const tokens = {
  get access() {
    return read(ACCESS_KEY)
  },
  get refresh() {
    return read(REFRESH_KEY)
  },
  set(access: string, refresh: string) {
    try {
      localStorage.setItem(ACCESS_KEY, access)
      localStorage.setItem(REFRESH_KEY, refresh)
    } catch {
      /* storage unavailable: session lasts until reload */
    }
  },
  clear() {
    try {
      localStorage.removeItem(ACCESS_KEY)
      localStorage.removeItem(REFRESH_KEY)
    } catch {
      /* ignore */
    }
  },
}

let onSessionExpired: () => void = () => {}
export function setSessionExpiredHandler(fn: () => void) {
  onSessionExpired = fn
}

interface Envelope<T> {
  success: boolean
  data?: T
  error?: string
}

async function send<T>(path: string, init: RequestInit, auth: boolean): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  if (init.body) headers.set('Content-Type', 'application/json')
  if (auth && tokens.access) headers.set('Authorization', `Bearer ${tokens.access}`)

  let res: Response
  try {
    res = await fetch(`/api/v1${path}`, { ...init, headers })
  } catch {
    throw new ApiError('Cannot reach the server. Is the API running?', 0)
  }
  const body = (await res.json().catch(() => null)) as Envelope<T> | null
  if (!res.ok || !body?.success) {
    throw new ApiError(body?.error ?? `Request failed (${res.status})`, res.status)
  }
  return body.data as T
}

let refreshing: Promise<boolean> | null = null

async function refreshTokens(): Promise<boolean> {
  const refresh = tokens.refresh
  if (!refresh) return false
  try {
    const s = await send<Session>('/auth/refresh', { method: 'POST', body: JSON.stringify({ refresh_token: refresh }) }, false)
    tokens.set(s.access_token, s.refresh_token)
    return true
  } catch {
    return false
  }
}

/** Authenticated request; on 401 refreshes the token once and retries. */
async function authed<T>(path: string, init: RequestInit = {}): Promise<T> {
  try {
    return await send<T>(path, init, true)
  } catch (e) {
    if (!(e instanceof ApiError) || e.status !== 401) throw e
    refreshing ??= refreshTokens().finally(() => (refreshing = null))
    if (await refreshing) return send<T>(path, init, true)
    tokens.clear()
    onSessionExpired()
    throw e
  }
}

export const api = {
  login: (email: string, password: string) =>
    send<Session>('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }, false),
  me: () => authed<{ user: User; companies: Company[] }>('/auth/me'),
  companies: () => authed<Company[]>('/companies'),
  company: (id: string) => authed<CompanyDetail>(`/companies/${id}`),
  channels: (companyId: string) => authed<ChannelsResponse>(`/companies/${companyId}/channels`),
  connectInstagram: (companyId: string) =>
    authed<{ authorize_url: string }>(`/companies/${companyId}/channels/instagram/connect`, { method: 'POST' }),
  disconnectInstagram: (companyId: string, accountId: string) =>
    authed<ChannelAccount>(`/companies/${companyId}/channels/instagram/${accountId}`, { method: 'DELETE' }),
}
