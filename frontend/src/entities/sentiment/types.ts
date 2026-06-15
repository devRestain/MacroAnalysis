export interface SentimentSignal {
  id?: number | string
  batchDate?: string | null
  sourceType?: string | null
  sourceId?: string | number | null
  actor?: string | null
  dimension?: string | null
  stance?: string | null
  stanceScore?: number | null
  intensity?: number | null
  confidence?: number | null
  evidence?: string | null
}

export interface ExpectationPoint {
  date: string
  consensusScore: number | null
  rawScore: number | null
  consensusStrength: number | null
  inertiaCoefficient: number | null
  inertiaReset: boolean | null
  momentumScore: number | null
}

export interface ExpectationSeries {
  key: string
  points: ExpectationPoint[]
}

export interface DivergenceEvent {
  id?: number | string
  batchDate?: string | null
  actor?: string | null
  dimension?: string | null
  rawScore?: number | null
  consensusScore?: number | null
  adjustedGap?: number | null
  severity?: 'INFO' | 'WARNING' | 'ALERT' | string
  report?: {
    headline?: string | null
    background?: string | null
    actionPlan?: string | null
    riskScenario?: string | null
  } | null
}

