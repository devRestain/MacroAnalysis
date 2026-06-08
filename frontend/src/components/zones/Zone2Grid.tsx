import { SummaryResponse, Snapshot } from '../../lib/api'
import { fmt, fmtPct, directionArrow, directionColor, signalColor, clsx } from '../../lib/utils'

const KEY_CARDS = [
  { key: 'DFF', label: '기준금리', unit: '%' },
  { key: 'DX-Y.NYB', label: 'DXY', unit: '' },
  { key: '^VIX', label: 'VIX', unit: '' },
  { key: 'DGS10', label: '10Y 국채', unit: '%' },
  { key: 'USDKRW', label: 'USD/KRW', unit: '' },
  { key: 'HY_OAS', label: 'HY 스프레드', unit: 'bp' },
  { key: 'CL=F', label: 'WTI 원유', unit: '' },
  { key: 'COPPER_GOLD', label: '구리/금 비율', unit: '' },
]

interface Props {
  snapshots: Record<string, Snapshot>
  equities: SummaryResponse['equities']
  onSelect: (key: string) => void
}

export function Zone2Grid({ snapshots, equities, onSelect }: Props) {
  return (
    <section className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-px bg-surface-border border-b border-surface-border">
      {KEY_CARDS.map(({ key, label, unit }) => {
        const snap = snapshots[key]
        const equity = equities[key]
        const value = snap?.value ?? (equity?.close ?? null)
        const delta1d = snap?.delta_1d_pct ?? (equity ? equity.change_pct : null)
        const delta1w = snap?.delta_1w_pct ?? null
        const signal = snap?.signal ?? 'green'
        const direction = snap?.direction ?? (delta1d == null ? 'flat' : delta1d > 0.1 ? 'up' : delta1d < -0.1 ? 'down' : 'flat')

        return (
          <button
            key={key}
            onClick={() => onSelect(key)}
            className="bg-surface-card hover:bg-surface-hover transition-colors p-3 text-left group"
          >
            <div className="text-xs text-text-secondary mb-1 group-hover:text-text-primary transition-colors">
              {label}
            </div>
            <div className="font-mono text-base font-semibold text-text-primary mb-1">
              {value != null ? fmt(value, 2, '') : '—'}
              {unit && value != null && (
                <span className="text-xs text-text-secondary ml-0.5">{unit}</span>
              )}
            </div>
            <div className="flex gap-2 text-xs font-mono">
              <span className={directionColor(direction)}>
                {directionArrow(direction)}{' '}
                {delta1d != null ? fmtPct(delta1d) : '—'}
              </span>
              {delta1w != null && (
                <span className="text-text-muted">
                  1W {fmtPct(delta1w)}
                </span>
              )}
            </div>
            {snap?.z_score_1y != null && Math.abs(snap.z_score_1y) >= 1.0 && (
              <div className={clsx('text-xs mt-1 font-mono', signalColor(signal))}>
                Z:{snap.z_score_1y > 0 ? '+' : ''}{snap.z_score_1y.toFixed(1)}
              </div>
            )}
          </button>
        )
      })}
    </section>
  )
}
