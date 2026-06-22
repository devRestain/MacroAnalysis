import { IndicatorExplanation } from '../../entities/indicator/types'
import { IndicatorHistory } from '../../entities/observation/types'
import { apiGet } from './client'

export type HistoryPeriod = '1w' | '1m' | '3m' | '1y' | 'all'

interface IndicatorHistoryResponse {
  indicator_key: string
  period: string
  data?: { date: string; value: number | null }[]
}

interface IndicatorExplanationResponse {
  indicator_key?: string
  key?: string
  display_name?: string | null
  short_label?: string | null
  name?: string | null
  title?: string | null
  category?: string | null
  description?: string | null
  market_role?: string | null
  analysis_hints?: Record<string, unknown> | null
  related_indicators?: string[] | null
}

interface IndicatorExplanationListResponse {
  indicator_explanations?: IndicatorExplanationResponse[]
  count?: number
}

export function normalizeIndicatorHistory(row: IndicatorHistoryResponse): IndicatorHistory {
  return {
    indicatorKey: row.indicator_key,
    period: row.period,
    data: row.data ?? [],
  }
}

export function normalizeIndicatorExplanation(row: IndicatorExplanationResponse): IndicatorExplanation {
  return {
    indicatorKey: row.indicator_key ?? row.key ?? '',
    name: row.display_name ?? row.name ?? row.title,
    shortLabel: row.short_label,
    category: row.category,
    description: row.description,
    whyItMatters: row.market_role,
    analysisHints: row.analysis_hints,
    relatedIndicatorKeys: row.related_indicators ?? [],
  }
}

export async function getIndicatorHistory(indicatorKey: string, period: HistoryPeriod = '3m'): Promise<IndicatorHistory> {
  const safeKey = encodeURIComponent(indicatorKey)
  return normalizeIndicatorHistory(await apiGet<IndicatorHistoryResponse>(`/indicators/history/${safeKey}?period=${period}`))
}

export async function getIndicatorExplanations(category?: string): Promise<IndicatorExplanation[]> {
  const query = category ? `?category=${encodeURIComponent(category)}` : ''
  const response = await apiGet<IndicatorExplanationListResponse>(`/indicator-explanations${query}`)
  return (response.indicator_explanations ?? []).map(normalizeIndicatorExplanation)
}

export async function getIndicatorExplanation(indicatorKey: string): Promise<IndicatorExplanation> {
  return normalizeIndicatorExplanation(
    await apiGet<IndicatorExplanationResponse>(`/indicator-explanations/${encodeURIComponent(indicatorKey)}`)
  )
}
