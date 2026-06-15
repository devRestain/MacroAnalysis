export type AiSummaryType = 'macro' | 'market' | 'calendar' | 'communication'

export interface AiSummary {
  id?: number | string
  summaryDate?: string
  summaryType: AiSummaryType
  targetKey?: string | null
  headline?: string | null
  body?: string | null
  modelUsed?: string | null
  metadata?: Record<string, unknown>
}

export interface ChatReply {
  reply: string
}

