export interface Observation {
  indicatorKey: string
  value: number | string | null
  observedAt?: string | null
  updatedAt?: string | null
}

export interface HistoryPoint {
  date: string
  value: number | null
}

export interface IndicatorHistory {
  indicatorKey: string
  period: string
  data: HistoryPoint[]
}

