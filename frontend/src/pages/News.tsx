import { Activity, ArrowLeft, ExternalLink } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { api } from '../lib/api'
import { timeAgo } from '../lib/utils'

const CATEGORY_LABELS: Record<string, string> = {
  fed: 'Fed',
  macro: 'Macro',
  fx: 'FX',
  equity: 'Equity',
  commodity: 'Commodity',
  geopolitics: 'Geo',
  general: 'General',
}

export function News() {
  const { data, loading, error } = useApi(() => api.news(undefined, 100), [], 5 * 60 * 1000)
  const news = data?.news ?? []

  return (
    <div className="min-h-screen bg-surface text-text-primary">
      <header className="sticky top-0 z-40 bg-surface/95 backdrop-blur-sm border-b border-surface-border">
        <div className="flex items-center justify-between px-4 h-10">
          <a href="/" className="flex items-center gap-2 text-text-secondary hover:text-text-primary transition-colors">
            <ArrowLeft size={14} />
            <span className="text-xs">대시보드</span>
          </a>
          <div className="flex items-center gap-2">
            <Activity size={16} className="text-accent" />
            <span className="text-sm font-semibold">MacroWatch 뉴스</span>
          </div>
          <div className="w-16" />
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-5">
        {loading && <div className="py-16 text-center text-sm text-text-muted">뉴스 로딩 중...</div>}
        {error && <div className="py-16 text-center text-sm text-signal-red">뉴스를 불러오지 못했습니다.</div>}
        {!loading && !error && news.length === 0 && (
          <div className="py-16 text-center text-sm text-text-muted">수집된 뉴스가 없습니다.</div>
        )}

        <div className="divide-y divide-surface-border border border-surface-border bg-surface-card">
          {news.map((item) => (
            <a
              key={item.id}
              href={item.url || '#'}
              target="_blank"
              rel="noopener noreferrer"
              className="block px-4 py-3 hover:bg-surface-hover transition-colors"
            >
              <div className="flex items-start gap-3">
                <span className="mt-0.5 min-w-16 text-center text-xs px-2 py-1 rounded bg-surface-hover text-text-secondary">
                  {CATEGORY_LABELS[item.category] || item.category}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-start gap-2">
                    <h2 className="text-sm font-medium leading-6 text-text-primary">{item.title}</h2>
                    {item.url && <ExternalLink size={12} className="mt-1 flex-shrink-0 text-text-muted" />}
                  </div>
                  {item.summary && (
                    <p className="mt-1 text-xs leading-5 text-text-secondary line-clamp-2">{item.summary}</p>
                  )}
                  <div className="mt-1 text-xs text-text-muted">
                    {item.source} · {timeAgo(item.published_at)}
                  </div>
                </div>
              </div>
            </a>
          ))}
        </div>
      </main>
    </div>
  )
}
