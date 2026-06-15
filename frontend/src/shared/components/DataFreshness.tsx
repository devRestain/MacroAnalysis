import { Clock } from 'lucide-react'
import { fmtDateTime } from '../utils/format'

export function DataFreshness({ updatedAt }: { updatedAt?: string | null }) {
  return (
    <div className="inline-flex items-center gap-1 rounded-full border border-surface-border bg-white px-3 py-1.5 text-xs font-medium text-text-secondary">
      <Clock size={12} />
      <span>Update time {fmtDateTime(updatedAt)}</span>
    </div>
  )
}
