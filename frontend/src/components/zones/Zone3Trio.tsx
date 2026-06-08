import { SummaryResponse, NewsItem } from '../../lib/api'
import { timeAgo } from '../../lib/utils'
import { ExternalLink, Bot, ChevronRight } from 'lucide-react'

interface Props {
  yieldCurve: SummaryResponse['yield_curve']
  aiHeadline: string | null
  newsPreview: NewsItem[]
  onOpenChat: () => void
  onOpenAiSummary: () => void
}

const CATEGORY_COLOR: Record<string, string> = {
  fed: 'bg-accent/20 text-accent',
  macro: 'bg-purple-500/20 text-purple-400',
  fx: 'bg-yellow-500/20 text-yellow-400',
  equity: 'bg-emerald-500/20 text-emerald-400',
  commodity: 'bg-orange-500/20 text-orange-400',
  geopolitics: 'bg-red-500/20 text-red-400',
  general: 'bg-surface-border text-text-secondary',
}

export function Zone3Trio({ yieldCurve, aiHeadline, newsPreview, onOpenChat, onOpenAiSummary }: Props) {
  const curveData = [
    { label: '2Y', key: 'DGS2' },
    { label: '10Y', key: 'DGS10' },
    { label: '30Y', key: 'DGS30' },
    { label: '10Y-2Y', key: 'T10Y2Y' },
  ]

  return (
    <section className="grid grid-cols-1 lg:grid-cols-3 gap-px bg-surface-border border-b border-surface-border">
      {/* Yield Curve */}
      <div className="bg-surface-card p-4">
        <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-widest mb-3">
          수익률 곡선
        </h3>
        <div className="space-y-2">
          {curveData.map(({ label, key }) => {
            const val = yieldCurve[key]
            return (
              <div key={key} className="flex items-center gap-2">
                <span className="text-xs text-text-secondary w-12">{label}</span>
                <div className="flex-1 bg-surface-hover rounded-full h-1.5 overflow-hidden">
                  <div
                    className="h-full bg-accent rounded-full transition-all"
                    style={{ width: val != null ? `${Math.min(val / 6 * 100, 100)}%` : '0%' }}
                  />
                </div>
                <span className="text-xs font-mono text-text-primary w-12 text-right">
                  {val != null ? `${val.toFixed(2)}%` : '—'}
                </span>
              </div>
            )
          })}
        </div>
        {yieldCurve['T10Y2Y'] != null && (
          <div className={`mt-3 text-xs px-2 py-1 rounded ${yieldCurve['T10Y2Y'] < 0 ? 'bg-signal-red/10 text-signal-red' : 'bg-signal-green/10 text-signal-green'}`}>
            {yieldCurve['T10Y2Y'] < 0 ? '장단기 역전 중' : '정상 기울기'}
          </div>
        )}
      </div>

      {/* AI Summary */}
      <div className="bg-surface-card p-4 flex flex-col">
        <div className="flex items-center gap-2 mb-3">
          <Bot size={14} className="text-accent" />
          <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-widest">
            AI 일일 브리핑
          </h3>
        </div>
        {aiHeadline ? (
          <p className="text-sm text-text-primary leading-relaxed flex-1">{aiHeadline}</p>
        ) : (
          <p className="text-sm text-text-muted flex-1">오늘 브리핑이 아직 생성되지 않았습니다.</p>
        )}
        <div className="flex gap-2 mt-4">
          <button
            onClick={onOpenAiSummary}
            className="flex items-center gap-1 text-xs text-accent hover:text-accent/80 transition-colors"
          >
            전체 요약 보기 <ChevronRight size={12} />
          </button>
          <button
            onClick={onOpenChat}
            className="flex items-center gap-1 text-xs px-3 py-1.5 bg-accent/20 text-accent rounded hover:bg-accent/30 transition-colors ml-auto"
          >
            <Bot size={12} /> AI 채팅
          </button>
        </div>
      </div>

      {/* News Preview */}
      <div className="bg-surface-card p-4">
        <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-widest mb-3">
          주요 뉴스
        </h3>
        <div className="space-y-2.5">
          {newsPreview.slice(0, 5).map((item) => (
            <a
              key={item.id}
              href={item.url || '#'}
              target="_blank"
              rel="noopener noreferrer"
              className="block group"
            >
              <div className="flex items-start gap-2">
                <span className={`text-xs px-1.5 py-0.5 rounded flex-shrink-0 mt-0.5 ${CATEGORY_COLOR[item.category] || CATEGORY_COLOR.general}`}>
                  {item.category}
                </span>
                <span className="text-xs text-text-primary group-hover:text-accent transition-colors leading-relaxed line-clamp-2">
                  {item.title}
                </span>
              </div>
              <div className="flex items-center gap-1 mt-0.5 ml-auto text-xs text-text-muted">
                <span>{item.source}</span>
                <span>·</span>
                <span>{timeAgo(item.published_at)}</span>
                {item.url && <ExternalLink size={10} className="ml-1 opacity-50 group-hover:opacity-100" />}
              </div>
            </a>
          ))}
        </div>
        <a href="/news" className="flex items-center gap-1 mt-3 text-xs text-accent hover:text-accent/80 transition-colors">
          전체 뉴스 <ChevronRight size={12} />
        </a>
      </div>
    </section>
  )
}
