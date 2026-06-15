import { DivergenceEvent, ExpectationSeries, SentimentSignal } from '../../entities/sentiment/types'
import { apiGet } from './client'

interface SentimentSignalResponse {
  id?: number
  batch_date?: string | null
  source_type?: string | null
  source_id?: string | number | null
  actor?: string | null
  dimension?: string | null
  stance?: string | null
  stance_score?: number | null
  intensity?: number | null
  confidence?: number | null
  evidence?: string | null
}

interface SentimentSignalListResponse {
  signals?: SentimentSignalResponse[]
  count?: number
}

interface ExpectationsResponse {
  expectations?: Record<string, {
    date: string
    consensus_score: number | null
    raw_score: number | null
    consensus_strength: number | null
    inertia_coefficient: number | null
    inertia_reset: boolean | null
    momentum_score: number | null
  }[]>
}

interface DivergenceResponse {
  divergence_events?: {
    id?: number
    batch_date?: string | null
    actor?: string | null
    dimension?: string | null
    raw_score?: number | null
    consensus_score?: number | null
    adjusted_gap?: number | null
    severity?: string
    report?: {
      headline?: string | null
      background?: string | null
      action_plan?: string | null
      risk_scenario?: string | null
    } | null
  }[]
  count?: number
}

export async function getSentimentSignals(limit = 50): Promise<SentimentSignal[]> {
  const response = await apiGet<SentimentSignalListResponse>(`/sentiment/signals?limit=${limit}`)
  return (response.signals ?? []).map((signal) => ({
    id: signal.id,
    batchDate: signal.batch_date,
    sourceType: signal.source_type,
    sourceId: signal.source_id,
    actor: signal.actor,
    dimension: signal.dimension,
    stance: signal.stance,
    stanceScore: signal.stance_score,
    intensity: signal.intensity,
    confidence: signal.confidence,
    evidence: signal.evidence,
  }))
}

export async function getExpectations(days = 30): Promise<ExpectationSeries[]> {
  const response = await apiGet<ExpectationsResponse>(`/expectations?days=${days}`)
  return Object.entries(response.expectations ?? {}).map(([key, points]) => ({
    key,
    points: points.map((point) => ({
      date: point.date,
      consensusScore: point.consensus_score,
      rawScore: point.raw_score,
      consensusStrength: point.consensus_strength,
      inertiaCoefficient: point.inertia_coefficient,
      inertiaReset: point.inertia_reset,
      momentumScore: point.momentum_score,
    })),
  }))
}

export async function getDivergence(days = 7): Promise<DivergenceEvent[]> {
  const response = await apiGet<DivergenceResponse>(`/divergence?days=${days}`)
  return (response.divergence_events ?? []).map((event) => ({
    id: event.id,
    batchDate: event.batch_date,
    actor: event.actor,
    dimension: event.dimension,
    rawScore: event.raw_score,
    consensusScore: event.consensus_score,
    adjustedGap: event.adjusted_gap,
    severity: event.severity,
    report: event.report
      ? {
          headline: event.report.headline,
          background: event.report.background,
          actionPlan: event.report.action_plan,
          riskScenario: event.report.risk_scenario,
        }
      : null,
  }))
}

