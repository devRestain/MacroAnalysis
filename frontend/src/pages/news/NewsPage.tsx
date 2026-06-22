import { useState } from 'react'
import { ExternalLink } from 'lucide-react'
import { getNews } from '../../shared/api/news'
import { getSentimentSignals } from '../../shared/api/sentiment'
import { Badge } from '../../shared/components/Badge'
import { Card } from '../../shared/components/Card'
import { useLanguage } from '../../shared/i18n'
import { DisabledState, EmptyState, ErrorState, LoadingState } from '../../shared/components/StateViews'
import { useResource } from '../../shared/hooks/useResource'
import { timeAgo } from '../../shared/utils/format'

const categories = ['all', 'fed', 'macro', 'fx', 'equity', 'commodity', 'geopolitics', 'general']

export function NewsPage() {
  const { t, label } = useLanguage()
  const [category, setCategory] = useState('all')
  const news = useResource(() => getNews(category, 50), [category], { optional: true })
  const sentiment = useResource(() => getSentimentSignals(50), [], { optional: true })

  return (
    <div className="page-shell animate-fade-up">
      <div className="mb-6">
        <h1 className="text-3xl font-extrabold tracking-[-0.04em]">{t('news.title')}</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-text-secondary">{t('news.description')}</p>
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        {categories.map((item) => (
          <button key={item} onClick={() => setCategory(item)} className={`filter-chip ${category === item ? 'filter-chip-active' : ''}`}>
            {label('newsCategory', item, item)}
          </button>
        ))}
      </div>

      <Card title={t('news.card.recent')} eyebrow={t('news.card.recentEyebrow')} tone="amber">
        {news.state.status === 'loading' || news.state.status === 'idle' ? <LoadingState /> : news.state.status === 'disabled' ? <DisabledState /> : news.state.status === 'error' ? <ErrorState label={t('news.apiUnavailable')} /> : news.state.status === 'empty' ? <EmptyState label={t('news.empty')} /> : (
          <div className="divide-y divide-surface-border">
            {news.state.data.map((item) => {
              const relatedSentiment = sentiment.state.status === 'success'
                ? sentiment.state.data.find((signal) => String(signal.sourceId) === String(item.id) || signal.sourceType === 'news_item')
                : undefined
              return (
                <a key={item.id} href={item.url ?? '#'} target={item.url ? '_blank' : undefined} rel="noreferrer" className="block rounded-[22px] px-3 py-4 first:pt-0 last:pb-0 hover:bg-white/65">
                  <div className="flex items-start gap-3">
                    <Badge>{label('newsCategory', item.category, item.category)}</Badge>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start gap-2">
                        <h2 className="text-base font-extrabold leading-7 tracking-[-0.01em]">{item.title}</h2>
                        {item.url && <ExternalLink size={13} className="mt-1 shrink-0 text-text-muted" />}
                      </div>
                      {item.summary && <p className="mt-2 line-clamp-2 text-sm leading-7 text-text-secondary">{item.summary}</p>}
                      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-text-muted">
                        <span>{item.source}</span>
                        <span>{timeAgo(item.publishedAt)}</span>
                        {relatedSentiment && <Badge tone="blue">{t('news.sentimentLinked')} {relatedSentiment.stance ?? relatedSentiment.stanceScore ?? 'linked'}</Badge>}
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
