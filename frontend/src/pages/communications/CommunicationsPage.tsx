import { getFomcOverview } from '../../shared/api/calendar'
import { getTypedAiSummary } from '../../shared/api/ai'
import { getSentimentSignals } from '../../shared/api/sentiment'
import { Badge } from '../../shared/components/Badge'
import { Card } from '../../shared/components/Card'
import { DisabledState, EmptyState, ErrorState, LoadingState } from '../../shared/components/StateViews'
import { useResource } from '../../shared/hooks/useResource'
import { fmt, fmtDate } from '../../shared/utils/format'

export function CommunicationsPage() {
  const fomc = useResource(() => getFomcOverview(), [], { optional: true })
  const powell = useResource(() => getTypedAiSummary('communication', { targetKey: 'Powell', days: 30 }), [], { optional: true })
  const sentiment = useResource(() => getSentimentSignals(50), [], { optional: true })
  const communicationSignals = sentiment.state.status === 'success'
    ? sentiment.state.data.filter((signal) => signal.sourceType === 'communication_event')
    : []

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 lg:px-6">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Communications</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-text-secondary">Fed communications, FOMC details, and communication-scoped briefings kept separate from general calendar dates.</p>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card title="FOMC Detail Context" eyebrow="meeting records">
          {fomc.state.status === 'success' ? (
            <div className="space-y-3">
              {fomc.state.data.meetings.slice(0, 8).map((meeting) => (
                <div key={`${meeting.id ?? meeting.date}`} className="border-b border-surface-border pb-3 last:border-0">
                  <div className="flex justify-between gap-3">
                    <span className="text-sm font-medium">{meeting.displayName ?? 'FOMC Meeting'}</span>
                    <span className="font-mono text-xs text-text-muted">{fmtDate(meeting.eventDateLocal ?? meeting.date)}</span>
                  </div>
                  <div className="mt-1 text-xs text-text-muted">Decision rate {meeting.rate ?? '-'} · Change {meeting.changeBp ?? '-'}</div>
                </div>
              ))}
            </div>
          ) : fomc.state.status === 'disabled' ? <DisabledState /> : fomc.state.status === 'error' ? <ErrorState /> : <LoadingState />}
        </Card>

        <Card title="Powell Communication Summary" eyebrow="typed AI summary">
          {powell.state.status === 'success' ? (
            <article>
              <h2 className="text-lg font-semibold">{powell.state.data.headline ?? 'Communication briefing'}</h2>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-text-secondary">{powell.state.data.body ?? 'No summary body available.'}</p>
              <div className="mt-4 text-xs text-text-muted">Model {powell.state.data.modelUsed ?? '-'} · {powell.state.data.summaryDate ?? '-'}</div>
            </article>
          ) : powell.state.status === 'disabled' ? <DisabledState /> : powell.state.status === 'error' ? <ErrorState label="Communication summary is unavailable." /> : <LoadingState />}
        </Card>

        <Card title="Communication Sentiment" eyebrow="optional pipeline" className="xl:col-span-2">
          {sentiment.state.status === 'success' ? (
            communicationSignals.length > 0 ? (
              <div className="grid gap-3 md:grid-cols-2">
                {communicationSignals.slice(0, 8).map((signal) => (
                  <div key={signal.id} className="border border-surface-border p-3">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm font-medium">{signal.actor ?? 'communication'} / {signal.dimension ?? 'macro'}</span>
                      <Badge>{fmt(signal.stanceScore, 2)}</Badge>
                    </div>
                    <p className="mt-2 line-clamp-2 text-xs leading-5 text-text-secondary">{signal.evidence}</p>
                  </div>
                ))}
              </div>
            ) : <EmptyState label="No communication-sourced sentiment signals." />
          ) : sentiment.state.status === 'disabled' ? <DisabledState /> : sentiment.state.status === 'error' ? <ErrorState /> : <LoadingState />}
        </Card>
      </div>
    </div>
  )
}

