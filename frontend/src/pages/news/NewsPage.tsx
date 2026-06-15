import { useState } from 'react'
import { ExternalLink } from 'lucide-react'
import { getNews } from '../../shared/api/news'
import { getSentimentSignals } from '../../shared/api/sentiment'
import { Badge } from '../../shared/components/Badge'
import { Card } from '../../shared/components/Card'
import { DisabledState, EmptyState, ErrorState, LoadingState } from '../../shared/components/StateViews'
import { useResource } from '../../shared/hooks/useResource'
import { timeAgo } from '../../shared/utils/format'

const categories = ['all', 'fed', 'macro', 'fx', 'equity', 'commodity', 'geopolitics', 'general']

export function NewsPage() {
  const [category, setCategory] = useState('all')
  const news = useResource(() => getNews(category, 50), [category], { optional: true })
  const sentiment = useResource(() => getSentimentSignals(50), [], { optional: true })

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 lg:px-6">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">News</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-text-secondary">Recent collected news. The UI does not assume unlimited historical retention.</p>
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        {categories.map((item) => (
          <button key={item} onClick={() => setCategory(item)} className={`border px-3 py-1.5 text-xs ${category === item ? 'border-accent bg-accent/10 text-accent' : 'border-surface-border text-text-secondary hover:bg-surface-hover'}`}>
            {item}
          </button>
        ))}
      </div>

      <Card title="Recent News" eyebrow="listing">
        {news.state.status === 'loading' || news.state.status === 'idle' ? <LoadingState /> : news.state.status === 'disabled' ? <DisabledState /> : news.state.status === 'error' ? <ErrorState label="News API is unavailable." /> : news.state.status === 'empty' ? <EmptyState label="No recent news collected." /> : (
          <div className="divide-y divide-surface-border">
            {news.state.data.map((item) => {
              const relatedSentiment = sentiment.state.status === 'success'
                ? sentiment.state.data.find((signal) => String(signal.sourceId) === String(item.id) || signal.sourceType === 'news_item')
                : undefined
              return (
                <a key={item.id} href={item.url ?? '#'} target={item.url ? '_blank' : undefined} rel="noreferrer" className="block py-4 first:pt-0 last:pb-0 hover:bg-surface-hover/40">
                  <div className="flex items-start gap-3">
                    <Badge>{item.category}</Badge>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start gap-2">
                        <h2 className="text-sm font-semibold leading-6">{item.title}</h2>
                        {item.url && <ExternalLink size={13} className="mt-1 shrink-0 text-text-muted" />}
                      </div>
                      {item.summary && <p className="mt-1 line-clamp-2 text-sm leading-6 text-text-secondary">{item.summary}</p>}
                      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-text-muted">
                        <span>{item.source}</span>
                        <span>{timeAgo(item.publishedAt)}</span>
                        {relatedSentiment && <Badge tone="blue">sentiment {relatedSentiment.stance ?? relatedSentiment.stanceScore ?? 'linked'}</Badge>}
                      </div>
                    </div>
                  </div>
                </a>
              )
            })}
          </div>
        )}
      </Card>
    </div>
  )
}
