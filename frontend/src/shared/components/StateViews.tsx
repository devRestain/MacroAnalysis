import { AlertCircle, Ban, CircleDashed, Loader2 } from 'lucide-react'

export function LoadingState({ label = 'Loading latest collected data...' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-10 text-sm text-text-secondary">
      <Loader2 size={16} className="animate-spin text-accent" />
      {label}
    </div>
  )
}

export function EmptyState({ label = 'No collected data available yet.' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-10 text-sm text-text-muted">
      <CircleDashed size={16} />
      {label}
    </div>
  )
}

export function ErrorState({ label = 'Unable to load this panel.' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-10 text-sm text-signal-red">
      <AlertCircle size={16} />
      {label}
    </div>
  )
}

export function DisabledState({ label = 'This capability is not enabled in the current pipeline.' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-10 text-sm text-text-muted">
      <Ban size={16} />
      {label}
    </div>
  )
}

