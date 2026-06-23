import { CalendarEvent } from '../../entities/calendarEvent/types'
import { useLanguage } from '../i18n'
import { fmtDate } from '../utils/format'
import { Badge } from './Badge'

export function CalendarDayAgenda({
  date,
  events,
  onSelect,
  emptyLabel,
  maxItems,
}: {
  date: string
  events: CalendarEvent[]
  onSelect: (event: CalendarEvent) => void
  emptyLabel: string
  maxItems?: number
}) {
  const { t, label } = useLanguage()
  const items = typeof maxItems === 'number' ? events.slice(0, maxItems) : events

  return (
    <div>
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-text-muted">{t('calendar.selectedDate')}</div>
          <div className="mt-1 text-sm font-bold tracking-[-0.02em] text-text-primary">{fmtDate(date)}</div>
        </div>
        <div className="text-[11px] text-text-muted">{events.length} {t('calendar.eventsUnit')}</div>
      </div>

      {items.length > 0 ? (
        <div className="space-y-2">
          {items.map((event) => (
            <button
              key={event.id}
              onClick={() => onSelect(event)}
              className="block w-full rounded-[16px] border border-surface-border bg-white px-3 py-3 text-left transition hover:bg-surface-hover"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold text-text-primary">{event.displayName}</div>
                  <div className="mt-1 text-[11px] text-text-muted">
                    {event.displayTime ?? event.eventTimeLocal ?? t('calendar.timePending')} · {event.statusLabel ?? label('status', event.status, event.status ?? '')}
                  </div>
                </div>
                <Badge tone={event.importance === 'high' ? 'red' : event.importance === 'medium' ? 'yellow' : 'neutral'}>
                  {event.importanceLabel ?? label('importance', event.importance, event.importance)}
                </Badge>
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                <Badge>{event.categoryLabel ?? label('category', event.category, event.category)}</Badge>
                {event.relatedIndicatorKeys.slice(0, 2).map((item) => <Badge key={item}><span className="font-mono">{item}</span></Badge>)}
              </div>
            </button>
          ))}
        </div>
      ) : (
        <div className="rounded-[18px] border border-dashed border-surface-border bg-surface-hover px-4 py-6 text-sm text-text-muted">
          {emptyLabel}
        </div>
      )}
    </div>
  )
}
