import { RefreshCw } from 'lucide-react'
import { ReactNode } from 'react'
import { getCalendarEvents } from '../../shared/api/calendar'
import { getDashboardSummary, getSectors } from '../../shared/api/dashboard'
import { getSentimentSignals } from '../../shared/api/sentiment'
import { Badge } from '../../shared/components/Badge'
import { Card } from '../../shared/components/Card'
import { DataFreshness } from '../../shared/components/DataFreshness'
import { DisabledState, EmptyState, ErrorState, LoadingState } from '../../shared/components/StateViews'
import { useResource } from '../../shared/hooks/useResource'
import { fmt, fmtPct, timeAgo } from '../../shared/utils/format'

export function DashboardPage() {
  const summary = useResource(() => getDashboardSummary(), [], { refreshInterval: 5 * 60 * 1000 })
  const sectors = useResource(() => getSectors(), [], { refreshInterval: 30 * 60 * 1000, optional: true })
  const calendar = useResource(() => getCalendarEvents(14, true), [], { optional: true })
  const sentiment = useResource(() => getSentimentSignals(5), [], { optional: true })

  if (summary.state.status === 'loading' || summary.state.status === 'idle') {
    return <PageFrame title="Dashboard"><LoadingState /></PageFrame>
  }

  if (summary.state.status === 'error' || summary.state.status === 'disabled') {
    return <PageFrame title="Dashboard"><ErrorState label="Critical dashboard summary is unavailable." /></PageFrame>
  }

  if (summary.state.status === 'empty') {
    return <PageFrame title="Dashboard"><EmptyState label="No dashboard summary has been collected yet." /></PageFrame>
  }

  const data = summary.state.data
  const topSignals = [...data.alerts, ...Object.values(data.snapshots)]
    .filter((item, index, all) => all.findIndex((candidate) => candidate.key === item.key) === index)
    .slice(0, 8)
  const upcoming = calendar.state.status === 'success' ? calendar.state.data.slice(0, 5) : []
  const sentimentRows = sentiment.state.status === 'success' ? sentiment.state.data : []

  return (
    <PageFrame
      title="Dashboard"
      description="Latest collected data, market context, and watch items from the normalized macro platform."
      action={<button onClick={summary.reload} className="inline-flex items-center gap-2 border border-surface-border px-3 py-1.5 text-xs text-text-secondary hover:bg-surface-hover"><RefreshCw size={13} />Refresh</button>}
    >
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <DataFreshness updatedAt={data.updatedAt} />
        {data.fomc?.daysLeft != null && <Badge tone="blue">FOMC D-{data.fomc.daysLeft}</Badge>}
        {data.aiAsOfDate && <Badge>AI briefing {data.aiAsOfDate}</Badge>}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.4fr_0.8fr]">
        <Card title="Market Overview" eyebrow="indicators + observations + signals">
          <div className="grid gap-px overflow-hidden border border-surface-border bg-surface-border md:grid-cols-4">
            {topSignals.map((item) => (
              <a key={item.key} href={`/indicators/${encodeURIComponent(item.key)}`} className="bg-surface-card p-3 hover:bg-surface-hover">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-xs text-text-secondary">{item.label}</span>
                  <Badge tone={item.signal === 'red' ? 'red' : item.signal === 'yellow' ? 'yellow' : 'green'}>{item.signal}</Badge>
                </div>
                <div className="mt-3 font-mono text-lg font-semibold">{fmt(item.value, 2, item.unit ?? '')}</div>
                <div className="mt-1 text-xs text-text-muted">1m {fmtPct(item.delta1mPct)} · z {fmt(item.zScore1y, 2)}</div>
              </a>
            ))}
          </div>
        </Card>

        <Card title="AI Headline" eyebrow="briefing">
          <p className="text-lg font-semibold leading-7">{data.aiHeadline || 'No AI headline is available for the latest collection.'}</p>
          <a href="/ai" className="mt-4 inline-flex text-xs font-medium text-accent">Open typed briefings</a>
        </Card>

        <Card title="Yield Curve" eyebrow="rates context">
          <div className="grid grid-cols-2 gap-px border border-surface-border bg-surface-border md:grid-cols-4">
            {Object.entries(data.yieldCurve).map(([key, value]) => (
              <div key={key} className="bg-surface-card p-3">
                <div className="text-xs text-text-muted">{key}</div>
                <div className="mt-2 font-mono text-lg">{fmt(value, 2)}</div>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Equity Sectors" eyebrow="market context">
          {sectors.state.status === 'success' ? (
            <div className="space-y-2">
              {sectors.state.data.slice(0, 7).map((row) => (
                <div key={row.ticker} className="grid grid-cols-[70px_1fr_70px] items-center gap-3 text-xs">
                  <span className="font-mono text-text-secondary">{row.ticker}</span>
                  <span className="truncate">{row.name}</span>
                  <span className={row.change1d && row.change1d < 0 ? 'text-signal-red' : 'text-signal-green'}>{fmtPct(row.change1d)}</span>
                </div>
              ))}
            </div>
          ) : sectors.state.status === 'disabled' ? <DisabledState /> : sectors.state.status === 'error' ? <ErrorState /> : <LoadingState />}
        </Card>

        <Card title="Calendar Watch" eyebrow="next 14 days">
          {calendar.state.status === 'success' && upcoming.length > 0 ? (
            <div className="divide-y divide-surface-border">
              {upcoming.map((event) => (
                <a key={event.id} href="/calendar" className="block py-3 first:pt-0 last:pb-0">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium">{event.displayName}</span>
                    <Badge tone={event.importance === 'high' ? 'red' : event.importance === 'medium' ? 'yellow' : 'neutral'}>{event.importance}</Badge>
                  </div>
                  <div className="mt-1 text-xs text-text-muted">{event.eventDateLocal} · {event.displayTime ?? event.eventTimeLocal ?? 'time pending'}</div>
                </a>
              ))}
            </div>
          ) : calendar.state.status === 'disabled' ? <DisabledState /> : calendar.state.status === 'error' ? <ErrorState /> : <EmptyState />}
        </Card>

        <Card title="News Preview" eyebrow="recent">
          <div className="divide-y divide-surface-border">
            {data.newsPreview.map((item) => (
              <a key={item.id} href={item.url ?? '/news'} className="block py-3 first:pt-0 last:pb-0">
                <div className="line-clamp-2 text-sm font-medium">{item.title}</div>
                <div className="mt-1 text-xs text-text-muted">{item.source} · {timeAgo(item.publishedAt)}</div>
              </a>
            ))}
          </div>
        </Card>

        <Card title="Sentiment Mini Panel" eyebrow="optional pipeline">
          {sentiment.state.status === 'success' && sentimentRows.length > 0 ? (
            <div className="space-y-3">
              {sentimentRows.map((row) => (
                <div key={row.id} className="text-sm">
                  <div className="flex justify-between gap-3">
                    <span>{row.actor ?? row.sourceType ?? 'signal'} / {row.dimension ?? 'macro'}</span>
                    <span className="font-mono text-text-secondary">{fmt(row.stanceScore, 2)}</span>
                  </div>
                  <p className="mt-1 line-clamp-2 text-xs text-text-muted">{row.evidence}</p>
                </div>
              ))}
            </div>
          ) : sentiment.state.status === 'disabled' ? <DisabledState /> : sentiment.state.status === 'error' ? <ErrorState /> : <EmptyState label="No sentiment signals are available." />}
        </Card>
      </div>
    </PageFrame>
  )
}

function PageFrame({ title, description, action, children }: { title: string; description?: string; action?: ReactNode; children: ReactNode }) {
  return (
    <div className="mx-auto max-w-7xl px-4 py-6 lg:px-6">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">{title}</h1>
          {description && <p className="mt-2 max-w-3xl text-sm leading-6 text-text-secondary">{description}</p>}
        </div>
        {action}
      </div>
      {children}
    </div>
  )
}
