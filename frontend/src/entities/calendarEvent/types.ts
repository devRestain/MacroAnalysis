export interface CalendarEvent {
  id: number | string
  eventKey: string
  displayName: string
  shortName?: string | null
  eventType: string
  category: string
  importance: 'low' | 'medium' | 'high' | string
  eventDateTimeUtc?: string | null
  eventDateLocal?: string | null
  eventTimeLocal?: string | null
  displayTime?: string | null
  status?: string | null
  source?: string | null
  beginnerDescription?: string | null
  whyItMatters?: string | null
  watchItems: string[]
  relatedIndicatorKeys: string[]
  details?: Record<string, unknown> | null
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

