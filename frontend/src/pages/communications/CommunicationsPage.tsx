import { getFomcOverview } from '../../shared/api/calendar'
import { getTypedAiSummary } from '../../shared/api/ai'
import { getSentimentSignals } from '../../shared/api/sentiment'
import { Badge } from '../../shared/components/Badge'
import { Card } from '../../shared/components/Card'
import { useLanguage } from '../../shared/i18n'
import { DisabledState, EmptyState, ErrorState, LoadingState } from '../../shared/components/StateViews'
import { useResource } from '../../shared/hooks/useResource'
import { fmt, fmtDate } from '../../shared/utils/format'

export function CommunicationsPage() {
  const { locale, t } = useLanguage()
  const fomc = useResource(() => getFomcOverview(), [locale], { optional: true })
  const powell = useResource(() => getTypedAiSummary('communication', { targetKey: 'Powell', days: 30 }), [], { optional: true })
  const sentiment = useResource(() => getSentimentSignals(50), [], { optional: true })
  const communicationSignals = sentiment.state.status === 'success'
    ? sentiment.state.data.filter((signal) => signal.sourceType === 'communication_event')
    : []

  return (
    <div className="page-shell animate-fade-up">
      <div className="mb-6">
        <h1 className="text-3xl font-extrabold tracking-[-0.04em]">{t('communications.title')}</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-text-secondary">{t('communications.description')}</p>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card title={t('communications.card.context')} eyebrow={t('communications.card.contextEyebrow')} tone="rose">
          {fomc.state.status === 'success' ? (
            <div className="space-y-3">
              {fomc.state.data.meetings.slice(0, 8).map((meeting) => (
                <div key={`${meeting.id ?? meeting.date}`} className="rounded-[20px] border border-surface-border/80 bg-white/75 px-4 py-3">
                  <div className="flex justify-between gap-3">
                    <span className="text-sm font-bold">{meeting.displayName ?? t('calendar.fomcMeetingFallback')}</span>
                    <span className="font-mono text-xs text-text-muted">{fmtDate(meeting.eventDateLocal ?? meeting.date)}</span>
                  </div>
                  <div className="mt-1 text-xs text-text-muted">{t('communications.rate')} {meeting.rate ?? '-'} · {t('communications.change')} {meeting.changeBp ?? '-'}</div>
                </div>
              ))}
            </div>
          ) : fomc.state.status === 'disabled' ? <DisabledState /> : fomc.state.status === 'error' ? <ErrorState /> : <LoadingState />}
        </Card>

        <Card title={t('communications.card.summary')} eyebrow={t('communications.card.summaryEyebrow')} tone="blue">
          {powell.state.status === 'success' ? (
            <article>
              <h2 className="text-xl font-extrabold tracking-[-0.02em]">{powell.state.data.headline ?? t('communications.summaryFallback')}</h2>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-text-secondary">{powell.state.data.body ?? t('communications.summaryBodyFallback')}</p>
              <div className="mt-4 text-xs text-text-muted">{t('communications.model')} {powell.state.data.modelUsed ?? '-'} · {powell.state.data.summaryDate ?? '-'}</div>
            </article>
          ) : powell.state.status === 'disabled' ? <DisabledState /> : powell.state.status === 'error' ? <ErrorState label={t('communications.summaryUnavailable')} /> : <LoadingState />}
        </Card>

        <Card title={t('communications.card.sentiment')} eyebrow={t('communications.card.sentimentEyebrow')} tone="amber" className="xl:col-span-2">
          {sentiment.state.status === 'success' ? (
            communicationSignals.length > 0 ? (
              <div className="grid gap-3 md:grid-cols-2">
                {communicationSignals.slice(0, 8).map((signal) => (
                  <div key={signal.id} className="rounded-[20px] border border-surface-border/80 bg-white/78 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm font-bold">{signal.actor ?? t('communications.actorFallback')} / {signal.dimension ?? 'macro'}</span>
                      <Badge>{fmt(signal.stanceScore, 2)}</Badge>
                    </div>
                    <p className="mt-2 line-clamp-2 text-xs leading-6 text-text-secondary">{signal.evidence}</p>
                  </div>
                ))}
              </div>
            ) : <EmptyState label={t('communications.noSignals')} />
          ) : sentiment.state.status === 'disabled' ? <DisabledState /> : sentiment.state.status === 'error' ? <ErrorState /> : <LoadingState />}
        </Card>
      </div>
    </div>
  )
}
