import { useCallback, useEffect, useRef, useState } from 'react'

interface UsePollingResult<T> {
  data: T | null
  error: string | null
  loading: boolean
  refetch: () => void
}

/**
 * Polls `fetcher` every `intervalMs` while the component is mounted.
 * The spec calls for polling-based updates initially (WebSockets are a
 * later bonus), so every data-driven page in this dashboard uses this
 * hook rather than fetching once.
 */
export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs: number = 4000,
  deps: unknown[] = [],
): UsePollingResult<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const load = useCallback(async () => {
    try {
      const result = await fetcherRef.current()
      setData(result)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    setLoading(true)
    load()
    const id = setInterval(load, intervalMs)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs, ...deps])

  return { data, error, loading, refetch: load }
}
