import { useState } from 'react'
import { Snapshot } from '../../lib/api'
import { fmt, fmtPct, signalColor, directionArrow, directionColor, clsx } from '../../lib/utils'

const CATEGORY_LABELS: Record<string, string> = {
  rates: '금리',
  macro: '거시경제',
  credit: '크레딧',
  equity: '주식',
  fx: '환율',
  real: '실물경제',
  sentiment: '심리',
}

interface Props {
  changes: Snapshot[]
  onSelect: (key: string) => void
}

export function Zone4Heatmap({ changes, onSelect }: Props) {
  const [activeCategory, setActiveCategory] = useState<string>('all')

  const categories = ['all', ...Array.from(new Set(changes.map((c) => c.category)))]
  const filtered = activeCategory === 'all' ? changes : changes.filter((c) => c.category === activeCategory)

  return (
    <section className="border-b border-surface-border">
      {/* Category tabs */}
      <div className="flex items-center gap-1 px-4 py-2 border-b border-surface-border overflow-x-auto">
        <span className="text-xs text-text-secondary mr-2 flex-shrink-0">전체 지표 변화량</span>
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={clsx(
              'text-xs px-2.5 py-1 rounded flex-shrink-0 transition-colors',
              activeCategory === cat
                ? 'bg-accent/20 text-accent'
                : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover'
            )}
          >
            {cat === 'all' ? '전체' : CATEGORY_LABELS[cat] || cat}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-surface-border">
              {['지표', '현재값', '1D', '1W', '1M', '3M', 'Z-score', '신호'].map((h) => (
                <th key={h} className="px-3 py-2 text-left font-medium text-text-muted whitespace-nowrap">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((snap) => (
              <tr
                key={snap.key}
                onClick={() => onSelect(snap.key)}
                className="border-b border-surface-border/50 hover:bg-surface-hover cursor-pointer transition-colors"
              >
                <td className="px-3 py-2 font-medium text-text-primary whitespace-nowrap">
                  {snap.label}
                </td>
                <td className="px-3 py-2 font-mono text-text-primary whitespace-nowrap">
                  {fmt(snap.value, 2)}{snap.unit && <span className="text-text-muted ml-0.5">{snap.unit}</span>}
                </td>
                <td className={clsx('px-3 py-2 font-mono whitespace-nowrap', directionColor(snap.direction))}>
                  {directionArrow(snap.direction)} {snap.delta_1d_pct != null ? fmtPct(snap.delta_1d_pct) : '—'}
                </td>
                <td className={clsx('px-3 py-2 font-mono whitespace-nowrap', deltaColor(snap.delta_1w_pct))}>
                  {snap.delta_1w_pct != null ? fmtPct(snap.delta_1w_pct) : '—'}
                </td>
                <td className={clsx('px-3 py-2 font-mono whitespace-nowrap', deltaColor(snap.delta_1m_pct))}>
                  {snap.delta_1m_pct != null ? fmtPct(snap.delta_1m_pct) : '—'}
                </td>
                <td className={clsx('px-3 py-2 font-mono whitespace-nowrap', deltaColor(snap.delta_3m_pct))}>
                  {snap.delta_3m_pct != null ? fmtPct(snap.delta_3m_pct) : '—'}
                </td>
                <td className="px-3 py-2 font-mono text-text-secondary whitespace-nowrap">
                  {snap.z_score_1y != null
                    ? `${snap.z_score_1y > 0 ? '+' : ''}${snap.z_score_1y.toFixed(2)}`
                    : '—'}
                </td>
                <td className="px-3 py-2 whitespace-nowrap">
                  <span className={clsx(
                    'px-1.5 py-0.5 rounded text-xs',
                    snap.signal === 'red' ? 'bg-signal-red/20 text-signal-red' :
                    snap.signal === 'yellow' ? 'bg-signal-yellow/20 text-signal-yellow' :
                    'bg-signal-green/20 text-signal-green'
                  )}>
                    {snap.signal === 'red' ? '경고' : snap.signal === 'yellow' ? '주의' : '정상'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="py-8 text-center text-text-muted text-sm">데이터 수집 중...</div>
        )}
      </div>
    </section>
  )
}

function deltaColor(v: number | null): string {
  if (v == null) return 'text-text-muted'
  if (v > 2) return 'text-signal-green'
  if (v > 0) return 'text-signal-green/70'
  if (v < -2) return 'text-signal-red'
  if (v < 0) return 'text-signal-red/70'
  return 'text-text-muted'
}
