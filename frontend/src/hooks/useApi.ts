import { useState, useEffect, useCallback } from 'react'

export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = [],
  refreshInterval?: number
) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    try {
      setError(null)
      const result = await fetcher()
      setData(result)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, deps) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetch()
    if (refreshInterval) {
      const id = setInterval(fetch, refreshInterval)
      return () => clearInterval(id)
    }
  }, [fetch, refreshInterval])

  return { data, loading, error, refetch: fetch }
}
