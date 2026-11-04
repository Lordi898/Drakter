import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from './client'
import { getTask, listTasks } from './api'
import type { Task, TaskDetail, TaskListParams } from './types'

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  return error instanceof Error ? error.message : 'No se pudo completar la operación.'
}

export interface TasksState {
  readonly items: readonly Task[]
  readonly loading: boolean
  readonly loadingMore: boolean
  readonly error: string | null
  readonly hasMore: boolean
  readonly loadMore: () => void
  readonly reload: () => void
}

/** Lista paginada por `next_cursor`. Una respuesta de una petición anterior se descarta. */
export function useTasks(params: Omit<TaskListParams, 'cursor'>): TasksState {
  const [items, setItems] = useState<readonly Task[]>([])
  const [cursor, setCursor] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tick, setTick] = useState(0)
  const latest = useRef(0)
  const key = JSON.stringify(params)

  useEffect(() => {
    const id = ++latest.current
    setLoading(true)
    setError(null)
    listTasks(JSON.parse(key) as TaskListParams)
      .then((page) => {
        if (id !== latest.current) return
        setItems(page.items)
        setCursor(page.next_cursor)
      })
      .catch((e: unknown) => {
        if (id !== latest.current) return
        setItems([])
        setCursor(null)
        setError(errorMessage(e))
      })
      .finally(() => {
        if (id === latest.current) setLoading(false)
      })
  }, [key, tick])

  const loadMore = useCallback(() => {
    if (cursor === null) return
    const id = ++latest.current
    setLoadingMore(true)
    listTasks({ ...(JSON.parse(key) as TaskListParams), cursor })
      .then((page) => {
        if (id !== latest.current) return
        setItems((current) => [...current, ...page.items])
        setCursor(page.next_cursor)
      })
      .catch((e: unknown) => {
        if (id === latest.current) setError(errorMessage(e))
      })
      .finally(() => {
        if (id === latest.current) setLoadingMore(false)
      })
  }, [cursor, key])

  const reload = useCallback(() => setTick((n) => n + 1), [])

  return { items, loading, loadingMore, error, hasMore: cursor !== null, loadMore, reload }
}

export interface TaskDetailState {
  readonly detail: TaskDetail | null
  readonly loading: boolean
  readonly error: string | null
}

/** Detalle de una tarea; se vuelve a pedir cuando cambia `id` o `version`. */
export function useTaskDetail(id: string | null, version: number): TaskDetailState {
  const [detail, setDetail] = useState<TaskDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const latest = useRef(0)

  useEffect(() => {
    const request = ++latest.current
    if (id === null) {
      setDetail(null)
      setError(null)
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    getTask(id)
      .then((value) => {
        if (request === latest.current) setDetail(value)
      })
      .catch((e: unknown) => {
        if (request !== latest.current) return
        setDetail(null)
        setError(errorMessage(e))
      })
      .finally(() => {
        if (request === latest.current) setLoading(false)
      })
  }, [id, version])

  return { detail: detail !== null && detail.id === id ? detail : null, loading, error }
}
