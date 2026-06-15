import { Clock } from 'lucide-react'
import { fmtDateTime } from '../utils/format'

export function DataFreshness({ updatedAt }: { updatedAt?: string | null }) {
  return (
    <div className="inline-flex items-center gap-1 text-xs text-text-muted">
      <Clock size={12} />
      <span>Update time {fmtDateTime(updatedAt)}</span>
    </div>
  )
}

