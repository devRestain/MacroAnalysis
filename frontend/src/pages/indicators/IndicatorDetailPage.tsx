import { useMemo, useState } from 'react'
import { getCalendarEvents } from '../../shared/api/calendar'
import { getDashboardSummary } from '../../shared/api/dashboard'
import { getIndicatorExplanation, getIndicatorHistory, HistoryPeriod } from '../../shared/api/indicators'
import { getNews } from '../../shared/api/news'
import { Badge } from '../../shared/components/Badge'
import { Card } from '../../shared/components/Card'
import { useLanguage } from '../../shared/i18n'
import { EmptyState, ErrorState, LoadingState } from '../../shared/components/StateViews'
import { useResource } from '../../shared/hooks/useResource'
import { fmt, fmtDate, fmtPct, timeAgo } from '../../shared/utils/format'

const periods: HistoryPeriod[] = ['1w', '1m', '3m', '1y', 'all']

export function IndicatorDetailPage({ indicatorKey }: { indicatorKey: string }) {
  const { locale, t, label } = useLanguage()
  const [period, setPeriod] = useState<HistoryPeriod>('3m')
  const summary = useResource(() => getDashboardSummary(), [locale])
  const history = useResource(() => getIndicatorHistory(indicatorKey, period), [indicatorKey, period])
  const explanation = useResource(() => getIndicatorExplanation(indicatorKey), [indicatorKey, locale], { optional: true })
  const calendar = useResource(() => getCalendarEvents(90, true), [locale], { optional: true })
  const news = useResource(() => getNews(undefined, 10), [], { optional: true })

  const snapshot = summary.state.status === 'success' ? summary.state.data.snapshots[indicatorKey] : undefined
  const relatedEvents = calendar.state.status === 'success'
    ? calendar.state.data.filter((event) => event.relatedIndicatorKeys.includes(indicatorKey)).slice(0, 5)
    : []

  const chartPath = useMemo(() => {
    if (history.state.status !== 'success' || history.state.data.data.length === 0) return ''
    const points = history.state.data.data.filter((point) => point.value != null)
    if (points.length === 0) return ''
    const values = points.map((point) => point.value as number)
    const min = Math.min(...values)
    const max = Math.max(...values)
    const span = max - min || 1
    return points.map((point, index) => {
      const x = (index / Math.max(points.length - 1, 1)) * 100
      const y = 100 - (((point.value as number) - min) / span) * 100
      return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`
    }).join(' ')
  }, [history.state])

  return (
    <div className="page-shell animate-fade-up">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <a href="/indicators" className="text-xs text-text-muted hover:text-accent">{t('indicatorDetail.back')}</a>
          <h1 className="mt-2 text-safe text-3xl font-extrabold tracking-[-0.04em]">{snapshot?.label ?? indicatorKey}</h1>
          <p className="mt-1 truncate font-mono text-xs text-text-muted">{indicatorKey}</p>
        </div>
        {snapshot && <Badge tone={snapshot.signal === 'red' ? 'red' : snapshot.signal === 'yellow' ? 'yellow' : 'green'}>{label('signal', snapshot.signal, snapshot.signal)}</Badge>}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <Card title={t('indicatorDetail.card.latest')} eyebrow={t('indicatorDetail.card.latestEyebrow')} tone="blue">
          {snapshot ? (
            <div className="grid gap-4 md:grid-cols-4">
              <Metric label={t('indicatorDetail.metric.latest')} value={fmt(snapshot.value, 2, snapshot.unit ?? '')} />
              <Metric label={t('indicatorDetail.metric.day1')} value={fmtPct(snapshot.delta1dPct)} />
              <Metric label={t('indicatorDetail.metric.month1')} value={fmtPct(snapshot.delta1mPct)} />
              <Metric label={t('indicatorDetail.metric.zScore')} value={fmt(snapshot.zScore1y, 2)} />
            </div>
          ) : <EmptyState label={t('indicatorDetail.snapshotMissing')} />}
        </Card>

        <Card title={t('indicatorDetail.card.explanation')} eyebrow={t('indicatorDetail.card.explanationEyebrow')} tone="default">
          {explanation.state.status === 'success' ? (
            <div className="space-y-3 text-safe text-sm leading-6 text-text-secondary">
              <p>{explanation.state.data.description ?? t('indicatorDetail.descriptionMissing')}</p>
              {explanation.state.data.whyItMatters && <p><span className="font-semibold text-text-primary">{t('indicatorDetail.whyItMatters')}: </span>{explanation.state.data.whyItMatters}</p>}
            </div>
          ) : explanation.state.status === 'error' || explanation.state.status === 'disabled' ? <EmptyState label={t('indicatorDetail.explanationMissing')} /> : <LoadingState />}
        </Card>

        <Card
          title={t('indicatorDetail.card.history')}
          eyebrow={t('indicatorDetail.card.historyEyebrow')}
          action={<div className="flex flex-wrap justify-end gap-1">{periods.map((item) => <button key={item} onClick={() => setPeriod(item)} className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${period === item ? 'border-accent/30 text-accent' : 'border-transparent text-text-muted hover:border-surface-border hover:bg-surface-hover'}`}>{item}</button>)}</div>}
          tone="green"
          className="xl:col-span-2"
        >
          {history.state.status === 'loading' || history.state.status === 'idle' ? <LoadingState /> : history.state.status === 'error' ? <ErrorState label={t('indicatorDetail.historyUnavailable')} /> : history.state.status === 'empty' ? <EmptyState label={t('indicatorDetail.historyEmpty')} /> : (
            <div className="h-72">
              <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="h-full w-full overflow-visible">
                <path d={chartPath} fill="none" stroke="#4f8ef7" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
              </svg>
            </div>
          )}
        </Card>

        <Card title={t('indicatorDetail.card.calendar')} eyebrow={t('indicatorDetail.card.calendarEyebrow')} tone="rose">
          {relatedEvents.length > 0 ? relatedEvents.map((event) => (
            <a key={event.id} href="/calendar" className="block min-w-0 border-b border-surface-border py-3 last:border-0">
              <div className="truncate text-sm font-medium">{event.displayName}</div>
              <div className="truncate text-xs text-text-muted">{fmtDate(event.eventDateLocal)} · {event.displayTime ?? event.eventTimeLocal ?? t('calendar.timePending')}</div>
            </a>
          )) : <EmptyState label={t('indicatorDetail.calendarEmpty')} />}
        </Card>

        <Card title={t('indicatorDetail.card.news')} eyebrow={t('indicatorDetail.card.newsEyebrow')} tone="amber">
          {news.state.status === 'success' ? news.state.data.slice(0, 5).map((item) => (
            <a key={item.id} href={item.url ?? '/news'} className="block min-w-0 border-b border-surface-border py-3 last:border-0">
              <div className="line-clamp-2 text-safe text-sm font-medium">{item.title}</div>
              <div className="truncate text-xs text-text-muted">{item.source} · {timeAgo(item.publishedAt)}</div>
            </a>
          )) : news.state.status === 'error' || news.state.status === 'disabled' ? <EmptyState label={t('indicatorDetail.newsUnavailable')} /> : <LoadingState />}
        </Card>
      </div>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <div className="text-xs text-text-muted">{label}</div>
      <div className="mt-1 truncate font-mono text-xl font-semibold">{value}</div>
    </div>
  )
}
