/**
 * Puente con el modo flotante de main (`window.api.floating`, CONTRACT §4.4). Los tipos son los de
 * `electron/shared`. Sin `window.api` (el renderer abierto en un navegador, sin Electron) se usa un
 * sustituto que dice que la extensión falta, así los botones abren la ayuda.
 */
import type { FloatingApi, FloatingState } from '../../electron/shared/bridge'

export type { CompanionStatus, FloatingAction, FloatingApi, FloatingState } from '../../electron/shared/bridge'

function createMissing(): FloatingApi {
  const state: FloatingState = {
    active: false,
    available: false,
    companion: 'missing',
    busy: null,
    reason: 'Falta la extensión de GNOME «Drakter Companion».'
  }
  const listeners = new Set<(s: FloatingState) => void>()
  return {
    getState: () => Promise.resolve(state),
    set() {
      listeners.forEach((cb) => cb(state)) // mismo estado no disponible: la interfaz abre la ayuda
      return Promise.resolve(state)
    },
    onState(cb) {
      listeners.add(cb)
      return () => listeners.delete(cb)
    },
    onLevelsDemand: () => () => undefined,
    reportLevels: () => undefined
  }
}

let cached: FloatingApi | null = null

export function floatingApi(): FloatingApi {
  if (cached) return cached
  cached = typeof window !== 'undefined' && typeof window.api !== 'undefined' ? window.api.floating : createMissing()
  return cached
}
