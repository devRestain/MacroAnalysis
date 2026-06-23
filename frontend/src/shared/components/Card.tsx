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
    <section className={`min-w-0 overflow-hidden rounded-[18px] border shadow-[0_8px_24px_-24px_rgba(15,23,42,0.22)] ${style.shell} ${className}`}>
      {(title || eyebrow || action) && (
        <div className="flex min-w-0 items-start justify-between gap-3 border-b border-surface-border px-3.5 py-2.5 lg:px-3.5">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${style.accent}`} />
              {eyebrow && <div className={`truncate text-[10px] font-bold uppercase tracking-[0.16em] ${style.text}`}>{eyebrow}</div>}
            </div>
            {title && <h2 className="mt-0.5 truncate text-[15px] font-bold tracking-[-0.02em] text-text-primary lg:text-base">{title}</h2>}
          </div>
          {action}
        </div>
      )}
      <div className="min-w-0 px-3.5 pb-3.5 pt-3 text-safe lg:px-3.5 lg:pb-3.5">{children}</div>
    </section>
  )
}
