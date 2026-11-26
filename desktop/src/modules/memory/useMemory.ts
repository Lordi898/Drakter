import { useCallback, useState } from 'react'
import { useRemote, type RemoteState } from '../remote'
import { approveMemory, forgetMemory, getMemoryStatus, listConflicts, listMemories, rejectMemory, resolveConflict, searchMemories } from './api'
import type { MemoryBackendStatus, MemoryConflict, MemoryHit, MemoryListParams, MemoryPage } from './types'

export function useMemories(params: MemoryListParams = {}): RemoteState<MemoryPage> {
  return useRemote(() => listMemories(params), JSON.stringify(params))
}

export function useMemoryStatus(): RemoteState<MemoryBackendStatus> {
  return useRemote(getMemoryStatus, 'status')
}

export function useMemoryConflicts(openOnly = true): RemoteState<readonly MemoryConflict[]> {
  return useRemote(() => listConflicts(openOnly), String(openOnly))
}

/** Búsqueda por texto (solo L0). Con texto vacío no pide nada. */
export function useMemorySearch(text: string, limit = 8): RemoteState<readonly MemoryHit[]> {
  const query = text.trim()
  return useRemote(() => searchMemories(query, { limit }), `${query}|${limit}`, query !== '')
}

/**
 * Acciones sobre un recuerdo. `approve` y `forget` devuelven `confirmation` cuando el backend exige
 * confirmar: ya queda pendiente en `stores/confirmations` y se decide allí con el diálogo nativo.
 */
export function useMemoryActions(onChanged?: () => void) {
  const [busy, setBusy] = useState(false)
  const run = useCallback(
    async <T,>(call: () => Promise<T>): Promise<T> => {
      setBusy(true)
      try {
        const result = await call()
        onChanged?.()
        return result
      } finally {
        setBusy(false)
      }
    },
    [onChanged]
  )
  return {
    busy,
    approve: (id: string) => run(() => approveMemory(id)),
    reject: (id: string) => run(() => rejectMemory(id)),
    forget: (id: string) => run(() => forgetMemory(id)),
    resolve: (conflictId: string, kept: string | null) => run(() => resolveConflict(conflictId, kept))
  }
}
