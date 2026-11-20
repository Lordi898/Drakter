import { useSyncExternalStore } from 'react'

export type ThemePreference = 'system' | 'light' | 'dark'

export interface Preferences {
  readonly theme: ThemePreference
  readonly reduceMotion: boolean
  readonly contextPanelOpen: boolean
  readonly desktopNotifications: boolean
  /** `deviceId` del micrófono elegido; vacío = predeterminado del sistema. */
  readonly micDeviceId: string
}

const STORAGE_KEY = 'drakter.preferences.v1'
const DEFAULTS: Preferences = {
  theme: 'system',
  reduceMotion: false,
  contextPanelOpen: true,
  desktopNotifications: true,
  micDeviceId: ''
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
      micDeviceId: typeof parsed.micDeviceId === 'string' ? parsed.micDeviceId : ''
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
