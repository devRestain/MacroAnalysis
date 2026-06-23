import { ReactNode } from 'react'
import { getHealth, getSystemAvailability, getSystemOverview } from '../../shared/api/system'
import { Badge } from '../../shared/components/Badge'
import { Card } from '../../shared/components/Card'
import { DataFreshness } from '../../shared/components/DataFreshness'
import { useLanguage } from '../../shared/i18n'
import { fmtPct } from '../../shared/utils/format'
import { ErrorState, LoadingState } from '../../shared/components/StateViews'
import { useResource } from '../../shared/hooks/useResource'

export function SystemStatusPage() {
  const { t } = useLanguage()
  const health = useResource(() => getHealth(), [], { optional: true })
  const availability = useResource(() => getSystemAvailability(), [], { optional: true })
  const overview = useResource(() => getSystemOverview(), [], { optional: true })

  return (
    <div className="page-shell animate-fade-up">
      <div className="grid gap-4 xl:grid-cols-2">
        <Card title={t('system.card.dashboardMeta')} eyebrow={t('system.card.dashboardMetaEyebrow')} tone="blue" className="xl:col-span-2">
          {overview.state.status === 'success' ? (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-3">
                <DataFreshness updatedAt={overview.state.data.dashboardUpdatedAt} />
                {overview.state.data.aiBriefingDate && <Badge>{t('dashboard.aiBriefing')} {overview.state.data.aiBriefingDate}</Badge>}
              </div>
              <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-6">
                <MetricChip label={t('dashboard.metric.trackedSignals')} value={overview.state.data.trackedSignals ?? '-'} />
                <MetricChip label={t('dashboard.metric.upcomingEvents')} value={overview.state.data.upcomingEvents ?? '-'} />
                <MetricChip label={t('dashboard.metric.newsItems')} value={overview.state.data.newsItems ?? '-'} />
                <MetricChip label="FOMC" value={overview.state.data.fomcDaysLeft != null ? `D-${overview.state.data.fomcDaysLeft}` : '-'} />
                <MetricChip label={t('calendar.prob.hold')} value={overview.state.data.probHold != null ? fmtPct(overview.state.data.probHold, 0, 'ratio') : '-'} />
                <MetricChip label={t('dashboard.aiBriefing')} value={overview.state.data.aiBriefingDate ?? '-'} compact />
              </div>
            </div>
          ) : overview.state.status === 'error' || overview.state.status === 'disabled' ? <ErrorState label={t('system.capabilityUnavailable')} /> : <LoadingState />}
        </Card>

        <Card title={t('system.card.runtime')} eyebrow={t('system.card.runtimeEyebrow')} tone="green">
          <div className="space-y-3 text-sm">
            <StatusRow label={t('system.frontend')} value={<Badge tone="green">{t('system.ready')}</Badge>} />
            <StatusRow label={t('system.mode')} value={import.meta.env.MODE} />
            <StatusRow label={t('system.apiBase')} value={import.meta.env.VITE_API_URL || '/api'} />
          </div>
        </Card>

        <Card title={t('system.card.health')} eyebrow={t('system.card.healthEyebrow')} tone="blue">
          {health.state.status === 'success' ? (
            <pre className="overflow-auto text-xs leading-5 text-text-secondary">{JSON.stringify(health.state.data, null, 2)}</pre>
          ) : health.state.status === 'error' || health.state.status === 'disabled' ? <ErrorState label={t('system.healthUnavailable')} /> : <LoadingState />}
        </Card>

        <Card title={t('system.card.capabilities')} eyebrow={t('system.card.capabilitiesEyebrow')} tone="amber" className="xl:col-span-2">
          {availability.state.status === 'success' ? (
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <div className="text-xs font-bold uppercase tracking-[0.18em] text-text-muted">{t('system.dashboardUpdated')}</div>
                <div className="mt-2"><DataFreshness updatedAt={availability.state.data.dashboardUpdatedAt} /></div>
              </div>
              <StatusRow label={t('system.ai')} value={<Badge tone={availability.state.data.aiAvailable ? 'green' : 'yellow'}>{availability.state.data.aiAvailable ? t('system.available') : t('system.disabledUnavailable')}</Badge>} />
              <StatusRow label={t('system.sentiment')} value={<Badge tone={availability.state.data.sentimentAvailable ? 'green' : 'yellow'}>{availability.state.data.sentimentAvailable ? t('system.available') : t('system.disabledUnavailable')}</Badge>} />
            </div>
          ) : availability.state.status === 'error' || availability.state.status === 'disabled' ? <ErrorState label={t('system.capabilityUnavailable')} /> : <LoadingState />}
        </Card>
      </div>
    </div>
  )
}

function StatusRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-[18px] border border-surface-border/75 bg-white/78 px-4 py-3 last:border-surface-border/75">
      <span className="font-semibold text-text-secondary">{label}</span>
      <span className="text-right font-mono text-xs">{value}</span>
    </div>
  )
}

function MetricChip({ label, value, compact = false }: { label: string; value: number | string; compact?: boolean }) {
  return (
    <div className="rounded-[16px] border border-surface-border bg-white px-3.5 py-3">
      <div className="text-[11px] font-bold uppercase tracking-[0.16em] text-text-muted">{label}</div>
      <div className={`mt-1.5 font-mono font-semibold tracking-[-0.04em] text-text-primary ${compact ? 'text-sm lg:text-base' : 'text-xl lg:text-2xl'}`}>{value}</div>
    </div>
  )
}
