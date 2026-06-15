import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../api/client'

export type ResourceState<T> =
  | { status: 'idle' }
  | { status: 'loading'; data?: T }
  | { status: 'success'; data: T }
  | { status: 'empty'; data?: T }
  | { status: 'error'; error: Error; data?: T }
  | { status: 'disabled'; error?: Error }

function isEmpty(value: unknown) {
  if (Array.isArray(value)) return value.length === 0
  if (value && typeof value === 'object') return Object.keys(value).length === 0
  return value == null
}

export function useResource<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = [],
  options: { refreshInterval?: number; optional?: boolean; emptyWhen?: (value: T) => boolean } = {}
) {
  const [state, setState] = useState<ResourceState<T>>({ status: 'idle' })

  const load = useCallback(async () => {
    setState((prev) => ({ status: 'loading', data: 'data' in prev ? prev.data : undefined }))
    try {
      const data = await fetcher()
      const empty = options.emptyWhen ? options.emptyWhen(data) : isEmpty(data)
      setState(empty ? { status: 'empty', data } : { status: 'success', data })
    } catch (error) {
      if (error instanceof ApiError && (error.kind === 'disabled' || error.kind === 'unauthorized')) {
        setState({ status: 'disabled', error })
      } else {
        setState({ status: 'error', error: error instanceof Error ? error : new Error('Unknown error') })
      }
    }
  }, deps) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    load()
    if (!options.refreshInterval) return undefined
    const id = window.setInterval(load, options.refreshInterval)
    return () => window.clearInterval(id)
  }, [load, options.refreshInterval])

  return { state, reload: load }
}

