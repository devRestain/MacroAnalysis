import { useMemo, useState } from 'react'
import { getCalendarEvents, getFomcOverview } from '../../shared/api/calendar'
import { Badge } from '../../shared/components/Badge'
import { Card } from '../../shared/components/Card'
import { useLanguage } from '../../shared/i18n'
import { DisabledState, EmptyState, ErrorState, LoadingState } from '../../shared/components/StateViews'
import { useResource } from '../../shared/hooks/useResource'
import { fmtPct, fmtDate } from '../../shared/utils/format'

export function CalendarPage() {
  const { locale, t, label } = useLanguage()
  const [importance, setImportance] = useState('all')
  const [category, setCategory] = useState('all')
  const events = useResource(() => getCalendarEvents(30, true), [locale], { optional: true })
  const fomc = useResource(() => getFomcOverview(), [locale], { optional: true })

  const categories = useMemo(() => {
    if (events.state.status !== 'success') return []
    return Array.from(new Set(events.state.data.map((event) => event.category))).sort()
  }, [events.state])

  const filtered = events.state.status === 'success'
    ? events.state.data.filter((event) => (importance === 'all' || event.importance === importance) && (category === 'all' || event.category === category))
    : []
  const nextFomc = fomc.state.status === 'success'
    ? fomc.state.data.meetings.find((meeting) => new Date(meeting.date).getTime() >= Date.now())
    : undefined

  return (
    <div className="page-shell animate-fade-up">
      <div className="mb-5 flex flex-wrap items-center gap-2">
        {['all', 'high', 'medium', 'low'].map((item) => (
          <button key={item} onClick={() => setImportance(item)} className={`filter-chip ${importance === item ? 'filter-chip-active' : ''}`}>
            {label('importance', item, item)}
          </button>
        ))}
        <span className="mx-1 h-7 border-l border-surface-border" />
        {['all', ...categories].map((item) => (
          <button key={item} onClick={() => setCategory(item)} className={`filter-chip ${category === item ? 'filter-chip-active' : ''}`}>
            {item === 'all' ? t('calendar.filter.all') : label('category', item, item)}
          </button>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <Card title={t('calendar.card.upcoming')} eyebrow={t('calendar.card.upcomingEyebrow')} tone="amber">
          {events.state.status === 'loading' || events.state.status === 'idle' ? <LoadingState /> : events.state.status === 'disabled' ? <DisabledState /> : events.state.status === 'error' ? <ErrorState /> : filtered.length === 0 ? <EmptyState /> : (
            <div className="divide-y divide-surface-border">
              {filtered.map((event) => (
                <article key={event.id} className="py-4 first:pt-0 last:pb-0">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h2 className="text-lg font-extrabold tracking-[-0.02em]">{event.displayName}</h2>
                      <div className="mt-1 text-xs font-medium text-text-muted">{fmtDate(event.eventDateLocal)} · {event.displayTime ?? event.eventTimeLocal ?? t('calendar.timePending')} · {event.statusLabel ?? label('status', event.status, event.status ?? '')}</div>
                    </div>
                    <div className="flex gap-2">
                      <Badge>{event.categoryLabel ?? event.category}</Badge>
                      <Badge tone={event.importance === 'high' ? 'red' : event.importance === 'medium' ? 'yellow' : 'neutral'}>{event.importanceLabel ?? label('importance', event.importance, event.importance)}</Badge>
                    </div>
                  </div>
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    <InfoBlock label={t('calendar.info.meaning')} value={event.beginnerDescription} emptyLabel={t('calendar.noDescription')} />
                    <InfoBlock label={t('calendar.info.why')} value={event.whyItMatters} emptyLabel={t('calendar.noDescription')} />
                    <ListBlock label={t('calendar.info.watch')} items={event.watchItems} emptyLabel={t('calendar.noWatchItems')} />
                    <ListBlock label={t('calendar.info.related')} items={event.relatedIndicatorKeys} emptyLabel={t('calendar.noWatchItems')} monospace />
                  </div>
                </article>
              ))}
            </div>
          )}
        </Card>

        <div className="space-y-4">
          <Card title={t('calendar.card.fomcWatch')} eyebrow={t('calendar.card.fomcWatchEyebrow')} tone="rose">
            {fomc.state.status === 'success' ? (
              <div>
                <div className="text-xs font-bold uppercase tracking-[0.18em] text-text-muted">{t('calendar.nextMeeting')}</div>
                <div className="mt-2 text-2xl font-extrabold tracking-[-0.03em]">{nextFomc ? fmtDate(nextFomc.eventDateLocal ?? nextFomc.date) : t('calendar.noUpcomingMeeting')}</div>
                {fomc.state.data.fedwatch ? (
                <div className="mt-4 grid grid-cols-3 gap-3">
                    <Prob label={t('calendar.prob.hold')} value={fomc.state.data.fedwatch.probHold} />
                    <Prob label={t('calendar.prob.cut')} value={fomc.state.data.fedwatch.probCut} />
                    <Prob label={t('calendar.prob.hike')} value={fomc.state.data.fedwatch.probHike} />
                  </div>
                ) : <EmptyState label={t('calendar.noFedWatch')} />}
              </div>
            ) : fomc.state.status === 'disabled' ? <DisabledState /> : fomc.state.status === 'error' ? <ErrorState /> : <LoadingState />}
          </Card>

          <Card title={t('calendar.card.fomcDetails')} eyebrow={t('calendar.card.fomcDetailsEyebrow')} tone="blue">
            {fomc.state.status === 'success' && fomc.state.data.meetings.length > 0 ? (
              <div className="space-y-3">
                {fomc.state.data.meetings.slice(0, 6).map((meeting) => (
                  <div key={`${meeting.id ?? meeting.date}`} className="rounded-[20px] border border-surface-border/80 bg-white/75 px-4 py-3">
                    <div className="flex justify-between gap-3 text-sm">
                      <span className="font-semibold">{meeting.displayName ?? t('calendar.fomcMeetingFallback')}</span>
                      <span className="font-mono text-text-secondary">{fmtDate(meeting.eventDateLocal ?? meeting.date)}</span>
                    </div>
                    <div className="mt-1 text-xs text-text-muted">{t('calendar.rate')} {meeting.rate ?? '-'} · {t('calendar.change')} {meeting.changeBp ?? '-'}</div>
                  </div>
                ))}
              </div>
            ) : <EmptyState label={t('calendar.noFomcDetails')} />}
          </Card>
        </div>
      </div>
    </div>
  )
}

function InfoBlock({ label, value, emptyLabel }: { label: string; value?: string | null; emptyLabel: string }) {
  return (
    <div className="rounded-[20px] border border-surface-border/80 bg-white/78 p-4">
      <div className="text-xs font-extrabold uppercase tracking-[0.18em] text-text-muted">{label}</div>
      <p className="mt-2 text-sm leading-6 text-text-secondary">{value || emptyLabel}</p>
    </div>
  )
}

function ListBlock({ label, items, emptyLabel, monospace = false }: { label: string; items: string[]; emptyLabel: string; monospace?: boolean }) {
  return (
    <div className="rounded-[20px] border border-surface-border/80 bg-white/78 p-4">
      <div className="text-xs font-extrabold uppercase tracking-[0.18em] text-text-muted">{label}</div>
      {items.length > 0 ? (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {items.map((item) => <Badge key={item}>{monospace ? <span className="font-mono">{item}</span> : item}</Badge>)}
        </div>
      ) : <p className="mt-2 text-sm text-text-muted">{emptyLabel}</p>}
    </div>
  )
}

function Prob({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="rounded-[18px] border border-surface-border bg-white p-4 text-center">
      <div className="text-xs font-extrabold uppercase tracking-[0.18em] text-text-muted">{label}</div>
      <div className="mt-2 font-mono text-2xl font-semibold">{fmtPct(value, 0, 'ratio')}</div>
    </div>
  )
}
