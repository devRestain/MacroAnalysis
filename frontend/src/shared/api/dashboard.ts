import { ChangeSnapshot } from '../../entities/changeSnapshot/types'
import { NewsItem } from '../../entities/news/types'
import { apiGet } from './client'

interface SnapshotResponse {
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
  signal: 'green' | 'yellow' | 'red' | string
  date: string | null
}

interface NewsResponseItem {
  id: number
  source: string
  title: string
  summary: string | null
  url: string | null
  category: string
  published_at: string | null
}

interface DashboardSummaryResponse {
  updated_at?: string | null
  alerts?: SnapshotResponse[]
  snapshots?: Record<string, SnapshotResponse>
  equities?: Record<string, { close?: number | null; change_pct?: number | null; date?: string | null }>
  yield_curve?: Record<string, number | null>
  fomc?: {
    next_date?: string | null
    days_left?: number | null
    prob_hold?: number | null
    prob_cut?: number | null
    prob_hike?: number | null
    prob_method?: string | null
  }
  ai_headline?: string | null
  ai_as_of_date?: string | null
  news_preview?: NewsResponseItem[]
}

interface ChangesResponse {
  changes?: SnapshotResponse[]
}

interface SectorsResponse {
  sectors?: SectorRowResponse[]
}

export interface EquitySnapshot {
  close?: number | null
  changePct?: number | null
  date?: string | null
}

export interface SectorRow {
  ticker: string
  name: string
  change1d: number | null
  change1m: number | null
  change3m: number | null
  changeYtd: number | null
  date: string | null
}

interface SectorRowResponse {
  ticker: string
  name: string
  change_1d: number | null
  change_1m: number | null
  change_3m: number | null
  change_ytd: number | null
  date: string | null
}

export interface DashboardSummary {
  updatedAt?: string | null
  alerts: ChangeSnapshot[]
  snapshots: Record<string, ChangeSnapshot>
  equities: Record<string, EquitySnapshot>
  yieldCurve: Record<string, number | null>
  fomc?: {
    nextDate?: string | null
    daysLeft?: number | null
    probHold?: number | null
    probCut?: number | null
    probHike?: number | null
    probMethod?: string | null
  }
  aiHeadline?: string | null
  aiAsOfDate?: string | null
  newsPreview: NewsItem[]
}

export function normalizeSnapshot(row: SnapshotResponse): ChangeSnapshot {
  return {
    key: row.key,
    label: row.label,
    category: row.category,
    value: row.value,
    unit: row.unit,
    delta1d: row.delta_1d,
    delta1dPct: row.delta_1d_pct,
    delta1wPct: row.delta_1w_pct,
    delta1mPct: row.delta_1m_pct,
    delta3mPct: row.delta_3m_pct,
    zScore1y: row.z_score_1y,
    direction: row.direction ?? 'unknown',
    signal: row.signal,
    date: row.date,
  }
}

function normalizeNewsItem(item: NewsResponseItem): NewsItem {
  return {
    id: item.id,
    source: item.source,
    title: item.title,
    summary: item.summary,
    url: item.url,
    category: item.category,
    publishedAt: item.published_at,
  }
}

function normalizeSector(row: SectorRowResponse): SectorRow {
  return {
    ticker: row.ticker,
    name: row.name,
    change1d: row.change_1d,
    change1m: row.change_1m,
    change3m: row.change_3m,
    changeYtd: row.change_ytd,
    date: row.date,
  }
}

export function normalizeDashboardSummary(row: DashboardSummaryResponse): DashboardSummary {
  const snapshots = Object.fromEntries(
    Object.entries(row.snapshots ?? {}).map(([key, value]) => [key, normalizeSnapshot(value)])
  )
  const equities = Object.fromEntries(
    Object.entries(row.equities ?? {}).map(([key, value]) => [
      key,
      { close: value.close, changePct: value.change_pct, date: value.date },
    ])
  )

  return {
    updatedAt: row.updated_at,
    alerts: (row.alerts ?? []).map(normalizeSnapshot),
    snapshots,
    equities,
    yieldCurve: row.yield_curve ?? {},
    fomc: row.fomc
      ? {
          nextDate: row.fomc.next_date,
          daysLeft: row.fomc.days_left,
          probHold: row.fomc.prob_hold,
          probCut: row.fomc.prob_cut,
          probHike: row.fomc.prob_hike,
          probMethod: row.fomc.prob_method,
        }
      : undefined,
    aiHeadline: row.ai_headline,
    aiAsOfDate: row.ai_as_of_date,
    newsPreview: (row.news_preview ?? []).map(normalizeNewsItem),
  }
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  return normalizeDashboardSummary(await apiGet<DashboardSummaryResponse>('/summary'))
}

export async function getChanges(category?: string): Promise<ChangeSnapshot[]> {
  const query = category ? `?category=${encodeURIComponent(category)}` : ''
  const response = await apiGet<ChangesResponse>(`/changes${query}`)
  return (response.changes ?? []).map(normalizeSnapshot)
}

export async function getSectors(): Promise<SectorRow[]> {
  const response = await apiGet<SectorsResponse>('/sectors')
  return (response.sectors ?? []).map(normalizeSector)
}

