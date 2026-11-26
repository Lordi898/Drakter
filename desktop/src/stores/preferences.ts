import { useSyncExternalStore } from 'react'

export type ThemePreference = 'system' | 'light' | 'dark'

/** Modo de la interfaz. Aquí para que `uiMode.ts` y las preferencias no dependan entre sí. */
export type UiMode = 'drakter' | 'jarvis'
/** Con qué modo arranca la app: siempre Drakter salvo que el usuario elija recordar el último. */
export type JarvisStartup = 'drakter' | 'last'
export type JarvisQuality = 'auto' | 'cine' | 'equilibrado' | 'ahorro'

const JARVIS_QUALITIES: readonly JarvisQuality[] = ['auto', 'cine', 'equilibrado', 'ahorro']

export interface Preferences {
  readonly theme: ThemePreference
  readonly reduceMotion: boolean
  readonly contextPanelOpen: boolean
  readonly desktopNotifications: boolean
  /** `deviceId` del micrófono elegido; vacío = predeterminado del sistema. */
  readonly micDeviceId: string
  /** `deviceId` de la salida elegida; vacío = predeterminada del sistema. */
  readonly outputDeviceId: string
  /** Modo al arrancar. Por defecto, siempre Drakter. */
  readonly jarvisStartup: JarvisStartup
  /** Último modo usado; solo se escribe y se lee con `jarvisStartup === 'last'`. */
  readonly lastUiMode: UiMode
  /** Nivel de calidad del modo Jarvis; `auto` lo elige según la GPU. */
  readonly jarvisQuality: JarvisQuality
  /**
   * Avatar 3D elegido (`character/avatars/registry.ts`): un id como `holo-orbe`, o `none` para el
   * personaje clásico. Aquí solo se valida la forma; un id desconocido o no portado se resuelve a «ninguno».
   */
  readonly avatarId: string
}

const AVATAR_ID = /^[a-z0-9-]{1,40}$/

const STORAGE_KEY = 'drakter.preferences.v1'
const DEFAULTS: Preferences = {
  theme: 'system',
  reduceMotion: false,
  contextPanelOpen: true,
  desktopNotifications: true,
  micDeviceId: '',
  outputDeviceId: '',
  jarvisStartup: 'drakter',
  lastUiMode: 'drakter',
  jarvisQuality: 'auto',
  avatarId: 'holo-contorno'
}

function load(): Preferences {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULTS
    const parsed = JSON.parse(raw) as Partial<Preferences>
    return {
      theme: parsed.theme === 'light' || parsed.theme === 'dark' ? parsed.theme : 'system',
      reduceMotion: parsed.reduceMotion === true,
      contextPanelOpen: parsed.contextPanelOpen !== false,
      desktopNotifications: parsed.desktopNotifications !== false,
      micDeviceId: typeof parsed.micDeviceId === 'string' ? parsed.micDeviceId : '',
      outputDeviceId: typeof parsed.outputDeviceId === 'string' ? parsed.outputDeviceId : '',
      jarvisStartup: parsed.jarvisStartup === 'last' ? 'last' : 'drakter',
      lastUiMode: parsed.lastUiMode === 'jarvis' ? 'jarvis' : 'drakter',
      jarvisQuality: JARVIS_QUALITIES.includes(parsed.jarvisQuality as JarvisQuality)
        ? (parsed.jarvisQuality as JarvisQuality)
        : 'auto',
      avatarId:
        typeof parsed.avatarId === 'string' && AVATAR_ID.test(parsed.avatarId) ? parsed.avatarId : DEFAULTS.avatarId
    }
  } catch {
    return DEFAULTS
  }
}

let current = load()
const listeners = new Set<() => void>()

export function getPreferences(): Preferences {
  return current
}

export function updatePreferences(patch: Partial<Preferences>): void {
  current = { ...current, ...patch }
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(current))
  } catch {
    // Sin almacenamiento la preferencia dura hasta cerrar la app.
  }
  listeners.forEach((listener) => listener())
}

export const subscribePreferences = subscribe

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function usePreferences(): Preferences {
  return useSyncExternalStore(subscribe, getPreferences)
}
