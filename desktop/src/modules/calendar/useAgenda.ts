import { useCallback, useEffect, useState } from 'react'
import { fetchAgenda, fetchOverlaps } from './api'
import type { AgendaItem, OverlapGroup } from './types'
import { errorText, isBackendUnavailable } from './workspaceApi'

export type AgendaState =
  | { readonly status: 'loading' }
  | { readonly status: 'unavailable' }
  | { readonly status: 'error'; readonly message: string }
  | { readonly status: 'ready'; readonly items: readonly AgendaItem[]; readonly truncated: boolean; readonly overlapIds: ReadonlySet<string> }

/** Carga la agenda y los solapes de [from, to) en `timezone`. `reload` repite la consulta. */
export function useAgenda(from: string, to: string, timezone: string): { state: AgendaState; reload: () => void } {
  const [state, setState] = useState<AgendaState>({ status: 'loading' })
  const [tick, setTick] = useState(0)
  const reload = useCallback(() => setTick((t) => t + 1), [])

  useEffect(() => {
    let active = true
    setState({ status: 'loading' })
    const overlaps: Promise<OverlapGroup[]> = fetchOverlaps(from, to, timezone).catch(() => [])
    Promise.all([fetchAgenda(from, to, timezone), overlaps])
      .then(([agenda, groups]) => {
        if (!active) return
        const overlapIds = new Set<string>(groups.flatMap((g) => [...g.items]))
        setState({ status: 'ready', items: agenda.items, truncated: agenda.truncated, overlapIds })
      })
      .catch((error: unknown) => {
        if (!active) return
        setState(isBackendUnavailable(error) ? { status: 'unavailable' } : { status: 'error', message: errorText(error) })
      })
    return () => {
      active = false
    }
  }, [from, to, timezone, tick])

  return { state, reload }
}
