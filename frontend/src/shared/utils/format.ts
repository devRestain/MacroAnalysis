import { getActiveLocale, getIntlLocale } from '../i18n'

export function fmt(value: number | null | undefined, digits = 2, unit = ''): string {
  if (value == null || Number.isNaN(value)) return '-'
  const abs = Math.abs(value)
  const locale = getIntlLocale(getActiveLocale())
  const formatted = abs >= 1000 ? value.toLocaleString(locale, { maximumFractionDigits: digits }) : value.toLocaleString(locale, { minimumFractionDigits: digits, maximumFractionDigits: digits })
  return unit ? `${formatted}${unit}` : formatted
}

export function fmtPct(value: number | null | undefined, digits = 1, mode: 'ratio' | 'percent' = 'percent'): string {
  if (value == null || Number.isNaN(value)) return '-'
  const normalized = mode === 'ratio' ? value * 100 : value
  return `${normalized > 0 ? '+' : ''}${normalized.toFixed(digits)}%`
}

export function fmtDate(value: string | null | undefined): string {
  if (!value) return '-'
  return new Date(value).toLocaleDateString(getIntlLocale(getActiveLocale()), { year: 'numeric', month: 'short', day: 'numeric' })
}

export function fmtDateTime(value: string | null | undefined): string {
  if (!value) return '-'
  return new Date(value).toLocaleString(getIntlLocale(getActiveLocale()), {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function timeAgo(value: string | null | undefined): string {
  if (!value) return ''
  const diff = (Date.now() - new Date(value).getTime()) / 1000
  if (getActiveLocale() === 'en') {
    if (diff < 60) return 'just now'
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
    return `${Math.floor(diff / 86400)}d ago`
  }
  if (diff < 60) return '방금'
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`
  return `${Math.floor(diff / 86400)}일 전`
}

export function compactText(value: string | null | undefined, fallback = getActiveLocale() === 'en' ? 'No context available' : '맥락 정보가 없습니다') {
  return value && value.trim() ? value : fallback
}
