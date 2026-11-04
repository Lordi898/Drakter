import { useEffect, useState } from 'react'
import { getRelated, listRelationshipTypes, searchRelationships, type RelationshipFilters } from './api'
import type { RelatedItems, RelationshipOut, RelationshipTypeOut } from './types'

export type Load<T> =
  | { readonly state: 'loading' }
  | { readonly state: 'error'; readonly error: unknown }
  | { readonly state: 'ready'; readonly data: T }

function useLoad<T>(load: () => Promise<T>, deps: readonly unknown[]): Load<T> {
  const [result, setResult] = useState<Load<T>>({ state: 'loading' })
  useEffect(() => {
    let cancelled = false
    setResult({ state: 'loading' })
    load().then(
      (data) => { if (!cancelled) setResult({ state: 'ready', data }) },
      (error: unknown) => { if (!cancelled) setResult({ state: 'error', error }) }
    )
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return result
}

export function useRelationshipTypes(): Load<RelationshipTypeOut[]> {
  return useLoad(listRelationshipTypes, [])
}

export function useRelated(entityId: string, refreshKey: number): Load<RelatedItems> {
  return useLoad(() => getRelated(entityId), [entityId, refreshKey])
}

export interface RelationshipList {
  readonly items: readonly RelationshipOut[]
  readonly loading: boolean
  readonly error: unknown
  readonly hasMore: boolean
  readonly loadMore: () => void
}

/** Lista paginada: se reinicia al cambiar filtros o `refreshKey`. */
export function useRelationshipList(filters: RelationshipFilters, refreshKey: number): RelationshipList {
  const [items, setItems] = useState<readonly RelationshipOut[]>([])
  const [cursor, setCursor] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown>(null)
  const [request, setRequest] = useState<{ cursor: string | null; n: number }>({ cursor: null, n: 0 })
  const key = JSON.stringify(filters)

  useEffect(() => {
    setItems([])
    setCursor(null)
    setRequest((r) => ({ cursor: null, n: r.n + 1 }))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, refreshKey])

  useEffect(() => {
    if (request.n === 0) return
    let cancelled = false
    setLoading(true)
    setError(null)
    searchRelationships(filters, request.cursor).then(
      (page) => {
        if (cancelled) return
        setItems((prev) => (request.cursor === null ? page.items : [...prev, ...page.items]))
        setCursor(page.next_cursor)
        setLoading(false)
      },
      (e: unknown) => {
        if (cancelled) return
        setError(e)
        setLoading(false)
      }
    )
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [request])

  return {
    items,
    loading,
    error,
    hasMore: cursor !== null,
    loadMore: () => { if (cursor !== null) setRequest((r) => ({ cursor, n: r.n + 1 })) }
  }
}
