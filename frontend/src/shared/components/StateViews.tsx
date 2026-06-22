import { AlertCircle, Ban, CircleDashed, Loader2 } from 'lucide-react'
import { useLanguage } from '../i18n'

export function LoadingState({ label = 'Loading latest collected data...' }: { label?: string }) {
  const { t } = useLanguage()
  return (
    <div className="flex min-h-36 flex-col items-center justify-center gap-3 rounded-[24px] border border-dashed border-surface-border bg-white/70 px-4 py-10 text-center text-sm text-text-secondary">
      <Loader2 size={18} className="animate-spin text-accent" />
      {label === 'Loading latest collected data...' ? t('state.loading') : label}
    </div>
  )
}

export function EmptyState({ label = 'No collected data available yet.' }: { label?: string }) {
  const { t } = useLanguage()
  return (
    <div className="flex min-h-36 flex-col items-center justify-center gap-3 rounded-[24px] border border-dashed border-surface-border bg-white/70 px-4 py-10 text-center text-sm text-text-muted">
      <CircleDashed size={16} />
      {label === 'No collected data available yet.' ? t('state.empty') : label}
    </div>
  )
}

export function ErrorState({ label = 'Unable to load this panel.' }: { label?: string }) {
  const { t } = useLanguage()
  return (
    <div className="flex min-h-36 flex-col items-center justify-center gap-3 rounded-[24px] border border-signal-red/15 bg-signal-red/5 px-4 py-10 text-center text-sm text-signal-red">
      <AlertCircle size={16} />
      {label === 'Unable to load this panel.' ? t('state.error') : label}
    </div>
  )
}

export function DisabledState({ label = 'This capability is not enabled in the current pipeline.' }: { label?: string }) {
  const { t } = useLanguage()
  return (
    <div className="flex min-h-36 flex-col items-center justify-center gap-3 rounded-[24px] border border-dashed border-surface-border bg-white/70 px-4 py-10 text-center text-sm text-text-muted">
      <Ban size={16} />
      {label === 'This capability is not enabled in the current pipeline.' ? t('state.disabled') : label}
    </div>
  )
}
