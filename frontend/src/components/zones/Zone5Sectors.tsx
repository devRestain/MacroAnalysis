import { useState } from 'react'
import { SectorRow } from '../../lib/api'
import { SummaryResponse } from '../../lib/api'
import { fmtPct, clsx } from '../../lib/utils'

type Period = '1d' | '1m' | '3m' | 'ytd'

interface Props {
  sectors: SectorRow[]
  fomc: SummaryResponse['fomc']
}

const PERIOD_LABELS: Record<Period, string> = { '1d': '1일', '1m': '1개월', '3m': '3개월', ytd: 'YTD' }

function heatColor(v: number | null): string {
  if (v == null) return 'bg-surface-hover text-text-muted'
  if (v >= 5) return 'bg-signal-green/30 text-signal-green'
  if (v >= 2) return 'bg-signal-green/15 text-signal-green'
  if (v >= 0.5) return 'bg-signal-green/8 text-signal-green/70'
  if (v >= -0.5) return 'bg-surface-hover text-text-muted'
  if (v >= -2) return 'bg-signal-red/8 text-signal-red/70'
  if (v >= -5) return 'bg-signal-red/15 text-signal-red'
  return 'bg-signal-red/30 text-signal-red'
}

export function Zone5Sectors({ sectors, fomc }: Props) {
  const [period, setPeriod] = useState<Period>('1m')

  const getValue = (s: SectorRow): number | null => {
    if (period === '1d') return s.change_1d
    if (period === '1m') return s.change_1m
    if (period === '3m') return s.change_3m
    return s.change_ytd
  }

  const today = new Date()
  const nextDate = fomc.next_date ? new Date(fomc.next_date) : null
  const daysLeft = fomc.days_left

  return (
    <section className="grid grid-cols-1 lg:grid-cols-2 gap-px bg-surface-border border-b border-surface-border">
      {/* Sector Heatmap */}
      <div className="bg-surface-card p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-widest">
            섹터 상대 강도
          </h3>
          <div className="flex gap-1">
            {(Object.keys(PERIOD_LABELS) as Period[]).map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={clsx(
                  'text-xs px-2 py-0.5 rounded transition-colors',
                  period === p ? 'bg-accent/20 text-accent' : 'text-text-muted hover:text-text-secondary'
                )}
              >
                {PERIOD_LABELS[p]}
              </button>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-1.5">
          {sectors.map((s) => {
            const v = getValue(s)
            return (
              <div
                key={s.ticker}
                className={clsx('flex items-center justify-between px-2.5 py-2 rounded text-xs', heatColor(v))}
              >
                <span className="font-medium">{s.name}</span>
                <span className="font-mono">{v != null ? fmtPct(v) : '—'}</span>
              </div>
            )
          })}
        </div>
      </div>

      {/* FOMC Timeline */}
      <div className="bg-surface-card p-4">
        <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-widest mb-3">
          FOMC 현황
        </h3>
        {nextDate && (
          <div className="mb-4">
            <div className="flex items-center gap-3 mb-2">
              <div className="text-3xl font-mono font-bold text-text-primary">
                D-{daysLeft ?? '?'}
              </div>
              <div>
                <div className="text-sm text-text-primary">다음 FOMC</div>
                <div className="text-xs text-text-secondary">
                  {nextDate.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' })}
                </div>
              </div>
            </div>
            {fomc.prob_hold != null && (
              <div>
                <div className="text-xs text-text-secondary mb-1.5">시장 금리 기대 (선물가격 추정)</div>
                <div className="flex gap-1 h-6 rounded overflow-hidden">
                  <div
                    className="bg-signal-green/60 flex items-center justify-center text-xs text-signal-green font-medium"
                    style={{ width: `${(fomc.prob_hold || 0) * 100}%` }}
                  >
                    {fomc.prob_hold != null ? `동결 ${(fomc.prob_hold * 100).toFixed(0)}%` : ''}
                  </div>
                  <div
                    className="bg-accent/60 flex items-center justify-center text-xs text-accent font-medium"
                    style={{ width: `${(fomc.prob_cut || 0) * 100}%` }}
                  >
                    {fomc.prob_cut != null ? `인하 ${(fomc.prob_cut * 100).toFixed(0)}%` : ''}
                  </div>
                  {fomc.prob_hike != null && fomc.prob_hike > 0.01 && (
                    <div
                      className="bg-signal-red/60 flex items-center justify-center text-xs text-signal-red font-medium"
                      style={{ width: `${fomc.prob_hike * 100}%` }}
                    >
                      인상 {(fomc.prob_hike * 100).toFixed(0)}%
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
        <a href="/fomc" className="text-xs text-accent hover:text-accent/80 transition-colors">
          FOMC 이력 전체 보기 →
        </a>
      </div>
    </section>
  )
}
