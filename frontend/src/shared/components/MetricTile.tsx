import { ArrowDownRight, ArrowRight, ArrowUpRight } from 'lucide-react'
import { ChangeSnapshot } from '../../entities/changeSnapshot/types'
import { useLanguage } from '../i18n'
import { fmt, fmtPct, fmtDate } from '../utils/format'
import { Badge } from './Badge'

export function MetricTile({ item, onClick }: { item: ChangeSnapshot; onClick: () => void }) {
  const { label } = useLanguage()
  const signalTone = item.signal === 'red' ? 'red' : item.signal === 'yellow' ? 'yellow' : item.signal === 'green' ? 'green' : 'neutral'
  const DirectionIcon = item.direction === 'up' ? ArrowUpRight : item.direction === 'down' ? ArrowDownRight : ArrowRight

  return (
    <button
      onClick={onClick}
      className="group flex min-w-0 flex-col rounded-[14px] border border-surface-border bg-white px-3 py-2.5 text-left transition-colors hover:border-accent/25 hover:bg-surface-hover"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-[10px] font-bold uppercase tracking-[0.14em] text-text-muted">{item.label}</div>
          <div className="mt-1 truncate font-mono text-[1.15rem] font-semibold tracking-[-0.05em] text-text-primary lg:text-[1.25rem]">
            {fmt(item.value, 2, item.unit ?? '')}
          </div>
        </div>
        <Badge tone={signalTone}>{label('signal', item.signal, item.signal)}</Badge>
      </div>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[10px]">
        <div className="flex items-center gap-1.5 text-text-secondary">
          <DirectionIcon size={12} className={item.direction === 'down' ? 'text-signal-red' : item.direction === 'up' ? 'text-signal-green' : 'text-text-muted'} />
          <span>1D {fmtPct(item.delta1dPct)}</span>
          <span>1M {fmtPct(item.delta1mPct)}</span>
        </div>
        <span className="truncate text-text-muted">{fmtDate(item.date)}</span>
      </div>
    </button>
  )
}
