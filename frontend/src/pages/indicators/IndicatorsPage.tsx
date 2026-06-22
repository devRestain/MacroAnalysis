import { ReactNode } from 'react'
import { getDashboardSummary } from '../../shared/api/dashboard'
import { getIndicatorExplanations } from '../../shared/api/indicators'
import { Badge } from '../../shared/components/Badge'
import { Card } from '../../shared/components/Card'
import { useLanguage } from '../../shared/i18n'
import { EmptyState, ErrorState, LoadingState } from '../../shared/components/StateViews'
import { useResource } from '../../shared/hooks/useResource'
import { fmt, fmtPct } from '../../shared/utils/format'

export function IndicatorsPage() {
  const { locale, t, label } = useLanguage()
  const summary = useResource(() => getDashboardSummary(), [locale])
  const explanations = useResource(() => getIndicatorExplanations(), [locale], { optional: true })

  if (summary.state.status === 'loading' || summary.state.status === 'idle') return <Frame><LoadingState /></Frame>
  if (summary.state.status === 'error' || summary.state.status === 'disabled') return <Frame><ErrorState label={t('indicators.snapshotsUnavailable')} /></Frame>
  if (summary.state.status === 'empty') return <Frame><EmptyState /></Frame>

  const rows = Object.values(summary.state.data.snapshots)
  const categories = Array.from(new Set(rows.map((row) => row.category))).sort()
  const explanationMap = new Map(
    explanations.state.status === 'success'
      ? explanations.state.data.map((item) => [item.indicatorKey, item])
      : []
  )

  return (
    <Frame>
      <div className="mb-6">
        <h1 className="text-3xl font-extrabold tracking-[-0.04em]">{t('indicators.title')}</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-text-secondary">{t('indicators.description')}</p>
      </div>
      <div className="space-y-5">
        {categories.map((category) => (
          <Card key={category} title={label('category', category, category)} eyebrow={t('indicators.categoryEyebrow')} tone="blue">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-xs font-bold uppercase tracking-[0.16em] text-text-muted">
                  <tr className="border-b border-surface-border">
                    <th className="py-2 text-left font-medium">{t('indicators.column.indicator')}</th>
                    <th className="py-2 text-right font-medium">{t('indicators.column.latest')}</th>
                    <th className="py-2 text-right font-medium">{t('indicators.column.1m')}</th>
                    <th className="py-2 text-right font-medium">{t('indicators.column.signal')}</th>
                    <th className="py-2 text-left font-medium">{t('indicators.column.context')}</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.filter((row) => row.category === category).map((row) => {
                    const explanation = explanationMap.get(row.key)
                    return (
                      <tr key={row.key} className="border-b border-surface-border/70 last:border-0 hover:bg-white/50">
                        <td className="py-4">
                          <a href={`/indicators/${encodeURIComponent(row.key)}`} className="font-bold text-text-primary hover:text-accent">{row.label}</a>
                          <div className="font-mono text-xs text-text-muted">{row.key}</div>
                        </td>
                        <td className="py-4 text-right font-mono text-base">{fmt(row.value, 2, row.unit ?? '')}</td>
                        <td className={`py-4 text-right font-mono font-semibold ${row.delta1mPct && row.delta1mPct < 0 ? 'text-signal-red' : 'text-signal-green'}`}>{fmtPct(row.delta1mPct)}</td>
                        <td className="py-4 text-right"><Badge tone={row.signal === 'red' ? 'red' : row.signal === 'yellow' ? 'yellow' : 'green'}>{label('signal', row.signal, row.signal)}</Badge></td>
                        <td className="max-w-sm py-4 text-xs leading-6 text-text-secondary">{explanation?.description ?? t('indicators.explanationMissing')}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        ))}
      </div>
    </Frame>
  )
}

function Frame({ children }: { children: ReactNode }) {
  return <div className="page-shell animate-fade-up">{children}</div>
}
