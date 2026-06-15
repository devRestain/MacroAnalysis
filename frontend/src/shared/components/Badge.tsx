import { ReactNode } from 'react'

type Tone = 'neutral' | 'green' | 'yellow' | 'red' | 'blue'

const toneClass: Record<Tone, string> = {
  neutral: 'border-surface-border bg-surface-hover text-text-secondary',
  green: 'border-signal-green/30 bg-signal-green/10 text-signal-green',
  yellow: 'border-signal-yellow/30 bg-signal-yellow/10 text-signal-yellow',
  red: 'border-signal-red/30 bg-signal-red/10 text-signal-red',
  blue: 'border-accent/30 bg-accent/10 text-accent',
}

export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: Tone }) {
  return <span className={`inline-flex items-center border px-2 py-0.5 text-[11px] font-medium ${toneClass[tone]}`}>{children}</span>
}

