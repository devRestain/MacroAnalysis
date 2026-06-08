import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { api, ChartResponse } from '../../lib/api'
import { fmt, fmtPct, signalColor } from '../../lib/utils'
import {
  Chart as ChartJS,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Tooltip,
  Filler,
} from 'chart.js'
import { Line } from 'react-chartjs-2'

ChartJS.register(LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Filler)

type Period = '1w' | '1m' | '3m' | '1y' | 'all'

interface Props {
  indicatorKey: string | null
  snapshot: { label: string; value: number | null; unit: string | null; z_score_1y: number | null; signal: string } | null
  onClose: () => void
}

export function SidePanel({ indicatorKey, snapshot, onClose }: Props) {
  const [period, setPeriod] = useState<Period>('3m')
  const [chart, setChart] = useState<ChartResponse | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!indicatorKey) return
    setLoading(true)
    api.chart(indicatorKey, period)
      .then(setChart)
      .catch(() => setChart(null))
      .finally(() => setLoading(false))
  }, [indicatorKey, period])

  if (!indicatorKey) return null

  const PERIODS: Period[] = ['1w', '1m', '3m', '1y', 'all']
  const PERIOD_LABELS: Record<Period, string> = { '1w': '1주', '1m': '1개월', '3m': '3개월', '1y': '1년', all: '전체' }

  const chartData = chart ? {
    labels: chart.data.map((d) => d.date.split('T')[0]),
    datasets: [{
      data: chart.data.map((d) => d.value),
      borderColor: '#4f8ef7',
      backgroundColor: 'rgba(79,142,247,0.08)',
      fill: true,
      tension: 0.3,
      pointRadius: 0,
      borderWidth: 1.5,
    }],
  } : null

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false }, tooltip: {
      callbacks: {
        label: (ctx: { raw: number }) => ` ${fmt(ctx.raw, 2)}${snapshot?.unit || ''}`,
      },
    }},
    scales: {
      x: { ticks: { color: '#4b5568', maxTicksLimit: 6 }, grid: { color: '#222840' } },
      y: { ticks: { color: '#4b5568' }, grid: { color: '#222840' } },
    },
  }

  return (
    <div className="fixed inset-y-0 right-0 w-full max-w-sm bg-surface-card border-l border-surface-border z-50 flex flex-col animate-slide-in-right shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-border">
        <div>
          <div className="text-sm font-semibold text-text-primary">{snapshot?.label ?? indicatorKey}</div>
          <div className="text-xs text-text-secondary font-mono">{indicatorKey}</div>
        </div>
        <button onClick={onClose} className="p-1.5 hover:bg-surface-hover rounded transition-colors">
          <X size={16} className="text-text-secondary" />
        </button>
      </div>

      {/* Value */}
      <div className="px-4 py-3 border-b border-surface-border">
        <div className="font-mono text-2xl font-bold text-text-primary">
          {fmt(snapshot?.value, 2)}{snapshot?.unit}
        </div>
        {snapshot?.z_score_1y != null && (
          <div className={`text-xs mt-1 ${signalColor(snapshot.signal)}`}>
            Z-score: {snapshot.z_score_1y > 0 ? '+' : ''}{snapshot.z_score_1y.toFixed(2)} (1년 기준)
          </div>
        )}
      </div>

      {/* Period selector */}
      <div className="flex gap-1 px-4 py-2 border-b border-surface-border">
        {PERIODS.map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={`text-xs px-2.5 py-1 rounded transition-colors ${
              period === p ? 'bg-accent/20 text-accent' : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            {PERIOD_LABELS[p]}
          </button>
        ))}
      </div>

      {/* Chart */}
      <div className="flex-1 p-4">
        {loading && (
          <div className="h-full flex items-center justify-center text-text-muted text-sm">로딩 중...</div>
        )}
        {!loading && chartData && (
          <div className="h-full">
            <Line data={chartData} options={chartOptions as any} />
          </div>
        )}
        {!loading && !chartData && (
          <div className="h-full flex items-center justify-center text-text-muted text-sm">
            차트 데이터 없음
          </div>
        )}
      </div>
    </div>
  )
}
