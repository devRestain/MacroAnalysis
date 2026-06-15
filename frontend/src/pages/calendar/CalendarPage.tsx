import { useMemo, useState } from 'react'
import { getCalendarEvents, getFomcOverview } from '../../shared/api/calendar'
import { Badge } from '../../shared/components/Badge'
import { Card } from '../../shared/components/Card'
import { DisabledState, EmptyState, ErrorState, LoadingState } from '../../shared/components/StateViews'
import { useResource } from '../../shared/hooks/useResource'
import { fmtPct, fmtDate } from '../../shared/utils/format'

export function CalendarPage() {
  const [importance, setImportance] = useState('all')
  const [category, setCategory] = useState('all')
  const events = useResource(() => getCalendarEvents(30, true), [], { optional: true })
  const fomc = useResource(() => getFomcOverview(), [], { optional: true })

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
      <div className="mb-6">
        <h1 className="text-3xl font-extrabold tracking-[-0.04em]">Calendar</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-text-secondary">
          Economic releases, FOMC meetings, and watch items rendered as interpretation events rather than a simple date list.
        </p>
      </div>

      <div className="mb-5 flex flex-wrap items-center gap-2">
        {['all', 'high', 'medium', 'low'].map((item) => (
          <button key={item} onClick={() => setImportance(item)} className={`filter-chip ${importance === item ? 'filter-chip-active' : ''}`}>
            {item}
          </button>
        ))}
        <span className="mx-1 h-7 border-l border-surface-border" />
        {['all', ...categories].map((item) => (
          <button key={item} onClick={() => setCategory(item)} className={`filter-chip ${category === item ? 'filter-chip-active' : ''}`}>
            {item}
          </button>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <Card title="Upcoming Events" eyebrow="economic calendar" tone="amber">
          {events.state.status === 'loading' || events.state.status === 'idle' ? <LoadingState /> : events.state.status === 'disabled' ? <DisabledState /> : events.state.status === 'error' ? <ErrorState /> : filtered.length === 0 ? <EmptyState /> : (
            <div className="divide-y divide-surface-border">
              {filtered.map((event) => (
                <article key={event.id} className="py-4 first:pt-0 last:pb-0">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h2 className="text-lg font-extrabold tracking-[-0.02em]">{event.displayName}</h2>
                      <div className="mt-1 text-xs font-medium text-text-muted">{fmtDate(event.eventDateLocal)} · {event.displayTime ?? event.eventTimeLocal ?? 'time pending'} · {event.status}</div>
                    </div>
                    <div className="flex gap-2">
                      <Badge>{event.category}</Badge>
                      <Badge tone={event.importance === 'high' ? 'red' : event.importance === 'medium' ? 'yellow' : 'neutral'}>{event.importance}</Badge>
                    </div>
                  </div>
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    <InfoBlock label="의미" value={event.beginnerDescription} />
                    <InfoBlock label="왜 중요한가" value={event.whyItMatters} />
                    <ListBlock label="주의할 점" items={event.watchItems} />
                    <ListBlock label="관련 지표" items={event.relatedIndicatorKeys} monospace />
                  </div>
                </article>
              ))}
            </div>
          )}
        </Card>

        <div className="space-y-4">
          <Card title="FOMC Watch" eyebrow="calendar + detail" tone="rose">
            {fomc.state.status === 'success' ? (
              <div>
                <div className="text-xs font-bold uppercase tracking-[0.18em] text-text-muted">Next meeting</div>
                <div className="mt-2 text-2xl font-extrabold tracking-[-0.03em]">{nextFomc ? fmtDate(nextFomc.eventDateLocal ?? nextFomc.date) : 'No upcoming meeting'}</div>
                {fomc.state.data.fedwatch ? (
                  <div className="mt-4 grid grid-cols-3 gap-3">
                    <Prob label="Hold" value={fomc.state.data.fedwatch.probHold} />
                    <Prob label="Cut" value={fomc.state.data.fedwatch.probCut} />
                    <Prob label="Hike" value={fomc.state.data.fedwatch.probHike} />
                  </div>
                ) : <EmptyState label="No FedWatch estimate collected." />}
              </div>
            ) : fomc.state.status === 'disabled' ? <DisabledState /> : fomc.state.status === 'error' ? <ErrorState /> : <LoadingState />}
          </Card>

          <Card title="FOMC Details" eyebrow="documents and outcomes" tone="blue">
            {fomc.state.status === 'success' && fomc.state.data.meetings.length > 0 ? (
              <div className="space-y-3">
                {fomc.state.data.meetings.slice(0, 6).map((meeting) => (
                  <div key={`${meeting.id ?? meeting.date}`} className="rounded-[20px] border border-surface-border/80 bg-white/75 px-4 py-3">
                    <div className="flex justify-between gap-3 text-sm">
                      <span className="font-semibold">{meeting.displayName ?? 'FOMC Meeting'}</span>
                      <span className="font-mono text-text-secondary">{fmtDate(meeting.eventDateLocal ?? meeting.date)}</span>
                    </div>
                    <div className="mt-1 text-xs text-text-muted">Rate {meeting.rate ?? '-'} · Change {meeting.changeBp ?? '-'}</div>
                  </div>
                ))}
              </div>
            ) : <EmptyState label="No FOMC detail records available." />}
          </Card>
        </div>
      </div>
    </div>
  )
}

function InfoBlock({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="rounded-[20px] border border-surface-border/80 bg-white/78 p-4">
      <div className="text-xs font-extrabold uppercase tracking-[0.18em] text-text-muted">{label}</div>
      <p className="mt-2 text-sm leading-6 text-text-secondary">{value || 'No description available.'}</p>
    </div>
  )
}

function ListBlock({ label, items, monospace = false }: { label: string; items: string[]; monospace?: boolean }) {
  return (
    <div className="rounded-[20px] border border-surface-border/80 bg-white/78 p-4">
      <div className="text-xs font-extrabold uppercase tracking-[0.18em] text-text-muted">{label}</div>
      {items.length > 0 ? (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {items.map((item) => <Badge key={item}>{monospace ? <span className="font-mono">{item}</span> : item}</Badge>)}
        </div>
      ) : <p className="mt-2 text-sm text-text-muted">No watch items.</p>}
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
