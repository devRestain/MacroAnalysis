import { ReactNode } from 'react'

interface CardProps {
  title?: string
  eyebrow?: string
  action?: ReactNode
  children: ReactNode
  className?: string
  tone?: 'default' | 'blue' | 'amber' | 'green' | 'rose'
}

const toneStyles = {
  default: {
    shell: 'border-surface-border bg-white',
    accent: 'bg-[#cfd8e3]',
    text: 'text-text-secondary',
  },
  blue: {
    shell: 'border-surface-border bg-white',
    accent: 'bg-[#2457d6]',
    text: 'text-accent',
  },
  amber: {
    shell: 'border-surface-border bg-white',
    accent: 'bg-[#b7791f]',
    text: 'text-[#8e6419]',
  },
  green: {
    shell: 'border-surface-border bg-white',
    accent: 'bg-[#158a5c]',
    text: 'text-signal-green',
  },
  rose: {
    shell: 'border-surface-border bg-white',
    accent: 'bg-[#d14343]',
    text: 'text-signal-red',
  },
}

export function Card({ title, eyebrow, action, children, className = '', tone = 'default' }: CardProps) {
  const style = toneStyles[tone]
  return (
    <section className={`min-w-0 overflow-hidden rounded-[22px] border shadow-[0_12px_30px_-24px_rgba(20,34,56,0.18)] ${style.shell} ${className}`}>
      <div className={`entity-strip mx-5 mt-4 ${style.accent}`} />
      {(title || eyebrow || action) && (
        <div className="flex min-w-0 items-start justify-between gap-4 border-b border-surface-border px-5 py-4">
          <div className="min-w-0">
            {eyebrow && <div className={`truncate text-[11px] font-bold uppercase tracking-[0.18em] ${style.text}`}>{eyebrow}</div>}
            {title && <h2 className="mt-1 truncate text-lg font-bold tracking-[-0.02em] text-text-primary">{title}</h2>}
          </div>
          {action}
        </div>
      )}
      <div className="min-w-0 p-5 text-safe">{children}</div>
    </section>
  )
}
