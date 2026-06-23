import { ApiError, optionalApi } from './client'
import { getCalendarEvents } from './calendar'
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

export async function getSystemOverview() {
  const [dashboard, calendar, ai] = await Promise.all([
    optionalApi(() => getDashboardSummary()),
    optionalApi(() => getCalendarEvents(14, true)),
    optionalApi(() => getTypedAiSummary('macro', { days: 7 })),
  ])

  const trackedSignals = dashboard instanceof ApiError
    ? null
    : [...dashboard.alerts, ...Object.values(dashboard.snapshots)]
      .filter((item, index, all) => all.findIndex((candidate) => candidate.key === item.key) === index)
      .slice(0, 10).length

  return {
    dashboardUpdatedAt: dashboard instanceof ApiError ? null : dashboard.updatedAt ?? null,
    aiBriefingDate: ai instanceof ApiError ? null : ai.summaryDate ?? null,
    trackedSignals,
    upcomingEvents: calendar instanceof ApiError ? null : calendar.slice(0, 6).length,
    newsItems: dashboard instanceof ApiError ? null : dashboard.newsPreview.length,
    fomcDaysLeft: dashboard instanceof ApiError ? null : dashboard.fomc?.daysLeft ?? null,
    probHold: dashboard instanceof ApiError ? null : dashboard.fomc?.probHold ?? null,
  }
}
