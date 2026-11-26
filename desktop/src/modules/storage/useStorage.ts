import { useCallback, useEffect, useRef, useState } from 'react'
import { listFolders, listLocations, listResources, searchResources } from './api'
import { isDisconnected, notifyError } from './errors'
import type { Folder, ResourceSummary, StorageLocation } from './types'

export interface Filters {
  readonly folderId: string | null
  readonly search: string
  readonly type: string
  readonly availability: string
}

export interface ResourceRow {
  readonly resource: ResourceSummary
  readonly snippet?: string
}

export function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), ms)
    return () => clearTimeout(timer)
  }, [value, ms])
  return debounced
}

/** Ubicaciones del almacén; `offline` si no hay conexión con el servicio. `reloadKey` fuerza otra carga. */
export function useLocations(reloadKey: number): {
  readonly locations: readonly StorageLocation[] | null
  readonly offline: boolean
} {
  const [locations, setLocations] = useState<readonly StorageLocation[] | null>(null)
  const [offline, setOffline] = useState(false)

  useEffect(() => {
    let live = true
    listLocations()
      .then((l) => {
        if (!live) return
        setOffline(false)
        setLocations(l)
      })
      .catch((error: unknown) => {
        if (!live) return
        if (isDisconnected(error)) {
          setOffline(true)
          return
        }
        setLocations([])
        notifyError('No se han podido cargar las ubicaciones', error)
      })
    return () => {
      live = false
    }
  }, [reloadKey])

  return { locations, offline }
}

/**
 * Carpetas hijas de `parentId` (null = raíces). Con `enabled` false no pide nada; una vez cargadas
 * no se vuelven a pedir salvo que cambie `reloadKey`. `null` mientras carga.
 */
export function useFolders(parentId: string | null, enabled = true, reloadKey = 0): readonly Folder[] | null {
  const [folders, setFolders] = useState<readonly Folder[] | null>(null)
  const loadedKey = useRef<number | null>(null)

  useEffect(() => {
    if (!enabled || loadedKey.current === reloadKey) return
    let live = true
    loadedKey.current = reloadKey
    listFolders(parentId)
      .then((list) => live && setFolders(list))
      .catch((error: unknown) => {
        if (live) setFolders([])
        notifyError(
          parentId === null ? 'No se han podido cargar las carpetas' : 'No se han podido cargar las subcarpetas',
          error
        )
      })
    return () => {
      live = false
      // Si se cancela antes de responder, la próxima activación debe volver a pedir.
      if (loadedKey.current === reloadKey) loadedKey.current = null
    }
  }, [parentId, enabled, reloadKey])

  return folders
}

export interface ResourcesState {
  readonly rows: readonly ResourceRow[]
  readonly hasMore: boolean
  readonly loading: boolean
  readonly failed: boolean
  readonly searching: boolean
  readonly loadMore: () => void
  readonly retry: () => void
}

/** Lista o búsqueda de recursos con paginación por cursor; descarta respuestas de peticiones antiguas. */
export function useResources(filters: Filters, reloadKey: number): ResourcesState {
  const [rows, setRows] = useState<readonly ResourceRow[]>([])
  const [cursor, setCursor] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const generation = useRef(0)
  const searching = filters.search.trim() !== ''

  const fetchPage = useCallback(
    async (after: string | null) => {
      const mine = ++generation.current
      setLoading(true)
      setFailed(false)
      try {
        let page: { rows: ResourceRow[]; next: string | null }
        if (searching) {
          const result = await searchResources(filters.search.trim(), filters.type, after)
          const kept = result.items.filter(
            (hit) => filters.availability === '' || hit.resource.availability_status === filters.availability
          )
          page = { rows: kept.map((hit) => ({ resource: hit.resource, snippet: hit.snippet })), next: result.next_cursor }
        } else {
          const result = await listResources({
            folderId: filters.folderId, type: filters.type, availability: filters.availability, cursor: after
          })
          page = { rows: result.items.map((resource) => ({ resource })), next: result.next_cursor }
        }
        if (mine !== generation.current) return
        setRows((prev) => (after ? [...prev, ...page.rows] : page.rows))
        setCursor(page.next)
      } catch (error) {
        if (mine !== generation.current) return
        setFailed(true)
        notifyError('No se han podido cargar los recursos', error)
      } finally {
        if (mine === generation.current) setLoading(false)
      }
    },
    [filters.folderId, filters.search, filters.type, filters.availability, searching]
  )

  useEffect(() => {
    void fetchPage(null)
  }, [fetchPage, reloadKey])

  const loadMore = useCallback(() => {
    if (cursor) void fetchPage(cursor)
  }, [cursor, fetchPage])
  const retry = useCallback(() => void fetchPage(null), [fetchPage])

  return { rows, hasMore: cursor !== null, loading, failed, searching, loadMore, retry }
}
