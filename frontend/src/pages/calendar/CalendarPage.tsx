import { useEffect, useMemo, useState } from 'react'
import { CalendarEvent, CalendarTodayBasis } from '../../entities/calendarEvent/types'
import { getCalendarEvents, getCalendarMonth, getFomcOverview } from '../../shared/api/calendar'
import { Badge } from '../../shared/components/Badge'
import { CalendarDayAgenda } from '../../shared/components/CalendarDayAgenda'
import { CalendarMonthGrid } from '../../shared/components/CalendarMonthGrid'
import { Card } from '../../shared/components/Card'
import { useLanguage } from '../../shared/i18n'
import { DisabledState, EmptyState, ErrorState, LoadingState } from '../../shared/components/StateViews'
import { useResource } from '../../shared/hooks/useResource'
import { selectDefaultCalendarDate, shiftMonthKey, toMonthKey } from '../../shared/utils/calendar'
import { fmtPct, fmtDate } from '../../shared/utils/format'

export function CalendarPage() {
  const { locale, t, label } = useLanguage()
  const [importance, setImportance] = useState('all')
  const [category, setCategory] = useState('all')
  const [monthKey, setMonthKey] = useState(() => toMonthKey(new Date()))
  const [todayBasis, setTodayBasis] = useState<CalendarTodayBasis>('market')
  const [selectedDate, setSelectedDate] = useState('')
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null)
  const browserTimeZone = typeof Intl !== 'undefined' ? Intl.DateTimeFormat().resolvedOptions().timeZone : 'Asia/Seoul'

  const month = useResource(
    () => getCalendarMonth({
      month: monthKey,
      importance: importance === 'all' ? undefined : importance,
      category: category === 'all' ? undefined : category,
      todayBasis,
      todayTz: todayBasis === 'local' ? browserTimeZone : undefined,
    }),
    [locale, monthKey, importance, category, todayBasis, browserTimeZone],
    { optional: true }
  )
  const agenda = useResource(
    () => selectedDate ? getCalendarEvents({
      from: selectedDate,
      to: selectedDate,
      includeDetails: true,
      importance: importance === 'all' ? undefined : importance,
      category: category === 'all' ? undefined : category,
    }) : Promise.resolve([]),
    [locale, selectedDate, importance, category],
    { optional: true }
  )
  const fomc = useResource(() => getFomcOverview(), [locale], { optional: true })

  useEffect(() => {
    if (month.state.status !== 'success') return
    const selectedDay = month.state.data.days.find((day) => day.date === selectedDate)
    if (!selectedDate || !selectedDay || selectedDay.eventCount === 0) {
      setSelectedDate(selectDefaultCalendarDate(month.state.data))
    }
  }, [month.state])

  useEffect(() => {
    setSelectedEvent(null)
  }, [selectedDate, importance, category, monthKey])

  const categories = useMemo(() => {
    if (month.state.status !== 'success') return []
    return Array.from(new Set(month.state.data.days.flatMap((day) => day.categories))).sort()
  }, [month.state])

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

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
        <Card title={t('calendar.card.month')} eyebrow={t('calendar.card.monthEyebrow')} tone="amber">
          {month.state.status === 'loading' || month.state.status === 'idle' ? <LoadingState /> : month.state.status === 'disabled' ? <DisabledState /> : month.state.status === 'error' ? <ErrorState /> : (
            <CalendarMonthGrid
              data={month.state.data}
              selectedDate={selectedDate}
              onSelectDate={setSelectedDate}
              onShiftMonth={(delta) => setMonthKey((current) => shiftMonthKey(current, delta))}
              todayBasis={todayBasis}
              onTodayBasisChange={setTodayBasis}
              size="full"
            />
          )}
        </Card>

        <div className="space-y-4">
          <Card title={t('calendar.card.selectedDay')} eyebrow={t('calendar.card.selectedDayEyebrow')}>
            {agenda.state.status === 'loading' || agenda.state.status === 'idle' ? <LoadingState /> : agenda.state.status === 'disabled' ? <DisabledState /> : agenda.state.status === 'error' ? <ErrorState /> : (
              <CalendarDayAgenda
                date={selectedDate || (month.state.status === 'success' ? month.state.data.todayDate : '')}
                events={agenda.state.status === 'success' ? agenda.state.data : []}
                onSelect={setSelectedEvent}
                emptyLabel={t('calendar.selectedDayEmpty')}
              />
            )}
          </Card>

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
                  <button
                    key={`${meeting.id ?? meeting.date}`}
                    onClick={() => {
                      const targetDate = meeting.eventDateLocal ?? meeting.date.slice(0, 10)
                      setMonthKey(toMonthKey(new Date(`${targetDate}T00:00:00`)))
                      setSelectedDate(targetDate)
                    }}
                    className="block w-full rounded-[20px] border border-surface-border/80 bg-white/75 px-4 py-3 text-left"
                  >
                    <div className="flex justify-between gap-3 text-sm">
                      <span className="font-semibold">{meeting.displayName ?? t('calendar.fomcMeetingFallback')}</span>
                      <span className="font-mono text-text-secondary">{fmtDate(meeting.eventDateLocal ?? meeting.date)}</span>
                    </div>
                    <div className="mt-1 text-xs text-text-muted">{t('calendar.rate')} {meeting.rate ?? '-'} · {t('calendar.change')} {meeting.changeBp ?? '-'}</div>
                  </button>
                ))}
              </div>
            ) : <EmptyState label={t('calendar.noFomcDetails')} />}
          </Card>
        </div>
      </div>

      {selectedEvent && (
        <div className="mt-4">
          <Card title={selectedEvent.displayName} eyebrow={fmtDate(selectedEvent.eventDateLocal)} tone="amber">
            <div className="flex flex-wrap gap-2">
              <Badge>{selectedEvent.categoryLabel ?? label('category', selectedEvent.category, selectedEvent.category)}</Badge>
              <Badge tone={selectedEvent.importance === 'high' ? 'red' : selectedEvent.importance === 'medium' ? 'yellow' : 'neutral'}>
                {selectedEvent.importanceLabel ?? label('importance', selectedEvent.importance, selectedEvent.importance)}
              </Badge>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <InfoBlock label={t('calendar.info.meaning')} value={selectedEvent.beginnerDescription} emptyLabel={t('calendar.noDescription')} />
              <InfoBlock label={t('calendar.info.why')} value={selectedEvent.whyItMatters} emptyLabel={t('calendar.noDescription')} />
              <ListBlock label={t('calendar.info.watch')} items={selectedEvent.watchItems} emptyLabel={t('calendar.noWatchItems')} />
              <ListBlock label={t('calendar.info.related')} items={selectedEvent.relatedIndicatorKeys} emptyLabel={t('calendar.noWatchItems')} monospace />
            </div>
          </Card>
        </div>
      )}
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
