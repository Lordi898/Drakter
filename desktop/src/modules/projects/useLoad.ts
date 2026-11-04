import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '../tasks/client'

export interface LoadError {
  readonly code: string
  readonly message: string
}

export interface LoadState<T> {
  readonly data: T | null
  readonly loading: boolean
  readonly error: LoadError | null
  readonly reload: () => void
}

export function toLoadError(error: unknown): LoadError {
  if (error instanceof ApiError) return { code: error.code, message: error.message }
  return {
    code: 'unexpected_error',
    message: error instanceof Error ? error.message : 'No se pudo completar la operación.'
  }
}

/** Carga un recurso y lo vuelve a pedir cuando cambia `key` o se llama a `reload`. Sin datos de relleno. */
export function useLoad<T>(load: () => Promise<T>, key: string): LoadState<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<LoadError | null>(null)
  const [tick, setTick] = useState(0)
  const loadRef = useRef(load)
  loadRef.current = load
  const latest = useRef(0)

  useEffect(() => {
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
        setError(toLoadError(e))
      })
      .finally(() => {
        if (id === latest.current) setLoading(false)
      })
  }, [key, tick])

  const reload = useCallback(() => setTick((n) => n + 1), [])
  return { data, loading, error, reload }
}
