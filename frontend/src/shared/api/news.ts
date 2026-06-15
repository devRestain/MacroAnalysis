import { NewsItem } from '../../entities/news/types'
import { apiGet } from './client'

interface NewsItemResponse {
  id: number
  source: string
  title: string
  summary: string | null
  url: string | null
  category: string
  published_at: string | null
}

interface NewsResponse {
  news?: NewsItemResponse[]
}

export async function getNews(category?: string, limit = 30): Promise<NewsItem[]> {
  const params = new URLSearchParams({ limit: String(limit) })
  if (category && category !== 'all') params.set('category', category)
  const response = await apiGet<NewsResponse>(`/news?${params.toString()}`)
  return (response.news ?? []).map((item) => ({
    id: item.id,
    source: item.source,
    title: item.title,
    summary: item.summary,
    url: item.url,
    category: item.category,
    publishedAt: item.published_at,
  }))
}

