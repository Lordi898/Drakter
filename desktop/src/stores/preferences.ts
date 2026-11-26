import { useSyncExternalStore } from 'react'
import type { UiAppearanceRequested } from '../../../contracts/ts'

export type ThemePreference = 'system' | 'light' | 'dark'

/** Modo de la interfaz. Aquí para que `uiMode.ts` y las preferencias no dependan entre sí. */
export type UiMode = 'drakter' | 'jarvis'
/** Con qué modo arranca la app: siempre Drakter salvo que el usuario elija recordar el último. */
export type JarvisStartup = 'drakter' | 'last'
export type JarvisQuality = 'auto' | 'cine' | 'equilibrado' | 'ahorro'

const JARVIS_QUALITIES: readonly JarvisQuality[] = ['auto', 'cine', 'equilibrado', 'ahorro']

/**
 * Avatar pedido por el evento `ui.appearance` o la herramienta (lista cerrada del contrato). La
 * preferencia `avatarId` es un `string` validado por forma y la resuelve `character/avatars/registry.ts`.
 */
export type AvatarChoice = NonNullable<UiAppearanceRequested['avatar']>
/** Interfaz del modo Jarvis (contrato `ui.appearance`). */
export type JarvisLayoutChoice = NonNullable<UiAppearanceRequested['layout']>

/** Listas en tiempo de ejecución; `satisfies` + la comprobación de abajo las atan al contrato. */
export const AVATAR_CHOICES = [
  'holo-contorno',
  'holo-hilo',
  'holo-busto',
  'holo-orbe',
  'holo-filamento',
  'ascuario',
  'relojero',
  'filamento',
  'none'
] as const satisfies readonly AvatarChoice[]
export const JARVIS_LAYOUT_CHOICES = ['nucleo', 'holomesa', 'visor'] as const satisfies readonly JarvisLayoutChoice[]
// Falla al compilar si el contrato gana un valor que estas listas no tienen.
type Missing<All, Listed> = Exclude<All, Listed> extends never ? true : never
const _avatarsComplete: Missing<AvatarChoice, (typeof AVATAR_CHOICES)[number]> = true
const _layoutsComplete: Missing<JarvisLayoutChoice, (typeof JARVIS_LAYOUT_CHOICES)[number]> = true
void _avatarsComplete
void _layoutsComplete

export const DEFAULT_JARVIS_LAYOUT: JarvisLayoutChoice = 'nucleo'

const isLayoutChoice = (v: unknown): v is JarvisLayoutChoice => (JARVIS_LAYOUT_CHOICES as readonly unknown[]).includes(v)

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
  /** Interfaz del modo Jarvis. La resuelve `jarvis/layouts/registry.ts`. */
  readonly jarvisLayout: JarvisLayoutChoice
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
  avatarId: 'holo-contorno',
  jarvisLayout: DEFAULT_JARVIS_LAYOUT
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
        typeof parsed.avatarId === 'string' && AVATAR_ID.test(parsed.avatarId) ? parsed.avatarId : DEFAULTS.avatarId,
      jarvisLayout: isLayoutChoice(parsed.jarvisLayout) ? parsed.jarvisLayout : DEFAULT_JARVIS_LAYOUT
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
