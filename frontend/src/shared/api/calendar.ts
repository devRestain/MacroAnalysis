import {
  CalendarEvent,
  CalendarMonthResponse,
  CalendarMonthTopEvent,
  CalendarTodayBasis,
  FomcOverview,
} from '../../entities/calendarEvent/types'
import { apiGet } from './client'

interface CalendarEventResponse {
  id: number
  event_datetime_utc?: string | null
  event_date_local?: string | null
  event_time_local?: string | null
  display_time?: string | null
  event_key: string
  event_type: string
  event_type_label?: string | null
  category: string
  category_label?: string | null
  title: string
  display_name?: string | null
  short_name?: string | null
  source?: string | null
  importance: string
  importance_label?: string | null
  status: string
  status_label?: string | null
  beginner_description?: string | null
  why_it_matters?: string | null
  watch_items?: string[] | null
  source_label?: string | null
  related_indicator_key?: string | null
  related_indicator_keys?: string[] | null
  details?: Record<string, unknown> | null
}

interface CalendarEventListResponse {
  events?: CalendarEventResponse[]
  count?: number
}

interface CalendarMonthTopEventResponse {
  id: number
  display_name: string
  short_name?: string | null
  importance: string
  category: string
  event_time_local?: string | null
  display_time?: string | null
}

interface CalendarMonthDaySummaryResponse {
  date: string
  in_month: boolean
  is_today: boolean
  is_weekend: boolean
  event_count: number
  high_count: number
  medium_count: number
  categories: string[]
  top_events: CalendarMonthTopEventResponse[]
}

interface CalendarMonthResponseBody {
  month: string
  today_basis: CalendarTodayBasis
  today_date: string
  range: {
    start_date: string
    end_date: string
    grid_start_date: string
    grid_end_date: string
  }
  days: CalendarMonthDaySummaryResponse[]
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
    eventTypeLabel: row.event_type_label,
    category: row.category,
    categoryLabel: row.category_label,
    importance: row.importance,
    importanceLabel: row.importance_label,
    eventDateTimeUtc: row.event_datetime_utc,
    eventDateLocal: row.event_date_local,
    eventTimeLocal: row.event_time_local,
    displayTime: row.display_time,
    status: row.status,
    statusLabel: row.status_label,
    source: row.source,
    sourceLabel: row.source_label,
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

function normalizeMonthTopEvent(row: CalendarMonthTopEventResponse): CalendarMonthTopEvent {
  return {
    id: row.id,
    displayName: row.display_name,
    shortName: row.short_name,
    importance: row.importance,
    category: row.category,
    eventTimeLocal: row.event_time_local,
    displayTime: row.display_time,
  }
}

function normalizeCalendarMonth(row: CalendarMonthResponseBody): CalendarMonthResponse {
  return {
    month: row.month,
    todayBasis: row.today_basis,
    todayDate: row.today_date,
    range: {
      startDate: row.range.start_date,
      endDate: row.range.end_date,
      gridStartDate: row.range.grid_start_date,
      gridEndDate: row.range.grid_end_date,
    },
    days: row.days.map((day) => ({
      date: day.date,
      inMonth: day.in_month,
      isToday: day.is_today,
      isWeekend: day.is_weekend,
      eventCount: day.event_count,
      highCount: day.high_count,
      mediumCount: day.medium_count,
      categories: day.categories ?? [],
      topEvents: (day.top_events ?? []).map(normalizeMonthTopEvent),
    })),
  }
}

function buildQuery(params: Record<string, string | number | boolean | undefined | null>): string {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    search.set(key, String(value))
  })
  const query = search.toString()
  return query ? `?${query}` : ''
}

export interface CalendarEventQuery {
  from?: string
  to?: string
  days?: number
  includeDetails?: boolean
  importance?: string
  category?: string
  country?: string
}

export interface CalendarMonthQuery {
  month: string
  importance?: string
  category?: string
  country?: string
  todayBasis?: CalendarTodayBasis
  todayTz?: string
}

export async function getCalendarEvents(options: number | CalendarEventQuery = 30, includeDetails = true): Promise<CalendarEvent[]> {
  const query = typeof options === 'number'
    ? buildQuery({ days: options, include_details: includeDetails })
    : buildQuery({
        from: options.from,
        to: options.to,
        days: options.days ?? 30,
        include_details: options.includeDetails ?? true,
        importance: options.importance,
        category: options.category,
        country: options.country,
      })
  const response = await apiGet<CalendarEventListResponse>(`/calendar/events${query}`)
  return (response.events ?? []).map(normalizeCalendarEvent)
}

export async function getCalendarMonth(options: CalendarMonthQuery): Promise<CalendarMonthResponse> {
  const response = await apiGet<CalendarMonthResponseBody>(
    `/calendar/month${buildQuery({
      month: options.month,
      importance: options.importance,
      category: options.category,
      country: options.country,
      today_basis: options.todayBasis ?? 'market',
      today_tz: options.todayTz,
    })}`
  )
  return normalizeCalendarMonth(response)
}

export async function getFomcOverview(): Promise<FomcOverview> {
  return normalizeFomc(await apiGet<FomcResponse>('/fomc'))
}
