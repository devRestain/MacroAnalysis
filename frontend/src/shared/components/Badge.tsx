import { ReactNode } from 'react'

type Tone = 'neutral' | 'green' | 'yellow' | 'red' | 'blue'

const toneClass: Record<Tone, string> = {
  neutral: 'border-surface-border bg-white text-text-secondary',
  green: 'border-signal-green/20 bg-signal-green/10 text-signal-green',
  yellow: 'border-signal-yellow/20 bg-signal-yellow/10 text-signal-yellow',
  red: 'border-signal-red/20 bg-signal-red/10 text-signal-red',
  blue: 'border-accent/20 bg-accent/10 text-accent',
}

export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: Tone }) {
  return <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-bold tracking-[0.01em] ${toneClass[tone]}`}>{children}</span>
}
