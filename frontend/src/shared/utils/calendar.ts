import { CalendarMonthResponse } from '../../entities/calendarEvent/types'
import { getActiveLocale, getIntlLocale } from '../i18n'

export function toMonthKey(value: Date): string {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  return `${year}-${month}`
}

export function shiftMonthKey(monthKey: string, delta: number): string {
  const [year, month] = monthKey.split('-').map(Number)
  const next = new Date(year, month - 1 + delta, 1)
  return toMonthKey(next)
}

export function formatMonthLabel(monthKey: string): string {
  const [year, month] = monthKey.split('-').map(Number)
  return new Intl.DateTimeFormat(getIntlLocale(getActiveLocale()), {
    year: 'numeric',
    month: 'long',
  }).format(new Date(year, month - 1, 1))
}

export function weekdayLabels(): string[] {
  const formatter = new Intl.DateTimeFormat(getIntlLocale(getActiveLocale()), { weekday: 'short' })
  const start = new Date(Date.UTC(2026, 5, 7))
  return Array.from({ length: 7 }, (_, index) => {
    const value = new Date(start)
    value.setUTCDate(start.getUTCDate() + index)
    return formatter.format(value)
  })
}

export function dayNumber(value: string): string {
  return String(new Date(`${value}T00:00:00`).getDate())
}

export function selectDefaultCalendarDate(month: CalendarMonthResponse): string {
  const today = month.days.find((day) => day.isToday && day.eventCount > 0)
  if (today) return today.date
  const future = month.days.find((day) => day.inMonth && day.date >= month.todayDate && day.eventCount > 0)
  if (future) return future.date
  const firstWithEvents = month.days.find((day) => day.inMonth && day.eventCount > 0)
  return firstWithEvents?.date ?? month.todayDate
}
