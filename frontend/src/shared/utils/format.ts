export function fmt(value: number | null | undefined, digits = 2, unit = ''): string {
  if (value == null || Number.isNaN(value)) return '-'
  const abs = Math.abs(value)
  const formatted = abs >= 1000 ? value.toLocaleString('en-US', { maximumFractionDigits: digits }) : value.toFixed(digits)
  return unit ? `${formatted}${unit}` : formatted
}

export function fmtPct(value: number | null | undefined, digits = 1, mode: 'ratio' | 'percent' = 'percent'): string {
  if (value == null || Number.isNaN(value)) return '-'
  const normalized = mode === 'ratio' ? value * 100 : value
  return `${normalized > 0 ? '+' : ''}${normalized.toFixed(digits)}%`
}

export function fmtDate(value: string | null | undefined): string {
  if (!value) return '-'
  return new Date(value).toLocaleDateString('ko-KR', { year: 'numeric', month: 'short', day: 'numeric' })
}

export function fmtDateTime(value: string | null | undefined): string {
  if (!value) return '-'
  return new Date(value).toLocaleString('ko-KR', {
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
  if (diff < 60) return '방금'
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`
  return `${Math.floor(diff / 86400)}일 전`
}

export function compactText(value: string | null | undefined, fallback = 'No context available') {
  return value && value.trim() ? value : fallback
}

