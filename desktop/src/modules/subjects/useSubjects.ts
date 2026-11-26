import { useCallback, useEffect, useState } from 'react'
import { errorText } from '@/modules/calendar/workspaceApi'
import { getTimetable, listSubjects } from './api'
import type { Subject, TimetableEntry } from './types'

export type SubjectsLoad =
  | { readonly status: 'loading' }
  | { readonly status: 'error'; readonly error: unknown }
  | { readonly status: 'ready'; readonly subjects: readonly Subject[] }

/** Asignaturas; al recargar conserva las anteriores hasta que llega la respuesta. */
export function useSubjects(includeArchived: boolean): { readonly load: SubjectsLoad; readonly reload: () => void } {
  const [load, setLoad] = useState<SubjectsLoad>({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    listSubjects(includeArchived).then(
      (page) => {
        if (!cancelled) setLoad({ status: 'ready', subjects: page.items })
      },
      (error: unknown) => {
        if (!cancelled) setLoad({ status: 'error', error })
      }
    )
    return () => {
      cancelled = true
    }
  }, [includeArchived, attempt])

  const reload = useCallback(() => setAttempt((n) => n + 1), [])
  return { load, reload }
}

/** Horario semanal de la semana que contiene `on` (YYYY-MM-DD). `reloadKey` fuerza otra carga. */
export function useTimetable(
  on: string,
  reloadKey = 0
): {
  readonly entries: readonly TimetableEntry[] | null
  readonly error: string | null
  readonly reload: () => void
} {
  const [entries, setEntries] = useState<readonly TimetableEntry[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    setError(null)
    getTimetable(on).then(
      (timetable) => {
        if (!cancelled) setEntries(timetable.entries)
      },
      (e: unknown) => {
        if (!cancelled) setError(errorText(e))
      }
    )
    return () => {
      cancelled = true
    }
  }, [on, reloadKey, attempt])

  const reload = useCallback(() => setAttempt((n) => n + 1), [])
  return { entries, error, reload }
}
