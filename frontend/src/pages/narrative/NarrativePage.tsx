import { getDivergence, getExpectations, getSentimentSignals } from '../../shared/api/sentiment'
import { Badge } from '../../shared/components/Badge'
import { Card } from '../../shared/components/Card'
import { useLanguage } from '../../shared/i18n'
import { DisabledState, EmptyState, ErrorState, LoadingState } from '../../shared/components/StateViews'
import { useResource } from '../../shared/hooks/useResource'
import { fmt, fmtDate } from '../../shared/utils/format'

export function NarrativePage() {
  const { t, label } = useLanguage()
  const expectations = useResource(() => getExpectations(30), [], { optional: true })
  const divergence = useResource(() => getDivergence(7), [], { optional: true })
  const sentiment = useResource(() => getSentimentSignals(50), [], { optional: true })
  const communicationSignals = sentiment.state.status === 'success'
    ? sentiment.state.data.filter((signal) => signal.sourceType === 'communication_event')
    : []

  return (
    <div className="page-shell animate-fade-up">
      <div className="mb-6">
        <h1 className="text-3xl font-extrabold tracking-[-0.04em]">{t('narrative.title')}</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-text-secondary">{t('narrative.description')}</p>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <Card title={t('narrative.card.expectations')} eyebrow={t('narrative.card.expectationsEyebrow')} tone="blue">
          {expectations.state.status === 'success' ? (
            expectations.state.data.length > 0 ? <div className="space-y-4">{expectations.state.data.map((series) => {
              const latest = series.points[series.points.length - 1]
              return (
                <div key={series.key} className="min-w-0 border-b border-surface-border pb-3 last:border-0">
                  <div className="flex min-w-0 items-center justify-between gap-3">
                    <span className="truncate text-sm font-medium">{series.key}</span>
                    <span className="font-mono text-sm">{fmt(latest?.consensusScore, 2)}</span>
                  </div>
                  <div className="mt-1 text-xs text-text-muted">{t('narrative.momentum')} {fmt(latest?.momentumScore, 2)} · {fmtDate(latest?.date)}</div>
                </div>
              )
            })}</div> : <EmptyState />
          ) : expectations.state.status === 'disabled' ? <DisabledState /> : expectations.state.status === 'error' ? <ErrorState /> : <LoadingState />}
        </Card>

        <Card title={t('narrative.card.divergence')} eyebrow={t('narrative.card.divergenceEyebrow')} tone="rose">
          {divergence.state.status === 'success' ? (
            divergence.state.data.length > 0 ? <div className="space-y-4">{divergence.state.data.map((event) => (
              <div key={event.id} className="min-w-0 border-b border-surface-border pb-3 last:border-0">
                <div className="flex min-w-0 items-center justify-between gap-3">
                  <span className="truncate text-sm font-medium">{event.report?.headline ?? `${event.actor ?? 'actor'} / ${event.dimension ?? 'dimension'}`}</span>
                  <Badge tone={event.severity === 'ALERT' ? 'red' : event.severity === 'WARNING' ? 'yellow' : 'neutral'}>{label('severity', event.severity, event.severity ?? 'INFO')}</Badge>
                </div>
                <p className="mt-2 line-clamp-2 text-safe text-xs leading-5 text-text-secondary">{event.report?.background ?? t('narrative.noReport')}</p>
              </div>
            ))}</div> : <EmptyState />
          ) : divergence.state.status === 'disabled' ? <DisabledState /> : divergence.state.status === 'error' ? <ErrorState /> : <LoadingState />}
        </Card>

        <Card title={t('narrative.card.sentiment')} eyebrow={t('narrative.card.sentimentEyebrow')} tone="green">
          {sentiment.state.status === 'success' ? (
            sentiment.state.data.length > 0 ? <div className="space-y-3">{sentiment.state.data.slice(0, 12).map((signal) => (
              <div key={signal.id} className="grid min-w-0 grid-cols-[minmax(0,1fr)_80px] gap-3 border-b border-surface-border pb-3 text-sm last:border-0">
                <div className="min-w-0">
                  <div className="truncate font-medium">{signal.actor ?? label('sourceType', signal.sourceType, 'source')} / {signal.dimension ?? 'macro'}</div>
                  <p className="mt-1 line-clamp-2 text-safe text-xs text-text-muted">{signal.evidence}</p>
                </div>
                <div className="text-right font-mono">{fmt(signal.stanceScore, 2)}</div>
              </div>
            ))}</div> : <EmptyState />
          ) : sentiment.state.status === 'disabled' ? <DisabledState /> : sentiment.state.status === 'error' ? <ErrorState /> : <LoadingState />}
        </Card>

        <Card title={t('narrative.card.communication')} eyebrow={t('narrative.card.communicationEyebrow')} tone="amber">
          {sentiment.state.status === 'success' ? (
            communicationSignals.length > 0 ? communicationSignals.slice(0, 8).map((signal) => (
              <div key={signal.id} className="min-w-0 border-b border-surface-border py-3 first:pt-0 last:border-0">
                <div className="truncate text-sm font-medium">{signal.actor ?? label('sourceType', 'communication_event', 'communication')} / {signal.dimension ?? 'macro'}</div>
                <p className="mt-1 line-clamp-2 text-safe text-xs text-text-muted">{signal.evidence}</p>
              </div>
            )) : <EmptyState label={t('narrative.noCommunicationSignals')} />
          ) : sentiment.state.status === 'disabled' ? <DisabledState /> : sentiment.state.status === 'error' ? <ErrorState /> : <LoadingState />}
          <a href="/ai" className="mt-4 inline-block text-xs font-medium text-accent">{t('narrative.openAi')}</a>
        </Card>
      </div>
    </div>
  )
}
