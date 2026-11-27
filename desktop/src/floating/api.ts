/**
 * Puente con el modo flotante de main (`window.api.floating`, CONTRACT §4.4). Los tipos copian
 * §4.2 y §4.4 tal cual: cuando D2 publique `FloatingApi` en `electron/shared/bridge.ts` y
 * `FloatingState` en `electron/shared/floating.ts`, el integrador puede sustituir estas
 * declaraciones por imports (la forma es la misma).
 *
 * Sin `window.api.floating` (navegador o una build sin D2) se usa un doble: dice que la extensión
 * falta, así los botones abren la ayuda. `localStorage['drakter:floating-double']='ok'` simula una
 * extensión instalada para ver el resto de estados (solo existe mientras main no exponga la API real).
 */
export type CompanionStatus = 'ok' | 'missing' | 'outdated' | 'denied' | 'unsupported_session'

export interface FloatingState {
  readonly active: boolean
  readonly available: boolean
  readonly companion: CompanionStatus
  readonly busy: 'activating' | 'deactivating' | null
  readonly reason: string | null
}

export type FloatingAction = 'on' | 'off' | 'toggle'

export interface FloatingApi {
  getState(): Promise<FloatingState>
  set(action: FloatingAction): Promise<FloatingState>
  onState(cb: (s: FloatingState) => void): () => void
  onLevelsDemand(cb: (on: boolean) => void): () => void
  reportLevels(out: number, input: number): void
}

export const DOUBLE_KEY = 'drakter:floating-double'

function createDouble(): FloatingApi {
  const simulateOk = globalThis.localStorage?.getItem(DOUBLE_KEY) === 'ok'
  let state: FloatingState = simulateOk
    ? { active: false, available: true, companion: 'ok', busy: null, reason: null }
    : { active: false, available: false, companion: 'missing', busy: null, reason: 'Falta la extensión de GNOME «Drakter Companion».' }
  const stateListeners = new Set<(s: FloatingState) => void>()
  const demandListeners = new Set<(on: boolean) => void>()
  const publish = (next: FloatingState): void => {
    state = next
    stateListeners.forEach((cb) => cb(state))
  }
  return {
    getState: () => Promise.resolve(state),
    set(action) {
      if (!state.available) {
        publish({ ...state })
        return Promise.resolve(state)
      }
      const on = action === 'toggle' ? !state.active : action === 'on'
      if (on === state.active) return Promise.resolve(state)
      publish({ ...state, busy: on ? 'activating' : 'deactivating' })
      return new Promise((resolve) => {
        setTimeout(() => {
          publish({ ...state, active: on, busy: null })
          demandListeners.forEach((cb) => cb(on))
          resolve(state)
        }, 400)
      })
    },
    onState(cb) {
      stateListeners.add(cb)
      return () => stateListeners.delete(cb)
    },
    onLevelsDemand(cb) {
      demandListeners.add(cb)
      return () => demandListeners.delete(cb)
    },
    reportLevels() {
      // Contador para comprobar a mano que el reenvío solo corre con demanda.
      const holder = globalThis as { __floatingDoubleLevels?: number }
      holder.__floatingDoubleLevels = (holder.__floatingDoubleLevels ?? 0) + 1
    }
  }
}

let cached: FloatingApi | null = null

export function floatingApi(): FloatingApi {
  if (cached) return cached
  const real =
    typeof window !== 'undefined' && typeof window.api !== 'undefined'
      ? (window.api as unknown as { readonly floating?: FloatingApi }).floating
      : undefined
  cached = real ?? createDouble()
  return cached
}
