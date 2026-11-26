/**
 * Un tema de `JarvisData` como instantánea estable: solo carga si está pedido, conserva el último
 * dato bueno ante fallos y recargas, y se repite tras un resync del enlace. La identidad del objeto
 * solo cambia cuando cambia su contenido: las capas del Stage pueden comparar por referencia.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ApiError, describeError } from '@/services/api'
import { subscribeResync } from '@/services/ws'
import type { Snapshot, SnapshotStatus } from './types'

interface State<T> {
  readonly status: SnapshotStatus
  readonly data: T | null
  readonly error: string | null
  readonly updatedAt: number | null
}

const INITIAL: State<never> = { status: 'loading', data: null, error: null, updatedAt: null }

/** Sin respuesta del servicio local (`ApiError.status === 0`): no es un fallo de la petición. */
const isOffline = (error: unknown): boolean => error instanceof ApiError && error.status === 0

/** `key` resume todo lo que cambia la petición (fechas, ids…); `load` puede cambiar en cada render. */
export function useTopic<T>(load: () => Promise<T>, key: string, enabled: boolean): Snapshot<T> {
  const [state, setState] = useState<State<T>>(INITIAL)
  const [tick, setTick] = useState(0)
  const loadRef = useRef(load)
  loadRef.current = load
  const latest = useRef(0)

  useEffect(() => {
    if (!enabled) return
    const id = ++latest.current
    setState((s) => (s.status === 'loading' && s.error === null ? s : { ...s, status: 'loading', error: null }))
    loadRef
      .current()
      .then((data) => {
        if (id === latest.current) setState({ status: 'ready', data, error: null, updatedAt: Date.now() })
      })
      .catch((error: unknown) => {
        if (id !== latest.current) return
        const offline = isOffline(error)
        setState((s) => ({
          ...s,
          status: offline ? 'offline' : 'error',
          error: offline ? 'Sin conexión con el servicio local.' : describeError(error, 'No se pudieron cargar los datos.')
        }))
      })
    return () => {
      // Una respuesta que llega tras desmontar o cambiar de clave se descarta.
      latest.current++
    }
  }, [key, tick, enabled])

  const reload = useCallback(() => setTick((n) => n + 1), [])

  useEffect(() => (enabled ? subscribeResync(reload) : undefined), [enabled, reload])

  return useMemo(() => ({ ...state, reload }), [state, reload])
}

/**
 * Tema derivado de otros: el peor estado manda y `data` sale de `derive` en cuanto alguna fuente tiene
 * datos (si una falla, el resultado es parcial y el estado lo dice).
 */
export function useDerived<T>(sources: readonly Snapshot<unknown>[], derive: () => T | null, deps: readonly unknown[]): Snapshot<T> {
  const statuses = sources.map((s) => `${s.status}:${s.error ?? ''}`).join('|')
  const reloadAll = useRef<() => void>(() => undefined)
  reloadAll.current = () => sources.forEach((s) => s.reload())
  const reload = useCallback(() => reloadAll.current(), [])
  return useMemo(() => {
    const failed = sources.find((s) => s.status === 'offline') ?? sources.find((s) => s.status === 'error')
    const loading = sources.some((s) => s.status === 'loading')
    const status: SnapshotStatus = failed?.status ?? (loading ? 'loading' : 'ready')
    const ready = sources.some((s) => s.data !== null)
    const times = sources.map((s) => s.updatedAt ?? 0)
    return {
      status,
      data: ready ? derive() : null,
      error: failed?.error ?? null,
      updatedAt: ready ? Math.max(...times) : null,
      reload
    }
  }, [statuses, reload, ...deps])
}
