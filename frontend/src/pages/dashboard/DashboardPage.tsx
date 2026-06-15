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
      action={<button onClick={summary.reload} className="inline-flex items-center gap-2 rounded-full border border-surface-border bg-white px-4 py-2 text-xs font-bold text-text-secondary hover:border-accent/35 hover:text-accent"><RefreshCw size={13} />Refresh</button>}
    >
      <div className="mb-6 grid gap-3 xl:grid-cols-[minmax(0,1.5fr)_repeat(3,minmax(0,0.5fr))]">
        <div className="flat-metric min-w-0">
          <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-text-muted">Workspace</div>
          <h2 className="mt-2 text-2xl font-bold tracking-[-0.03em] text-text-primary">One surface, clearly separated entities.</h2>
          <p className="mt-2 max-w-3xl text-sm leading-7 text-text-secondary">
            The layout is flattened so market, calendar, news, and sentiment panels stay distinct without breaking the overall rhythm of the page.
          </p>
        </div>
        <MetricChip label="Tracked signals" value={topSignals.length} />
        <MetricChip label="Upcoming events" value={upcoming.length} />
        <MetricChip label="News items" value={data.newsPreview.length} />
      </div>

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <DataFreshness updatedAt={data.updatedAt} />
        {data.fomc?.daysLeft != null && <Badge tone="blue">FOMC D-{data.fomc.daysLeft}</Badge>}
        {data.aiAsOfDate && <Badge>AI briefing {data.aiAsOfDate}</Badge>}
      </div>

      <div className="grid gap-4 2xl:grid-cols-12">
        <Card title="Market Overview" eyebrow="indicators + observations + signals" tone="blue" className="2xl:col-span-7">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {topSignals.map((item) => (
              <a key={item.key} href={`/indicators/${encodeURIComponent(item.key)}`} className="min-w-0 rounded-[18px] border border-surface-border bg-white p-4 hover:border-accent/30">
                <div className="flex min-w-0 items-start justify-between gap-2">
                  <span className="min-w-0 truncate text-xs font-bold uppercase tracking-[0.14em] text-text-muted">{item.label}</span>
                  <Badge tone={item.signal === 'red' ? 'red' : item.signal === 'yellow' ? 'yellow' : 'green'}>{item.signal}</Badge>
                </div>
                <div className="mt-4 truncate font-mono text-2xl font-semibold tracking-[-0.04em]">{fmt(item.value, 2, item.unit ?? '')}</div>
                <div className="mt-2 text-xs font-medium text-text-secondary">1m {fmtPct(item.delta1mPct)} · z {fmt(item.zScore1y, 2)}</div>
              </a>
            ))}
          </div>
        </Card>

        <Card title="AI Headline" eyebrow="briefing" tone="amber" className="2xl:col-span-5">
          <div className="min-w-0">
            <p className="text-safe text-lg font-bold leading-8">{data.aiHeadline || 'No AI headline is available for the latest collection.'}</p>
            <a href="/ai" className="mt-5 inline-flex rounded-full border border-surface-border bg-white px-3 py-1.5 text-xs font-bold text-accent">Open typed briefings</a>
          </div>
        </Card>

        <Card title="Yield Curve" eyebrow="rates context" tone="green" className="2xl:col-span-4">
          <div className="grid grid-cols-2 gap-3 xl:grid-cols-4 2xl:grid-cols-2">
            {Object.entries(data.yieldCurve).map(([key, value]) => (
              <div key={key} className="rounded-[18px] border border-surface-border bg-white p-4">
                <div className="text-xs font-bold uppercase tracking-[0.14em] text-text-muted">{key}</div>
                <div className="mt-2 font-mono text-2xl">{fmt(value, 2)}</div>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Equity Sectors" eyebrow="market context" tone="default" className="2xl:col-span-4">
          {sectors.state.status === 'success' ? (
            <div className="space-y-2">
              {sectors.state.data.slice(0, 7).map((row) => (
                <div key={row.ticker} className="grid min-w-0 grid-cols-[64px_minmax(0,1fr)_76px] items-center gap-3 rounded-[16px] border border-surface-border bg-white px-3 py-2.5 text-xs">
                  <span className="font-mono text-text-secondary">{row.ticker}</span>
                  <span className="truncate font-semibold">{row.name}</span>
                  <span className={`text-right font-bold ${row.change1d && row.change1d < 0 ? 'text-signal-red' : 'text-signal-green'}`}>{fmtPct(row.change1d)}</span>
                </div>
              ))}
            </div>
          ) : sectors.state.status === 'disabled' ? <DisabledState /> : sectors.state.status === 'error' ? <ErrorState /> : <LoadingState />}
        </Card>

        <Card title="Calendar Watch" eyebrow="next 14 days" tone="rose" className="2xl:col-span-4">
          {calendar.state.status === 'success' && upcoming.length > 0 ? (
            <div className="divide-y divide-surface-border">
              {upcoming.map((event) => (
                <a key={event.id} href="/calendar" className="block min-w-0 py-3 first:pt-0 last:pb-0">
                  <div className="flex min-w-0 items-center justify-between gap-3">
                    <span className="truncate text-sm font-bold">{event.displayName}</span>
                    <Badge tone={event.importance === 'high' ? 'red' : event.importance === 'medium' ? 'yellow' : 'neutral'}>{event.importance}</Badge>
                  </div>
                  <div className="mt-1 truncate text-xs font-medium text-text-muted">{event.eventDateLocal} · {event.displayTime ?? event.eventTimeLocal ?? 'time pending'}</div>
                </a>
              ))}
            </div>
          ) : calendar.state.status === 'disabled' ? <DisabledState /> : calendar.state.status === 'error' ? <ErrorState /> : <EmptyState />}
        </Card>

        <Card title="News Preview" eyebrow="recent" tone="amber" className="2xl:col-span-6">
          <div className="divide-y divide-surface-border">
            {data.newsPreview.map((item) => (
              <a key={item.id} href={item.url ?? '/news'} className="block min-w-0 py-3 first:pt-0 last:pb-0">
                <div className="line-clamp-2 text-safe text-sm font-bold">{item.title}</div>
                <div className="mt-1 truncate text-xs font-medium text-text-muted">{item.source} · {timeAgo(item.publishedAt)}</div>
              </a>
            ))}
          </div>
        </Card>

        <Card title="Sentiment Mini Panel" eyebrow="optional pipeline" tone="green" className="2xl:col-span-6">
          {sentiment.state.status === 'success' && sentimentRows.length > 0 ? (
            <div className="space-y-3">
              {sentimentRows.map((row) => (
                <div key={row.id} className="min-w-0 rounded-[16px] border border-surface-border bg-white p-3 text-sm">
                  <div className="flex min-w-0 justify-between gap-3">
                    <span className="truncate font-semibold">{row.actor ?? row.sourceType ?? 'signal'} / {row.dimension ?? 'macro'}</span>
                    <span className="font-mono text-text-secondary">{fmt(row.stanceScore, 2)}</span>
                  </div>
                  <p className="mt-1 line-clamp-2 text-safe text-xs leading-5 text-text-muted">{row.evidence}</p>
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
    <div className="page-shell animate-fade-up">
      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <h1 className="text-3xl font-extrabold tracking-[-0.04em] text-text-primary">{title}</h1>
          {description && <p className="mt-3 max-w-3xl text-sm leading-7 text-text-secondary">{description}</p>}
        </div>
        {action}
      </div>
      {children}
    </div>
  )
}

function MetricChip({ label, value }: { label: string; value: number }) {
  return (
    <div className="flat-metric">
      <div className="text-[11px] font-bold uppercase tracking-[0.16em] text-text-muted">{label}</div>
      <div className="mt-2 font-mono text-2xl font-semibold text-text-primary">{value}</div>
    </div>
  )
}
