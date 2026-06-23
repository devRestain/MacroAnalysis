import { ReactNode, useEffect, useRef } from 'react'
import { X } from 'lucide-react'

interface InsightDrawerProps {
  open: boolean
  onClose: () => void
  title: string
  subtitle?: string
  children: ReactNode
}

export function InsightDrawer({ open, onClose, title, subtitle, children }: InsightDrawerProps) {
  const closeButtonRef = useRef<HTMLButtonElement | null>(null)

  useEffect(() => {
    if (!open) return undefined
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    window.setTimeout(() => closeButtonRef.current?.focus(), 0)
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50">
      <button
        aria-label="Close dialog"
        className="absolute inset-0 bg-slate-950/30 backdrop-blur-[2px]"
        onClick={onClose}
      />
      <div className="absolute inset-x-0 bottom-0 top-auto mx-auto flex max-h-[88vh] w-full max-w-[960px] flex-col overflow-hidden rounded-t-[28px] border border-surface-border bg-white shadow-[0_-12px_48px_-24px_rgba(15,23,42,0.28)] md:inset-y-6 md:right-6 md:left-auto md:top-6 md:mx-0 md:max-h-[calc(100vh-48px)] md:rounded-[28px]">
        <div className="flex items-start justify-between gap-4 border-b border-surface-border px-5 py-4 md:px-6">
          <div className="min-w-0">
            <h2 className="text-xl font-extrabold tracking-[-0.03em] text-text-primary">{title}</h2>
            {subtitle && <p className="mt-1 text-sm text-text-secondary">{subtitle}</p>}
          </div>
          <button
            ref={closeButtonRef}
            onClick={onClose}
            className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-surface-border bg-white text-text-secondary hover:text-text-primary"
          >
            <X size={18} />
          </button>
        </div>
        <div role="dialog" aria-modal="true" className="min-h-0 flex-1 overflow-y-auto px-5 py-5 md:px-6">
          {children}
        </div>
      </div>
    </div>
  )
}
