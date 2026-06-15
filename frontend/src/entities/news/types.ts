export interface NewsItem {
  id: number | string
  source: string
  title: string
  summary: string | null
  url: string | null
  category: string
  publishedAt: string | null
}

