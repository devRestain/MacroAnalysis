import { CalendarEvent, FomcOverview } from '../../entities/calendarEvent/types'
import { apiGet } from './client'

interface CalendarEventResponse {
  id: number
  event_datetime_utc?: string | null
  event_date_local?: string | null
  event_time_local?: string | null
  display_time?: string | null
  event_key: string
  event_type: string
  category: string
  title: string
  display_name?: string | null
  short_name?: string | null
  source?: string | null
  importance: string
  status: string
  beginner_description?: string | null
  why_it_matters?: string | null
  watch_items?: string[] | null
  related_indicator_key?: string | null
  related_indicator_keys?: string[] | null
  details?: Record<string, unknown> | null
}

interface CalendarEventListResponse {
  events?: CalendarEventResponse[]
  count?: number
}

interface FomcResponse {
  meetings?: {
    id?: number
    date: string
    event_key?: string
    display_name?: string | null
    event_date_local?: string | null
    event_time_local?: string | null
    timezone?: string | null
    rate: number | null
    change_bp: number | null
    details?: Record<string, unknown> | null
  }[]
  fedwatch?: {
    prob_hold: number | null
    prob_cut: number | null
    prob_hike: number | null
    prob_method: string | null
  } | null
}

export function normalizeCalendarEvent(row: CalendarEventResponse): CalendarEvent {
  const related = row.related_indicator_keys ?? (row.related_indicator_key ? [row.related_indicator_key] : [])
  return {
    id: row.id,
    eventKey: row.event_key,
    displayName: row.display_name ?? row.title,
    shortName: row.short_name,
    eventType: row.event_type,
    category: row.category,
    importance: row.importance,
    eventDateTimeUtc: row.event_datetime_utc,
    eventDateLocal: row.event_date_local,
    eventTimeLocal: row.event_time_local,
    displayTime: row.display_time,
    status: row.status,
    source: row.source,
    beginnerDescription: row.beginner_description,
    whyItMatters: row.why_it_matters,
    watchItems: row.watch_items ?? [],
    relatedIndicatorKeys: related,
    details: row.details,
  }
}

function normalizeFomc(row: FomcResponse): FomcOverview {
  return {
    meetings: (row.meetings ?? []).map((meeting) => ({
      id: meeting.id,
      date: meeting.date,
      eventKey: meeting.event_key,
      displayName: meeting.display_name,
      eventDateLocal: meeting.event_date_local,
      eventTimeLocal: meeting.event_time_local,
      timezone: meeting.timezone,
      rate: meeting.rate,
      changeBp: meeting.change_bp,
      details: meeting.details,
    })),
    fedwatch: row.fedwatch
      ? {
          probHold: row.fedwatch.prob_hold,
          probCut: row.fedwatch.prob_cut,
          probHike: row.fedwatch.prob_hike,
          probMethod: row.fedwatch.prob_method,
        }
      : null,
  }
}

export async function getCalendarEvents(days = 30, includeDetails = true): Promise<CalendarEvent[]> {
  const response = await apiGet<CalendarEventListResponse>(
    `/calendar/events?days=${days}&include_details=${includeDetails ? 'true' : 'false'}`
  )
  return (response.events ?? []).map(normalizeCalendarEvent)
}

export async function getFomcOverview(): Promise<FomcOverview> {
  return normalizeFomc(await apiGet<FomcResponse>('/fomc'))
}

