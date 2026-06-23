import { CalendarEvent } from '../../entities/calendarEvent/types'
import { useLanguage } from '../i18n'
import { Badge } from './Badge'

export function CalendarCompactList({ events, onSelect }: { events: CalendarEvent[]; onSelect: (event: CalendarEvent) => void }) {
  const { t, label } = useLanguage()

  return (
    <div className="divide-y divide-surface-border">
      {events.map((event) => (
        <button
          key={event.id}
          onClick={() => onSelect(event)}
          className="flex w-full min-w-0 items-start justify-between gap-2.5 py-2 text-left first:pt-0 last:pb-0"
        >
          <div className="min-w-0">
            <div className="flex min-w-0 flex-wrap items-center gap-1.5">
              <span className="truncate text-[12px] font-semibold text-text-primary lg:text-[13px]">{event.displayName}</span>
              <Badge tone={event.importance === 'high' ? 'red' : event.importance === 'medium' ? 'yellow' : 'neutral'}>
                {event.importanceLabel ?? label('importance', event.importance, event.importance)}
              </Badge>
            </div>
            <div className="mt-0.5 flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-[10px] text-text-muted">
              <span>{event.eventDateLocal}</span>
              <span>{event.displayTime ?? event.eventTimeLocal ?? t('dashboard.timePending')}</span>
              <span>{event.categoryLabel ?? label('category', event.category, event.category)}</span>
              <span>{event.statusLabel ?? label('status', event.status, event.status ?? '')}</span>
            </div>
          </div>
          <span className="hidden shrink-0 text-[10px] text-text-muted lg:block">
            {event.relatedIndicatorKeys.slice(0, 2).join(' · ')}
          </span>
        </button>
      ))}
    </div>
  )
}
