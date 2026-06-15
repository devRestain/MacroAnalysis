import { AiSummary, AiSummaryType, ChatReply } from '../../entities/aiSummary/types'
import { aiChatHeaders, apiGet, apiPost } from './client'

interface AiSummaryResponse {
  id?: number
  summary_date?: string
  summary_type?: AiSummaryType
  target_key?: string | null
  headline?: string | null
  body?: string | null
  model_used?: string | null
  metadata?: Record<string, unknown>
}

function normalizeAiSummary(row: AiSummaryResponse, fallbackType: AiSummaryType): AiSummary {
  return {
    id: row.id,
    summaryDate: row.summary_date,
    summaryType: row.summary_type ?? fallbackType,
    targetKey: row.target_key,
    headline: row.headline,
    body: row.body,
    modelUsed: row.model_used,
    metadata: row.metadata ?? {},
  }
}

export async function getTypedAiSummary(
  summaryType: AiSummaryType,
  options: { targetKey?: string; days?: number } = {}
): Promise<AiSummary> {
  const params = new URLSearchParams({ summary_type: summaryType, days: String(options.days ?? 7) })
  if (options.targetKey) params.set('target_key', options.targetKey)
  return normalizeAiSummary(await apiGet<AiSummaryResponse>(`/ai/summary?${params.toString()}`), summaryType)
}

export async function sendAiChat(message: string): Promise<ChatReply> {
  return apiPost<ChatReply>('/ai/chat', { message }, { headers: aiChatHeaders() })
}

