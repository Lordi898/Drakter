import { useCallback, useEffect, useRef, useState } from 'react'
import { errorMessage } from '../remote'
import { listActivity } from './api'
import type { ActivityFilters, AuditEvent } from './types'

export interface ActivityState {
  readonly items: readonly AuditEvent[]
  readonly loading: boolean
  readonly error: string | null
  readonly hasMore: boolean
  readonly loadMore: () => void
  readonly reload: () => void
}

/** Registro de actividad con paginación por cursor; descarta respuestas de filtros anteriores. */
export function useActivity(filters: ActivityFilters = {}): ActivityState {
  const [items, setItems] = useState<readonly AuditEvent[]>([])
  const [cursor, setCursor] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tick, setTick] = useState(0)
  const latest = useRef(0)
  const key = JSON.stringify(filters)

  const fetchPage = useCallback(
    (after: string | null) => {
      const id = ++latest.current
      setLoading(true)
      setError(null)
      listActivity(JSON.parse(key) as ActivityFilters, after)
        .then((page) => {
          if (id !== latest.current) return
          setItems((prev) => (after ? [...prev, ...page.items] : page.items))
          setCursor(page.next_cursor)
        })
        .catch((e: unknown) => {
          if (id !== latest.current) return
          if (!after) setItems([])
          setError(errorMessage(e))
        })
        .finally(() => {
          if (id === latest.current) setLoading(false)
        })
    },
    [key]
  )

  useEffect(() => fetchPage(null), [fetchPage, tick])

  const loadMore = useCallback(() => {
    if (cursor) fetchPage(cursor)
  }, [cursor, fetchPage])
  const reload = useCallback(() => setTick((n) => n + 1), [])

  return { items, loading, error, hasMore: cursor !== null, loadMore, reload }
}
