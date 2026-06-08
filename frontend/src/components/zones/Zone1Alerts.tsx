import { Snapshot } from '../../lib/api'
import { signalColor, signalBg, fmt, fmtPct, zScoreLabel, clsx } from '../../lib/utils'
import { AlertTriangle, TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface Props {
  alerts: Snapshot[]
  onSelect: (key: string) => void
}

export function Zone1Alerts({ alerts, onSelect }: Props) {
  if (alerts.length === 0) return null

  return (
    <section className="px-4 py-3 border-b border-surface-border">
      <div className="flex items-center gap-2 mb-2">
        <AlertTriangle size={14} className="text-signal-yellow" />
        <span className="text-xs font-semibold text-text-secondary uppercase tracking-widest">
          주목할 이상 신호
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        {alerts.map((s) => (
          <button
            key={s.key}
            onClick={() => onSelect(s.key)}
            className={clsx(
              'flex items-center gap-2 px-3 py-1.5 rounded-md border text-sm',
              'transition-all hover:brightness-110 cursor-pointer',
              signalBg(s.signal)
            )}
          >
            <DirectionIcon dir={s.direction} signal={s.signal} />
            <span className="text-text-primary font-medium">{s.label}</span>
            <span className={clsx('text-xs font-mono', signalColor(s.signal))}>
              {s.delta_1d_pct != null ? fmtPct(s.delta_1d_pct) : fmt(s.value, 2, s.unit || '')}
            </span>
            {s.z_score_1y != null && Math.abs(s.z_score_1y) >= 1.5 && (
              <span className="text-xs text-text-secondary">
                Z:{s.z_score_1y > 0 ? '+' : ''}{s.z_score_1y.toFixed(1)} ({zScoreLabel(s.z_score_1y)})
              </span>
            )}
          </button>
        ))}
      </div>
    </section>
  )
}

function DirectionIcon({ dir, signal }: { dir: string; signal: string }) {
  const cls = `w-3.5 h-3.5 ${signalColor(signal)}`
  if (dir === 'up') return <TrendingUp className={cls} />
  if (dir === 'down') return <TrendingDown className={cls} />
  return <Minus className={cls} />
}
