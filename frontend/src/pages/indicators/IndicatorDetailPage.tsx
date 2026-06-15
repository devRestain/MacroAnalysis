import { useMemo, useState } from 'react'
import { getCalendarEvents } from '../../shared/api/calendar'
import { getDashboardSummary } from '../../shared/api/dashboard'
import { getIndicatorExplanation, getIndicatorHistory, HistoryPeriod } from '../../shared/api/indicators'
import { getNews } from '../../shared/api/news'
import { Badge } from '../../shared/components/Badge'
import { Card } from '../../shared/components/Card'
import { EmptyState, ErrorState, LoadingState } from '../../shared/components/StateViews'
import { useResource } from '../../shared/hooks/useResource'
import { fmt, fmtDate, fmtPct, timeAgo } from '../../shared/utils/format'

const periods: HistoryPeriod[] = ['1w', '1m', '3m', '1y', 'all']

export function IndicatorDetailPage({ indicatorKey }: { indicatorKey: string }) {
  const [period, setPeriod] = useState<HistoryPeriod>('3m')
  const summary = useResource(() => getDashboardSummary(), [])
  const history = useResource(() => getIndicatorHistory(indicatorKey, period), [indicatorKey, period])
  const explanation = useResource(() => getIndicatorExplanation(indicatorKey), [indicatorKey], { optional: true })
  const calendar = useResource(() => getCalendarEvents(90, true), [], { optional: true })
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
          <a href="/indicators" className="text-xs text-text-muted hover:text-accent">Indicators</a>
          <h1 className="mt-2 text-safe text-3xl font-extrabold tracking-[-0.04em]">{snapshot?.label ?? indicatorKey}</h1>
          <p className="mt-1 truncate font-mono text-xs text-text-muted">{indicatorKey}</p>
        </div>
        {snapshot && <Badge tone={snapshot.signal === 'red' ? 'red' : snapshot.signal === 'yellow' ? 'yellow' : 'green'}>{snapshot.signal}</Badge>}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <Card title="Latest Observation" eyebrow="runtime signal" tone="blue">
          {snapshot ? (
            <div className="grid gap-4 md:grid-cols-4">
              <Metric label="Latest" value={fmt(snapshot.value, 2, snapshot.unit ?? '')} />
              <Metric label="1 day" value={fmtPct(snapshot.delta1dPct)} />
              <Metric label="1 month" value={fmtPct(snapshot.delta1mPct)} />
              <Metric label="Z-score 1y" value={fmt(snapshot.zScore1y, 2)} />
            </div>
          ) : <EmptyState label="No latest snapshot found for this indicator." />}
        </Card>

        <Card title="Static Explanation" eyebrow="metadata" tone="default">
          {explanation.state.status === 'success' ? (
            <div className="space-y-3 text-safe text-sm leading-6 text-text-secondary">
              <p>{explanation.state.data.description ?? 'No description available.'}</p>
              {explanation.state.data.whyItMatters && <p><span className="font-semibold text-text-primary">Why it matters: </span>{explanation.state.data.whyItMatters}</p>}
            </div>
          ) : explanation.state.status === 'error' || explanation.state.status === 'disabled' ? <EmptyState label="No static explanation found." /> : <LoadingState />}
        </Card>

        <Card
          title="History"
          eyebrow="latest available observation"
          action={<div className="flex flex-wrap justify-end gap-1">{periods.map((item) => <button key={item} onClick={() => setPeriod(item)} className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${period === item ? 'border-accent/30 text-accent' : 'border-transparent text-text-muted hover:border-surface-border hover:bg-surface-hover'}`}>{item}</button>)}</div>}
          tone="green"
          className="xl:col-span-2"
        >
          {history.state.status === 'loading' || history.state.status === 'idle' ? <LoadingState /> : history.state.status === 'error' ? <ErrorState label="History data is unavailable." /> : history.state.status === 'empty' ? <EmptyState label="No history data for this indicator." /> : (
            <div className="h-72">
              <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="h-full w-full overflow-visible">
                <path d={chartPath} fill="none" stroke="#4f8ef7" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
              </svg>
            </div>
          )}
        </Card>

        <Card title="Related Calendar Events" eyebrow="watch items" tone="rose">
          {relatedEvents.length > 0 ? relatedEvents.map((event) => (
            <a key={event.id} href="/calendar" className="block min-w-0 border-b border-surface-border py-3 last:border-0">
              <div className="truncate text-sm font-medium">{event.displayName}</div>
              <div className="truncate text-xs text-text-muted">{fmtDate(event.eventDateLocal)} · {event.displayTime ?? event.eventTimeLocal ?? 'time pending'}</div>
            </a>
          )) : <EmptyState label="No related calendar events found." />}
        </Card>

        <Card title="Related News" eyebrow="recent context" tone="amber">
          {news.state.status === 'success' ? news.state.data.slice(0, 5).map((item) => (
            <a key={item.id} href={item.url ?? '/news'} className="block min-w-0 border-b border-surface-border py-3 last:border-0">
              <div className="line-clamp-2 text-safe text-sm font-medium">{item.title}</div>
              <div className="truncate text-xs text-text-muted">{item.source} · {timeAgo(item.publishedAt)}</div>
            </a>
          )) : news.state.status === 'error' || news.state.status === 'disabled' ? <EmptyState label="Recent news is unavailable." /> : <LoadingState />}
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
