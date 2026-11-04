import { useEffect, useState } from 'react'
import { ApiError, describeError } from '@/services/api'
import { searchGlobal, type SearchItem } from './searchApi'

export type SearchState =
  | { readonly status: 'idle' }
  | { readonly status: 'loading' }
  | { readonly status: 'ready'; readonly items: readonly SearchItem[] }
  | { readonly status: 'error'; readonly message: string }
  | { readonly status: 'unavailable'; readonly reason: 'not-connected' | 'backend' }

const DEBOUNCE_MS = 150

function stateForError(error: unknown): SearchState {
  if (error instanceof ApiError && error.code === 'backend_unavailable') {
    return { status: 'unavailable', reason: 'not-connected' }
  }
  if (error instanceof ApiError && error.status === 503) {
    return { status: 'unavailable', reason: 'backend' }
  }
  return { status: 'error', message: describeError(error, 'No se pudo completar la búsqueda') }
}

export function useGlobalSearch(query: string, enabled: boolean): SearchState {
  const [state, setState] = useState<SearchState>({ status: 'idle' })
  const q = query.trim()

  useEffect(() => {
    if (!enabled || q.length < 1) {
      setState({ status: 'idle' })
      return
    }
    setState({ status: 'loading' })
    // El cliente común no admite cancelar: se ignora la respuesta de una consulta vieja.
    let stale = false
    const timer = window.setTimeout(() => {
      searchGlobal(q)
        .then((response) => {
          if (!stale) setState({ status: 'ready', items: response.items })
        })
        .catch((error: unknown) => {
          if (!stale) setState(stateForError(error))
        })
    }, DEBOUNCE_MS)
    return () => {
      stale = true
      window.clearTimeout(timer)
    }
  }, [q, enabled])

  return state
}
