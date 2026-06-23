import { ExternalLink } from 'lucide-react'
import { ReactNode, useEffect, useMemo, useState } from 'react'
import { AiSummary } from '../../entities/aiSummary/types'
import { CalendarEvent } from '../../entities/calendarEvent/types'
import { ChangeSnapshot } from '../../entities/changeSnapshot/types'
import { IndicatorHistory } from '../../entities/observation/types'
import { SentimentSignal } from '../../entities/sentiment/types'
import { getTypedAiSummary } from '../../shared/api/ai'
import { getCalendarEvents, getCalendarMonth, getFomcOverview } from '../../shared/api/calendar'
import { DashboardSummary, getDashboardSummary, getSectors, SectorRow } from '../../shared/api/dashboard'
import { getIndicatorExplanation, getIndicatorHistory } from '../../shared/api/indicators'
import { getSentimentSignals } from '../../shared/api/sentiment'
import { AiSummaryPanel } from '../../shared/components/AiSummaryPanel'
import { Badge } from '../../shared/components/Badge'
import { CalendarDayAgenda } from '../../shared/components/CalendarDayAgenda'
import { CalendarMonthGrid } from '../../shared/components/CalendarMonthGrid'
import { Card } from '../../shared/components/Card'
import { InsightDrawer } from '../../shared/components/InsightDrawer'
import { MetricTile } from '../../shared/components/MetricTile'
import { DisabledState, EmptyState, ErrorState, LoadingState } from '../../shared/components/StateViews'
import { useLanguage } from '../../shared/i18n'
import { useResource } from '../../shared/hooks/useResource'
import { selectDefaultCalendarDate, shiftMonthKey, toMonthKey } from '../../shared/utils/calendar'
import { compactText, fmt, fmtDate, fmtPct, timeAgo } from '../../shared/utils/format'

type DrawerState =
  | { kind: 'indicator'; item: ChangeSnapshot }
  | { kind: 'calendar'; event: CalendarEvent }
  | { kind: 'ai'; summary?: AiSummary | null; fallbackHeadline?: string | null; fallbackDate?: string | null }
  | null

export function DashboardPage() {
  const { locale, t, label } = useLanguage()
  const [drawer, setDrawer] = useState<DrawerState>(null)
  const [calendarMonthKey, setCalendarMonthKey] = useState(() => toMonthKey(new Date()))
  const [selectedDate, setSelectedDate] = useState('')

  const summary = useResource(() => getDashboardSummary(), [locale], { refreshInterval: 5 * 60 * 1000 })
  const sectors = useResource(() => getSectors(), [], { refreshInterval: 30 * 60 * 1000, optional: true })
  const calendarMonth = useResource(
    () => getCalendarMonth({ month: calendarMonthKey, todayBasis: 'market' }),
    [locale, calendarMonthKey],
    { optional: true }
  )
  const calendarAgenda = useResource(
    () => selectedDate ? getCalendarEvents({ from: selectedDate, to: selectedDate, includeDetails: true }) : Promise.resolve([]),
    [locale, selectedDate],
    { optional: true }
  )
  const sentiment = useResource(() => getSentimentSignals(5), [], { optional: true })
  const aiMacro = useResource(() => getTypedAiSummary('macro', { days: 7 }), [locale], { optional: true, refreshInterval: 30 * 60 * 1000 })
  const fomc = useResource(() => getFomcOverview(), [locale], { optional: true })

  useEffect(() => {
    const onRefresh = () => {
      summary.reload()
      sectors.reload()
      calendarMonth.reload()
      calendarAgenda.reload()
      sentiment.reload()
      aiMacro.reload()
      fomc.reload()
    }
    window.addEventListener('macro:dashboard-refresh', onRefresh as EventListener)
    return () => window.removeEventListener('macro:dashboard-refresh', onRefresh as EventListener)
  }, [summary, sectors, calendarMonth, calendarAgenda, sentiment, aiMacro, fomc])

  useEffect(() => {
    if (calendarMonth.state.status !== 'success') return
    const selectedDay = calendarMonth.state.data.days.find((day) => day.date === selectedDate)
    if (!selectedDate || !selectedDay || selectedDay.eventCount === 0) {
      setSelectedDate(selectDefaultCalendarDate(calendarMonth.state.data))
    }
  }, [calendarMonth.state])

  if (summary.state.status === 'loading' || summary.state.status === 'idle') {
    return <PageFrame><LoadingState /></PageFrame>
  }

  if (summary.state.status === 'error' || summary.state.status === 'disabled') {
    return <PageFrame><ErrorState label={t('dashboard.summaryUnavailable')} /></PageFrame>
  }

  if (summary.state.status === 'empty') {
    return <PageFrame><EmptyState label={t('dashboard.summaryEmpty')} /></PageFrame>
  }

  const data = summary.state.data
  const topSignals = [...data.alerts, ...Object.values(data.snapshots)]
    .filter((item, index, all) => all.findIndex((candidate) => candidate.key === item.key) === index)
    .slice(0, 10)
  const sentimentRows = sentiment.state.status === 'success' ? sentiment.state.data.slice(0, 4) : []
  const aiSummary = aiMacro.state.status === 'success' ? aiMacro.state.data : undefined
  const nextMeeting = fomc.state.status === 'success'
    ? fomc.state.data.meetings.find((meeting) => new Date(meeting.eventDateLocal ?? meeting.date).getTime() >= Date.now())
    : undefined

  return (
    <PageFrame>
      <Card title={t('dashboard.card.aiHeadline')} eyebrow={t('dashboard.card.aiHeadlineEyebrow')} tone="blue" className="mb-2.5">
        {aiMacro.state.status === 'disabled' ? (
          <DisabledState label={t('ai.summaryDisabled')} />
        ) : aiMacro.state.status === 'error' ? (
          <AiSummaryPanel
            fallbackHeadline={data.aiHeadline}
            fallbackDate={data.aiAsOfDate}
            onOpen={() => setDrawer({ kind: 'ai', fallbackHeadline: data.aiHeadline, fallbackDate: data.aiAsOfDate })}
          />
        ) : (
          <AiSummaryPanel
            summary={aiSummary}
            fallbackHeadline={data.aiHeadline}
            fallbackDate={data.aiAsOfDate}
            onOpen={() => setDrawer({ kind: 'ai', summary: aiSummary, fallbackHeadline: data.aiHeadline, fallbackDate: data.aiAsOfDate })}
          />
        )}
      </Card>

      <div className="grid gap-2.5 xl:grid-cols-12">
        <Card title={t('dashboard.card.marketOverview')} eyebrow={t('dashboard.card.marketOverviewEyebrow')} className="xl:col-span-9 2xl:col-span-9">
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
            {topSignals.map((item) => (
              <MetricTile key={item.key} item={item} onClick={() => setDrawer({ kind: 'indicator', item })} />
            ))}
          </div>
        </Card>

        <Card title={t('dashboard.card.calendarWatch')} eyebrow={t('dashboard.card.calendarWatchEyebrow')} tone="amber" className="xl:col-span-3 2xl:col-span-3">
          {calendarMonth.state.status === 'success' ? (
            <div>
              <CalendarMonthGrid
                data={calendarMonth.state.data}
                selectedDate={selectedDate}
                onSelectDate={setSelectedDate}
                onShiftMonth={(delta) => setCalendarMonthKey((current) => shiftMonthKey(current, delta))}
                todayBasis="market"
                onTodayBasisChange={() => undefined}
                size="compact"
                showTodayBasisToggle={false}
              />
              <div className="mt-4 border-t border-surface-border pt-4">
                {calendarAgenda.state.status === 'success' || calendarAgenda.state.status === 'empty' ? (
                  <CalendarDayAgenda
                    date={selectedDate || calendarMonth.state.data.todayDate}
                    events={calendarAgenda.state.status === 'success' ? calendarAgenda.state.data : []}
                    onSelect={(event) => setDrawer({ kind: 'calendar', event })}
                    emptyLabel={t('calendar.selectedDayEmpty')}
                    maxItems={4}
                  />
                ) : calendarAgenda.state.status === 'disabled' ? <DisabledState /> : calendarAgenda.state.status === 'error' ? <EmptyState label={t('calendar.selectedDayEmpty')} /> : <LoadingState />}
              </div>
            </div>
          ) : calendarMonth.state.status === 'disabled' ? <DisabledState /> : calendarMonth.state.status === 'error' ? <ErrorState /> : <LoadingState />}
        </Card>

        <Card title={t('dashboard.card.yieldCurve')} eyebrow={t('dashboard.card.yieldCurveEyebrow')} tone="green" className="xl:col-span-4 2xl:col-span-4">
          <div className="grid gap-2 sm:grid-cols-2">
            {Object.entries(data.yieldCurve).map(([key, value]) => (
              <div key={key} className="rounded-[14px] border border-surface-border bg-white px-3 py-2.5">
                <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-text-muted">{key}</div>
                <div className="mt-1 font-mono text-lg font-semibold tracking-[-0.04em] text-text-primary">{fmt(value, 2)}</div>
              </div>
            ))}
          </div>
          <div className="mt-2.5 rounded-[14px] border border-surface-border bg-surface-hover px-3 py-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-text-muted">{t('dashboard.fomcPulse')}</div>
                <div className="mt-0.5 text-sm font-bold tracking-[-0.03em] text-text-primary">
                  {nextMeeting ? fmtDate(nextMeeting.eventDateLocal ?? nextMeeting.date) : t('calendar.noUpcomingMeeting')}
                </div>
              </div>
              {data.fomc?.probHold != null && <Badge tone="blue">{t('calendar.prob.hold')} {fmtPct(data.fomc.probHold, 0, 'ratio')}</Badge>}
            </div>
            {fomc.state.status === 'success' && fomc.state.data.fedwatch ? (
              <div className="mt-2.5 grid grid-cols-3 gap-1.5 text-xs">
                <ProbabilityStat label={t('calendar.prob.hold')} value={fomc.state.data.fedwatch.probHold} />
                <ProbabilityStat label={t('calendar.prob.cut')} value={fomc.state.data.fedwatch.probCut} />
                <ProbabilityStat label={t('calendar.prob.hike')} value={fomc.state.data.fedwatch.probHike} />
              </div>
            ) : (
              <div className="mt-2 text-[12px] text-text-muted">{t('calendar.noFedWatch')}</div>
            )}
          </div>
        </Card>

        <Card title={t('dashboard.card.equitySectors')} eyebrow={t('dashboard.card.equitySectorsEyebrow')} className="xl:col-span-4 2xl:col-span-4">
          {sectors.state.status === 'success' ? (
            <div className="space-y-2">
              {sectors.state.data.slice(0, 7).map((row) => (
                <SectorRowView key={row.ticker} row={row} />
              ))}
            </div>
          ) : sectors.state.status === 'disabled' ? <DisabledState /> : sectors.state.status === 'error' ? <ErrorState /> : <LoadingState />}
        </Card>

        <Card title={t('dashboard.card.sentimentPanel')} eyebrow={t('dashboard.card.sentimentPanelEyebrow')} className="xl:col-span-4 2xl:col-span-4">
          {sentiment.state.status === 'success' && sentimentRows.length > 0 ? (
            <div className="space-y-2">
              {sentimentRows.map((row) => (
                <SentimentCard key={row.id ?? `${row.actor}-${row.dimension}`} row={row} />
              ))}
            </div>
          ) : sentiment.state.status === 'disabled' ? <DisabledState /> : sentiment.state.status === 'error' ? <ErrorState /> : <EmptyState label={t('dashboard.sentimentEmpty')} />}
        </Card>

        <Card title={t('dashboard.card.newsPreview')} eyebrow={t('dashboard.card.newsPreviewEyebrow')} tone="amber" className="xl:col-span-12 2xl:col-span-12">
          <div className="divide-y divide-surface-border">
            {data.newsPreview.map((item) => (
              <a
                key={item.id}
                href={item.url ?? '/news'}
                target={item.url ? '_blank' : undefined}
                rel={item.url ? 'noreferrer' : undefined}
                className="block rounded-[14px] px-2 py-2.5 first:pt-0 last:pb-0 hover:bg-white/70"
              >
                <div className="flex items-start gap-2.5">
                  <Badge>{label('newsCategory', item.category, item.category)}</Badge>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start gap-1.5">
                      <div className="line-clamp-2 text-safe text-[12px] font-semibold leading-5 text-text-primary">{item.title}</div>
                      {item.url && <ExternalLink size={11} className="mt-0.5 shrink-0 text-text-muted" />}
                    </div>
                    {item.summary && <p className="mt-1 line-clamp-2 text-[11px] leading-4 text-text-secondary">{item.summary}</p>}
                    <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[10px] text-text-muted">
                      <span>{item.source}</span>
                      <span>{timeAgo(item.publishedAt)}</span>
                    </div>
                  </div>
                </div>
              </a>
            ))}
          </div>
        </Card>
      </div>

      <DashboardDrawer drawer={drawer} onClose={() => setDrawer(null)} summary={data} />
    </PageFrame>
  )
}

function DashboardDrawer({ drawer, onClose, summary }: { drawer: DrawerState; onClose: () => void; summary: DashboardSummary }) {
  const { t } = useLanguage()

  if (!drawer) return null

  if (drawer.kind === 'indicator') {
    return (
      <InsightDrawer
        open
        onClose={onClose}
        title={drawer.item.label}
        subtitle={`${drawer.item.key} · ${fmtDate(drawer.item.date)}`}
      >
        <IndicatorDrawerContent item={drawer.item} />
      </InsightDrawer>
    )
  }

  if (drawer.kind === 'calendar') {
    return (
      <InsightDrawer
        open
        onClose={onClose}
        title={drawer.event.displayName}
        subtitle={`${drawer.event.eventDateLocal ?? '-'} · ${drawer.event.displayTime ?? drawer.event.eventTimeLocal ?? t('dashboard.timePending')}`}
      >
        <CalendarDrawerContent event={drawer.event} />
      </InsightDrawer>
    )
  }

  const headline = drawer.summary?.headline ?? drawer.fallbackHeadline ?? summary.aiHeadline ?? t('dashboard.aiHeadlineEmpty')
  const body = drawer.summary?.body ?? t('dashboard.aiFallbackBody')
  return (
    <InsightDrawer
      open
      onClose={onClose}
      title={headline}
      subtitle={`${drawer.summary?.summaryDate ?? drawer.fallbackDate ?? summary.aiAsOfDate ?? '-'} · ${drawer.summary?.modelUsed ?? t('ai.modelUnavailable')}`}
    >
      <article className="space-y-5">
        <p className="whitespace-pre-wrap text-sm leading-7 text-text-secondary">{body}</p>
        <a href="/ai" className="inline-flex rounded-full border border-surface-border bg-white px-4 py-2 text-sm font-bold text-text-secondary">
          {t('dashboard.openBriefings')}
        </a>
      </article>
    </InsightDrawer>
  )
}

function IndicatorDrawerContent({ item }: { item: ChangeSnapshot }) {
  const { locale, t } = useLanguage()
  const explanation = useResource(() => getIndicatorExplanation(item.key), [item.key, locale], { optional: true })
  const history = useResource(() => getIndicatorHistory(item.key, '3m'), [item.key], { optional: true })
  const chartPath = useMemo(() => {
    if (history.state.status !== 'success') return ''
    const points = history.state.data.data.filter((point) => point.value != null)
    if (points.length === 0) return ''
    return buildLinePath(points)
  }, [history.state])

  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <DrawerMetric label={t('indicatorDetail.metric.latest')} value={fmt(item.value, 2, item.unit ?? '')} />
        <DrawerMetric label={t('indicatorDetail.metric.day1')} value={fmtPct(item.delta1dPct)} />
        <DrawerMetric label={t('indicatorDetail.metric.month1')} value={fmtPct(item.delta1mPct)} />
        <DrawerMetric label={t('indicatorDetail.metric.zScore')} value={fmt(item.zScore1y, 2)} />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
        <Card title={t('indicatorDetail.card.history')} eyebrow={t('dashboard.drawer.latestTrend')} tone="blue">
          {history.state.status === 'loading' || history.state.status === 'idle' ? <LoadingState /> : history.state.status === 'disabled' ? <DisabledState /> : history.state.status === 'error' ? <ErrorState label={t('indicatorDetail.historyUnavailable')} /> : history.state.status === 'empty' ? <EmptyState label={t('indicatorDetail.historyEmpty')} /> : (
            <div className="h-56">
              <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="h-full w-full overflow-visible">
                <path d={chartPath} fill="none" stroke="#2457d6" strokeWidth="1.75" vectorEffect="non-scaling-stroke" />
              </svg>
            </div>
          )}
        </Card>

        <Card title={t('indicatorDetail.card.explanation')} eyebrow={t('indicatorDetail.card.explanationEyebrow')}>
          {explanation.state.status === 'success' ? (
            <div className="space-y-4 text-sm leading-7 text-text-secondary">
              <p>{compactText(explanation.state.data.description, t('indicatorDetail.descriptionMissing'))}</p>
              <p>{compactText(explanation.state.data.whyItMatters, t('indicatorDetail.descriptionMissing'))}</p>
              {explanation.state.data.relatedIndicatorKeys && explanation.state.data.relatedIndicatorKeys.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {explanation.state.data.relatedIndicatorKeys.map((related) => <Badge key={related}>{related}</Badge>)}
                </div>
              )}
            </div>
          ) : explanation.state.status === 'disabled' ? <DisabledState /> : explanation.state.status === 'error' ? <EmptyState label={t('indicatorDetail.explanationMissing')} /> : <LoadingState />}
        </Card>
      </div>

      <a href={`/indicators/${encodeURIComponent(item.key)}`} className="inline-flex rounded-full border border-surface-border bg-white px-4 py-2 text-sm font-bold text-text-secondary">
        {t('dashboard.viewIndicator')}
      </a>
    </div>
  )
}

function CalendarDrawerContent({ event }: { event: CalendarEvent }) {
  const { t, label } = useLanguage()
  const detailEntries = extractDetailEntries(event.details)

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2">
        <Badge>{event.categoryLabel ?? label('category', event.category, event.category)}</Badge>
        <Badge tone={event.importance === 'high' ? 'red' : event.importance === 'medium' ? 'yellow' : 'neutral'}>
          {event.importanceLabel ?? label('importance', event.importance, event.importance)}
        </Badge>
        <Badge>{event.statusLabel ?? label('status', event.status, event.status ?? '')}</Badge>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <InfoCard title={t('calendar.info.meaning')} body={compactText(event.beginnerDescription, t('calendar.noDescription'))} />
        <InfoCard title={t('calendar.info.why')} body={compactText(event.whyItMatters, t('calendar.noDescription'))} />
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <ListInfoCard title={t('calendar.info.watch')} items={event.watchItems} emptyLabel={t('calendar.noWatchItems')} />
        <ListInfoCard title={t('calendar.info.related')} items={event.relatedIndicatorKeys} emptyLabel={t('calendar.noWatchItems')} monospace />
      </div>
      {detailEntries.length > 0 && (
        <Card title={t('dashboard.drawer.details')} eyebrow={t('dashboard.drawer.detailsEyebrow')}>
          <div className="grid gap-3 sm:grid-cols-2">
            {detailEntries.map(([key, value]) => (
              <div key={key} className="rounded-[16px] border border-surface-border bg-surface-hover px-4 py-3">
                <div className="text-[11px] font-bold uppercase tracking-[0.16em] text-text-muted">{key}</div>
                <div className="mt-2 text-sm text-text-secondary">{String(value)}</div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}

function PageFrame({ children }: { children: ReactNode }) {
  return (
    <div className="dashboard-shell animate-fade-up">
      {children}
    </div>
  )
}

function ProbabilityStat({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="rounded-[12px] border border-surface-border bg-white px-2 py-2 text-center">
      <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-text-muted">{label}</div>
      <div className="mt-1 font-mono text-[13px] font-semibold text-text-primary">{fmtPct(value, 0, 'ratio')}</div>
    </div>
  )
}

function SectorRowView({ row }: { row: SectorRow }) {
  return (
    <div className="grid min-w-0 grid-cols-[50px_minmax(0,1fr)_56px_56px] items-center gap-2 rounded-[12px] border border-surface-border bg-white px-2.5 py-2 text-[10px]">
      <span className="font-mono text-text-secondary">{row.ticker}</span>
      <span className="truncate font-semibold text-text-primary">{row.name}</span>
      <span className={`text-right font-semibold ${row.change1d != null && row.change1d < 0 ? 'text-signal-red' : 'text-signal-green'}`}>{fmtPct(row.change1d)}</span>
      <span className={`text-right font-semibold ${row.change1m != null && row.change1m < 0 ? 'text-signal-red' : 'text-signal-green'}`}>{fmtPct(row.change1m)}</span>
    </div>
  )
}

function SentimentCard({ row }: { row: SentimentSignal }) {
  const { label } = useLanguage()
  return (
    <div className="rounded-[12px] border border-surface-border bg-white px-3 py-2.5">
      <div className="flex min-w-0 items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-[12px] font-semibold text-text-primary">
            {row.actor ?? label('sourceType', row.sourceType, 'signal')} / {row.dimension ?? 'macro'}
          </div>
          <div className="mt-0.5 text-[10px] text-text-muted">{row.stance ?? '-'}</div>
        </div>
        <div className="font-mono text-[12px] font-semibold text-text-secondary">{fmt(row.stanceScore, 2)}</div>
      </div>
      <p className="mt-1.5 line-clamp-2 text-[12px] leading-4 text-text-secondary">{compactText(row.evidence)}</p>
    </div>
  )
}

function DrawerMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[16px] border border-surface-border bg-surface-hover px-4 py-3">
      <div className="text-[11px] font-bold uppercase tracking-[0.16em] text-text-muted">{label}</div>
      <div className="mt-2 font-mono text-xl font-semibold tracking-[-0.04em] text-text-primary">{value}</div>
    </div>
  )
}

function InfoCard({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-[18px] border border-surface-border bg-surface-hover px-4 py-4">
      <div className="text-[11px] font-bold uppercase tracking-[0.16em] text-text-muted">{title}</div>
      <p className="mt-3 text-sm leading-7 text-text-secondary">{body}</p>
    </div>
  )
}

function ListInfoCard({ title, items, emptyLabel, monospace = false }: { title: string; items: string[]; emptyLabel: string; monospace?: boolean }) {
  return (
    <div className="rounded-[18px] border border-surface-border bg-surface-hover px-4 py-4">
      <div className="text-[11px] font-bold uppercase tracking-[0.16em] text-text-muted">{title}</div>
      {items.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {items.map((item) => <Badge key={item}>{monospace ? <span className="font-mono">{item}</span> : item}</Badge>)}
        </div>
      ) : (
        <p className="mt-3 text-sm text-text-muted">{emptyLabel}</p>
      )}
    </div>
  )
}

function extractDetailEntries(details?: Record<string, unknown> | null): [string, string | number | boolean][] {
  if (!details) return []
  const entries: [string, string | number | boolean][] = []
  for (const [key, value] of Object.entries(details)) {
    if (value == null) continue
    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
      entries.push([key, value])
      continue
    }
    if (typeof value === 'object') {
      for (const [nestedKey, nestedValue] of Object.entries(value as Record<string, unknown>)) {
        if (nestedValue == null) continue
        if (typeof nestedValue === 'string' || typeof nestedValue === 'number' || typeof nestedValue === 'boolean') {
          entries.push([`${key}.${nestedKey}`, nestedValue])
        }
      }
    }
  }
  return entries
}

function buildLinePath(points: IndicatorHistory['data']): string {
  const numeric = points.filter((point) => point.value != null)
  if (numeric.length === 0) return ''
  const values = numeric.map((point) => point.value as number)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  return numeric.map((point, index) => {
    const x = (index / Math.max(numeric.length - 1, 1)) * 100
    const y = 100 - (((point.value as number) - min) / span) * 100
    return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`
  }).join(' ')
}
