import { SummaryResponse } from '../../lib/api'
import { fmt, fmtPct, directionArrow } from '../../lib/utils'

const EQUITY_META: Record<string, string> = {
  '^GSPC': 'S&P 500',
  '^IXIC': 'NASDAQ',
  '^KS11': 'KOSPI',
  '^N225': 'Nikkei',
  '^GDAXI': 'DAX',
  '^SSEC': '상하이',
}

interface Props {
  equities: SummaryResponse['equities']
}

export function Zone6Equities({ equities }: Props) {
  return (
    <section className="border-b border-surface-border bg-surface-card">
      <div className="flex items-center overflow-x-auto gap-px">
        {Object.entries(EQUITY_META).map(([ticker, name]) => {
          const eq = equities[ticker]
          const up = eq && eq.change_pct > 0
          const flat = !eq || Math.abs(eq.change_pct) < 0.05
          return (
            <div
              key={ticker}
              className="flex items-center gap-3 px-4 py-2.5 border-r border-surface-border flex-shrink-0"
            >
              <span className="text-xs text-text-secondary">{name}</span>
              <span className="font-mono text-sm text-text-primary">
                {eq ? fmt(eq.close, 0) : '—'}
              </span>
              <span className={`text-xs font-mono ${flat ? 'text-text-muted' : up ? 'text-signal-green' : 'text-signal-red'}`}>
                {eq ? `${directionArrow(up ? 'up' : flat ? 'flat' : 'down')} ${fmtPct(eq.change_pct)}` : '—'}
              </span>
            </div>
          )
        })}
      </div>
    </section>
  )
}
