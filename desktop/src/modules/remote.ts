import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, apiRequest, describeError, type ApiRequestInit, type ConfirmationTicket } from '@/services/api'

/**
 * Piezas comunes de los módulos de lectura de Jarvis (memoria, actividad, automejora, copias).
 * Todo va por `apiRequest`; los datos del servidor son dato no confiable.
 */
export type Query = Record<string, string | number | boolean | null | undefined>

export function queryString(params: Query): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') search.set(key, String(value))
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}

export function backend<T>(method: NonNullable<ApiRequestInit['method']>, path: string, body?: unknown): Promise<T> {
  return apiRequest<T>(`/api/v1${path}`, { method, ...(body === undefined ? {} : { body }) })
}

export const errorMessage = (error: unknown): string => describeError(error, 'No se pudo completar la operación.')

export type ConfirmableResult<T> =
  | { readonly status: 'done'; readonly data: T }
  | { readonly status: 'confirmation'; readonly ticket: ConfirmationTicket }

/**
 * Ejecuta una acción destructiva. El backend responde 409 `confirmation_required` y `apiRequest`
 * ya deja la confirmación pendiente en `stores/confirmations`; aquí solo se distingue de un error.
 * Decidir sigue exigiendo el diálogo nativo (`reviewConfirmation`); este módulo nunca aprueba.
 */
export async function runConfirmable<T>(call: () => Promise<T>): Promise<ConfirmableResult<T>> {
  try {
    return { status: 'done', data: await call() }
  } catch (error) {
    if (error instanceof ApiError && error.confirmation) return { status: 'confirmation', ticket: error.confirmation }
    throw error
  }
}

export interface RemoteState<T> {
  readonly data: T | null
  readonly loading: boolean
  readonly error: string | null
  readonly reload: () => void
}

/** Carga un recurso y lo repite cuando cambia `key` o se llama a `reload`; descarta respuestas antiguas. */
export function useRemote<T>(load: () => Promise<T>, key: string, enabled = true): RemoteState<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(enabled)
  const [error, setError] = useState<string | null>(null)
  const [tick, setTick] = useState(0)
  const loadRef = useRef(load)
  loadRef.current = load
  const latest = useRef(0)

  useEffect(() => {
    if (!enabled) {
      setLoading(false)
      return
    }
    const id = ++latest.current
    setLoading(true)
    setError(null)
    loadRef
      .current()
      .then((value) => {
        if (id === latest.current) setData(value)
      })
      .catch((e: unknown) => {
        if (id !== latest.current) return
        setData(null)
        setError(errorMessage(e))
      })
      .finally(() => {
        if (id === latest.current) setLoading(false)
      })
  }, [key, tick, enabled])

  const reload = useCallback(() => setTick((n) => n + 1), [])
  return { data, loading, error, reload }
}
