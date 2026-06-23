export interface CalendarEvent {
  id: number | string
  eventKey: string
  displayName: string
  shortName?: string | null
  eventType: string
  eventTypeLabel?: string | null
  category: string
  categoryLabel?: string | null
  importance: 'low' | 'medium' | 'high' | string
  importanceLabel?: string | null
  eventDateTimeUtc?: string | null
  eventDateLocal?: string | null
  eventTimeLocal?: string | null
  displayTime?: string | null
  status?: string | null
  statusLabel?: string | null
  source?: string | null
  sourceLabel?: string | null
  beginnerDescription?: string | null
  whyItMatters?: string | null
  watchItems: string[]
  relatedIndicatorKeys: string[]
  details?: Record<string, unknown> | null
}

export type CalendarTodayBasis = 'market' | 'local'

export interface CalendarMonthTopEvent {
  id: number
  displayName: string
  shortName?: string | null
  importance: 'low' | 'medium' | 'high' | string
  category: string
  eventTimeLocal?: string | null
  displayTime?: string | null
}

export interface CalendarMonthDaySummary {
  date: string
  inMonth: boolean
  isToday: boolean
  isWeekend: boolean
  eventCount: number
  highCount: number
  mediumCount: number
  categories: string[]
  topEvents: CalendarMonthTopEvent[]
}

export interface CalendarMonthRange {
  startDate: string
  endDate: string
  gridStartDate: string
  gridEndDate: string
}

export interface CalendarMonthResponse {
  month: string
  todayBasis: CalendarTodayBasis
  todayDate: string
  range: CalendarMonthRange
  days: CalendarMonthDaySummary[]
}

export interface FomcMeeting {
  id?: number | string
  date: string
  eventKey?: string
  displayName?: string | null
  eventDateLocal?: string | null
  eventTimeLocal?: string | null
  timezone?: string | null
  rate: number | null
  changeBp: number | null
  details?: Record<string, unknown> | null
}

export interface FomcWatch {
  probHold: number | null
  probCut: number | null
  probHike: number | null
  probMethod: string | null
}

export interface FomcOverview {
  meetings: FomcMeeting[]
  fedwatch: FomcWatch | null
}
