import { AiSummary } from '../../entities/aiSummary/types'
import { useLanguage } from '../i18n'
import { compactText } from '../utils/format'

interface AiSummaryPanelProps {
  summary?: AiSummary | null
  fallbackHeadline?: string | null
  fallbackDate?: string | null
  onOpen: () => void
}

export function AiSummaryPanel({ summary, fallbackHeadline, fallbackDate, onOpen }: AiSummaryPanelProps) {
  const { t } = useLanguage()
  const headline = summary?.headline ?? fallbackHeadline ?? t('dashboard.aiHeadlineEmpty')
  const body = summary?.body ? compactText(summary.body, t('ai.summaryBodyFallback')) : t('dashboard.aiFallbackBody')
  const date = summary?.summaryDate ?? fallbackDate
  const model = summary?.modelUsed ?? t('ai.modelUnavailable')

  return (
    <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
      <div className="min-w-0 flex-1">
        <div className="mb-1 inline-flex items-center rounded-full border border-accent/15 bg-accent/10 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-[0.14em] text-accent">
          {t('dashboard.aiBriefing')}
        </div>
        <h3 className="text-safe line-clamp-2 text-[0.98rem] font-extrabold leading-5 tracking-[-0.04em] text-text-primary lg:text-[1.05rem]">
          {headline}
        </h3>
        <p className="mt-1 line-clamp-2 text-[11px] leading-4 text-text-secondary">
          {body}
        </p>
      </div>
      <div className="flex shrink-0 flex-wrap items-center gap-2 lg:justify-end">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-text-muted">
          <span>{date ?? '-'}</span>
          <span>{model}</span>
        </div>
        <button onClick={onOpen} className="inline-flex rounded-full bg-accent px-3 py-1.5 text-[12px] font-bold text-white">
          {t('dashboard.openDrawer')}
        </button>
        <a href="/ai" className="inline-flex rounded-full border border-surface-border bg-white px-3 py-1.5 text-[12px] font-bold text-text-secondary">
          {t('dashboard.openBriefings')}
        </a>
      </div>
    </div>
  )
}
