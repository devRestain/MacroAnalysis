import { ReactNode } from 'react'

interface CardProps {
  title?: string
  eyebrow?: string
  action?: ReactNode
  children: ReactNode
  className?: string
}

export function Card({ title, eyebrow, action, children, className = '' }: CardProps) {
  return (
    <section className={`border border-surface-border bg-surface-card ${className}`}>
      {(title || eyebrow || action) && (
        <div className="flex items-start justify-between gap-4 border-b border-surface-border px-4 py-3">
          <div>
            {eyebrow && <div className="text-[11px] font-semibold uppercase tracking-widest text-text-muted">{eyebrow}</div>}
            {title && <h2 className="mt-1 text-sm font-semibold text-text-primary">{title}</h2>}
          </div>
          {action}
        </div>
      )}
      <div className="p-4">{children}</div>
    </section>
  )
}

