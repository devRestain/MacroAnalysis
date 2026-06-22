import { getActiveLocale } from '../i18n'

export type ApiErrorKind =
  | 'network'
  | 'not_found'
  | 'unauthorized'
  | 'forbidden'
  | 'rate_limited'
  | 'server'
  | 'disabled'
  | 'empty'
  | 'unknown'

export class ApiError extends Error {
  status?: number
  kind: ApiErrorKind

  constructor(message: string, kind: ApiErrorKind = 'unknown', status?: number) {
    super(message)
    this.name = 'ApiError'
    this.kind = kind
    this.status = status
  }
}

const API_BASE = import.meta.env.VITE_API_URL || '/api'
const API_ACCESS_KEY = import.meta.env.VITE_API_ACCESS_KEY || ''

function classifyStatus(status: number, detail?: string): ApiErrorKind {
  const normalized = detail?.toLowerCase() ?? ''
  if (status === 401) return 'unauthorized'
  if (status === 403) return 'forbidden'
  if (status === 404) return 'not_found'
  if (status === 429) return 'rate_limited'
  if (status === 503 || normalized.includes('not configured') || normalized.includes('disabled')) return 'disabled'
  if (status >= 500) return 'server'
  return 'unknown'
}

async function parseJson<T>(res: Response): Promise<T> {
  const text = await res.text()
  if (!text) return undefined as T
  return JSON.parse(text) as T
}

function withLocaleQuery(path: string): string {
  if (/(^|[?&])lang=/.test(path)) return path
  const separator = path.includes('?') ? '&' : '?'
  return `${path}${separator}lang=${encodeURIComponent(getActiveLocale())}`
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json')
  }

  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  } catch (error) {
    throw new ApiError(error instanceof Error ? error.message : 'Network request failed', 'network')
  }

  if (!res.ok) {
    let detail = ''
    try {
      const body = await parseJson<{ detail?: string }>(res)
      detail = body?.detail ?? ''
    } catch {
      detail = await res.text().catch(() => '')
    }
    throw new ApiError(detail || `API ${path}: ${res.status}`, classifyStatus(res.status, detail), res.status)
  }

  return parseJson<T>(res)
}

export function apiGet<T>(path: string): Promise<T> {
  return apiRequest<T>(withLocaleQuery(path))
}

export function apiPost<T>(path: string, body: unknown, options: RequestInit = {}): Promise<T> {
  return apiRequest<T>(path, {
    method: 'POST',
    body: JSON.stringify(body),
    ...options,
  })
}

export function aiChatHeaders(): HeadersInit | undefined {
  return API_ACCESS_KEY ? { 'X-API-Key': API_ACCESS_KEY } : undefined
}

export async function optionalApi<T>(request: () => Promise<T>): Promise<T | ApiError> {
  try {
    return await request()
  } catch (error) {
    if (error instanceof ApiError) return error
    return new ApiError(error instanceof Error ? error.message : 'Unknown optional API error', 'unknown')
  }
}
