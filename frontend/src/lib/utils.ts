export function fmt(value: number | null | undefined, digits = 2, unit = ''): string {
  if (value == null) return '—'
  const abs = Math.abs(value)
  let formatted: string
  if (abs >= 1000000) {
    formatted = (value / 1000000).toFixed(1) + 'M'
  } else if (abs >= 1000) {
    formatted = value.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  } else {
    formatted = value.toFixed(digits)
  }
  return unit ? `${formatted}${unit}` : formatted
}

export function fmtPct(v: number | null | undefined, digits = 1): string {
  if (v == null) return '—'
  return `${v > 0 ? '+' : ''}${v.toFixed(digits)}%`
}

export function fmtDelta(v: number | null | undefined, unit = '', digits = 2): string {
  if (v == null) return '—'
  return `${v > 0 ? '+' : ''}${v.toFixed(digits)}${unit}`
}

export function signalColor(signal: string): string {
  if (signal === 'red') return 'text-signal-red'
  if (signal === 'yellow') return 'text-signal-yellow'
  return 'text-signal-green'
}

export function signalBg(signal: string): string {
  if (signal === 'red') return 'bg-signal-red/10 border-signal-red/30'
  if (signal === 'yellow') return 'bg-signal-yellow/10 border-signal-yellow/30'
  return 'bg-signal-green/10 border-signal-green/30'
}

export function directionArrow(dir: string): string {
  if (dir === 'up') return '▲'
  if (dir === 'down') return '▼'
  return '─'
}

export function directionColor(dir: string): string {
  if (dir === 'up') return 'text-signal-green'
  if (dir === 'down') return 'text-signal-red'
  return 'text-text-muted'
}

export function timeAgo(dateStr: string | null): string {
  if (!dateStr) return ''
  const diff = (Date.now() - new Date(dateStr).getTime()) / 1000
  if (diff < 60) return '방금'
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`
  return `${Math.floor(diff / 86400)}일 전`
}

export function zScoreLabel(z: number | null): string {
  if (z == null) return ''
  if (Math.abs(z) >= 2) return '극단'
  if (Math.abs(z) >= 1.5) return '이상'
  if (Math.abs(z) >= 1) return '주의'
  return '정상'
}

export function clsx(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ')
}
