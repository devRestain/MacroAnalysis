import { ReactNode } from 'react'
import { getHealth, getSystemAvailability } from '../../shared/api/system'
import { Badge } from '../../shared/components/Badge'
import { Card } from '../../shared/components/Card'
import { DataFreshness } from '../../shared/components/DataFreshness'
import { ErrorState, LoadingState } from '../../shared/components/StateViews'
import { useResource } from '../../shared/hooks/useResource'

export function SystemStatusPage() {
  const health = useResource(() => getHealth(), [], { optional: true })
  const availability = useResource(() => getSystemAvailability(), [], { optional: true })

  return (
    <div className="page-shell animate-fade-up">
      <div className="mb-6">
        <h1 className="text-3xl font-extrabold tracking-[-0.04em]">System</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-text-secondary">Safe frontend-visible status only. Admin operations, migrations, cleanup, and collection controls are intentionally not exposed.</p>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card title="Frontend Runtime" eyebrow="build status" tone="green">
          <div className="space-y-3 text-sm">
            <StatusRow label="Frontend" value={<Badge tone="green">ready</Badge>} />
            <StatusRow label="Mode" value={import.meta.env.MODE} />
            <StatusRow label="API base" value={import.meta.env.VITE_API_URL || '/api'} />
          </div>
        </Card>

        <Card title="API Health" eyebrow="/health" tone="blue">
          {health.state.status === 'success' ? (
            <pre className="overflow-auto text-xs leading-5 text-text-secondary">{JSON.stringify(health.state.data, null, 2)}</pre>
          ) : health.state.status === 'error' || health.state.status === 'disabled' ? <ErrorState label="Health endpoint is unavailable." /> : <LoadingState />}
        </Card>

        <Card title="Capability Availability" eyebrow="inferred from API responses" tone="amber" className="xl:col-span-2">
          {availability.state.status === 'success' ? (
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <div className="text-xs font-bold uppercase tracking-[0.18em] text-text-muted">Dashboard updated</div>
                <div className="mt-2"><DataFreshness updatedAt={availability.state.data.dashboardUpdatedAt} /></div>
              </div>
              <StatusRow label="AI" value={<Badge tone={availability.state.data.aiAvailable ? 'green' : 'yellow'}>{availability.state.data.aiAvailable ? 'available' : 'disabled/unavailable'}</Badge>} />
              <StatusRow label="Sentiment" value={<Badge tone={availability.state.data.sentimentAvailable ? 'green' : 'yellow'}>{availability.state.data.sentimentAvailable ? 'available' : 'disabled/unavailable'}</Badge>} />
            </div>
          ) : availability.state.status === 'error' || availability.state.status === 'disabled' ? <ErrorState label="Could not infer optional API availability." /> : <LoadingState />}
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
