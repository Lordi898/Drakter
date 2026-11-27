import { useSyncExternalStore } from 'react'
import { notify } from '@/services/notify'
import { floatingApi, type FloatingAction, type FloatingState } from './api'

/**
 * Estado del modo flotante en la ventana principal. El dueño es `FloatingController` en main
 * (CONTRACT §4.2); aquí solo se refleja y se pide. Todas las vías de la ventana principal (botones,
 * Ctrl+Shift+F, Ajustes) pasan por `requestFloating`: sin extensión no se activa nada y se abre la
 * ayuda de instalación.
 */
export interface FloatingSnapshot {
  /** `null` hasta la primera respuesta de main. */
  readonly state: FloatingState | null
  readonly helpOpen: boolean
}

let snapshot: FloatingSnapshot = { state: null, helpOpen: false }
const listeners = new Set<() => void>()
let started = false

function set(next: Partial<FloatingSnapshot>): void {
  snapshot = { ...snapshot, ...next }
  listeners.forEach((listener) => listener())
}

/**
 * Main vuelve a publicar el mismo estado no disponible cuando alguien intentó activar el modo desde
 * fuera de la ventana (bandeja) sin extensión (§4.2, paso 1): entonces se abre la ayuda. Un cambio de
 * `companion` (la extensión aparece o desaparece) solo actualiza el estado.
 */
function onState(next: FloatingState): void {
  const previous = snapshot.state
  const attempt = previous !== null && !next.available && previous.companion === next.companion && next.reason !== null
  set({ state: next, helpOpen: snapshot.helpOpen || attempt })
}

/** Arranca la escucha de `floating:state`. Idempotente; lo llama `FloatingHost`. */
export function startFloatingState(): () => void {
  if (started) return () => undefined
  started = true
  const api = floatingApi()
  const stop = api.onState(onState)
  api.getState().then(
    (state) => {
      if (snapshot.state === null) set({ state })
    },
    () => undefined
  )
  return () => {
    stop()
    started = false
  }
}

export function getFloating(): FloatingSnapshot {
  return snapshot
}

export function useFloating(): FloatingSnapshot {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
    () => snapshot
  )
}

export function setFloatingHelpOpen(open: boolean): void {
  set({ helpOpen: open })
}

/** Botones (`toggle`) y Ctrl+Shift+F (`on`). Con `!available` abre la ayuda y no pide nada a main. */
export function requestFloating(action: FloatingAction): void {
  const state = snapshot.state
  if (state && !state.available) {
    set({ helpOpen: true })
    return
  }
  if (state?.busy) return
  floatingApi()
    .set(action)
    .then(
      (next) => {
        set({ state: next, helpOpen: snapshot.helpOpen || !next.available })
      },
      () =>
        notify({
          tone: 'error',
          title: 'No se pudo cambiar el modo flotante',
          body: 'Inténtalo de nuevo. Si sigue fallando, reinicia Drakter.'
        })
    )
}
