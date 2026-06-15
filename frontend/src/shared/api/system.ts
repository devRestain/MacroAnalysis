import { ApiError, optionalApi } from './client'
import { getDashboardSummary } from './dashboard'
import { getSentimentSignals } from './sentiment'
import { getTypedAiSummary } from './ai'

export async function getHealth(): Promise<Record<string, unknown>> {
  const res = await fetch('/health')
  if (!res.ok) throw new ApiError(`Health check failed: ${res.status}`, res.status >= 500 ? 'server' : 'unknown', res.status)
  return res.json()
}

export async function getSystemAvailability() {
  const [dashboard, ai, sentiment] = await Promise.all([
    optionalApi(() => getDashboardSummary()),
    optionalApi(() => getTypedAiSummary('macro', { days: 7 })),
    optionalApi(() => getSentimentSignals(1)),
  ])

  return {
    dashboardUpdatedAt: dashboard instanceof ApiError ? null : dashboard.updatedAt ?? null,
    aiAvailable: !(ai instanceof ApiError),
    sentimentAvailable: !(sentiment instanceof ApiError),
    aiError: ai instanceof ApiError ? ai : null,
    sentimentError: sentiment instanceof ApiError ? sentiment : null,
  }
}
