export interface Indicator {
  key: string
  name?: string
  category?: string
  unit?: string | null
}

export interface IndicatorExplanation {
  indicatorKey: string
  name?: string | null
  category?: string | null
  description?: string | null
  whyItMatters?: string | null
  analysisHints?: string[] | null
  relatedIndicatorKeys?: string[]
}

