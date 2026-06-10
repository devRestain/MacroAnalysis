const API_BASE = import.meta.env.VITE_API_URL || '/api'
const API_ACCESS_KEY = import.meta.env.VITE_API_ACCESS_KEY || ''

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) throw new Error(`API ${path}: ${res.status}`)
  return res.json()
}

export const api = {
  summary: () => apiFetch<SummaryResponse>('/summary'),
  changes: (category?: string) =>
    apiFetch<ChangesResponse>(`/changes${category ? `?category=${category}` : ''}`),
  chart: (key: string, period: string) =>
    apiFetch<ChartResponse>(`/chart/${encodeURIComponent(key)}?period=${period}`),
  news: (category?: string, limit = 30) =>
    apiFetch<NewsResponse>(`/news?limit=${limit}${category ? `&category=${category}` : ''}`),
  sectors: () => apiFetch<SectorsResponse>('/sectors'),
  fomc: () => apiFetch<FomcResponse>('/fomc'),
  aiSummary: () => apiFetch<AiSummaryResponse>('/ai/summary'),
  aiChat: (message: string) =>
    apiFetch<ChatResponse>('/ai/chat', {
      method: 'POST',
      headers: API_ACCESS_KEY ? { 'X-API-Key': API_ACCESS_KEY } : undefined,
      body: JSON.stringify({ message }),
    }),
}

// Types
export interface Snapshot {
  key: string
  label: string
  category: string
  value: number | null
  unit: string | null
  delta_1d: number | null
  delta_1d_pct: number | null
  delta_1w_pct: number | null
  delta_1m_pct: number | null
  delta_3m_pct: number | null
  z_score_1y: number | null
  direction: 'up' | 'down' | 'flat'
  signal: 'green' | 'yellow' | 'red'
  date: string
}

export interface SummaryResponse {
  updated_at: string
  alerts: Snapshot[]
  snapshots: Record<string, Snapshot>
  equities: Record<string, { close: number; change_pct: number; date: string }>
  yield_curve: Record<string, number>
  fomc: {
    next_date: string | null
    days_left: number | null
    prob_hold: number | null
    prob_cut: number | null
    prob_hike: number | null
    prob_method: string | null
  }
  ai_headline: string | null
  news_preview: NewsItem[]
}

export interface ChangesResponse {
  changes: Snapshot[]
}

export interface ChartResponse {
  indicator_key: string
  period: string
  data: { date: string; value: number }[]
}

export interface NewsItem {
  id: number
  source: string
  title: string
  summary: string | null
  url: string | null
  category: string
  published_at: string | null
}

export interface NewsResponse {
  news: NewsItem[]
}

export interface SectorRow {
  ticker: string
  name: string
  change_1d: number | null
  change_1m: number | null
  change_3m: number | null
  change_ytd: number | null
  date: string
}

export interface SectorsResponse {
  sectors: SectorRow[]
}

export interface FomcResponse {
  meetings: { date: string; rate: number | null; change_bp: number | null }[]
  fedwatch: { prob_hold: number | null; prob_cut: number | null; prob_hike: number | null; prob_method: string | null } | null
}

export interface AiSummaryResponse {
  date: string
  headline: string | null
  body: string
  model: string
}

export interface ChatResponse {
  reply: string
}
