import {
  getPreferences,
  updatePreferences,
  type AvatarChoice,
  type JarvisLayoutChoice
} from '@/stores/preferences'
import { getUiMode, requestUiMode, type UiModeSource } from '@/stores/uiMode'

/**
 * Apariencia: avatar (en los dos modos) e interfaz del modo Jarvis. Única puerta para cambiarlas
 * desde cualquier vía (Ajustes, selector del HUD, Ctrl+K, `ui.appearance` de la voz o del agente).
 * Se guarda en las preferencias locales; nadie más guarda estado (el backend tampoco).
 */
export interface AppearanceRequest {
  readonly avatar?: AvatarChoice | null
  readonly layout?: JarvisLayoutChoice | null
}

export type AppearanceOutcome = 'applied' | 'unchanged' | 'rate_limited'

/** Igual que el modo: una orden repetida (voz y agente a la vez) no hace parpadear la interfaz. */
const MIN_INTERVAL_MS = 1000
let lastChangeAt = Number.NEGATIVE_INFINITY

/**
 * Aplica la petición. Pedir una interfaz Jarvis estando en Drakter también abre el modo Jarvis
 * («pon la interfaz visor» es querer verla); cambiar de avatar no cambia de modo.
 * Las vías directas del usuario (Ajustes, selector) pasan `source: 'button'` y no tienen límite.
 */
export function requestAppearance(request: AppearanceRequest, source: UiModeSource): AppearanceOutcome {
  const current = getPreferences()
  const patch: { avatarId?: string; jarvisLayout?: JarvisLayoutChoice } = {}
  if (request.avatar && request.avatar !== current.avatarId) patch.avatarId = request.avatar
  if (request.layout && request.layout !== current.jarvisLayout) patch.jarvisLayout = request.layout
  const wantsJarvis = Boolean(request.layout) && getUiMode().target !== 'jarvis'
  if (Object.keys(patch).length === 0 && !wantsJarvis) return 'unchanged'

  const now = performance.now()
  const limited = source !== 'button' && source !== 'startup'
  if (limited && now - lastChangeAt < MIN_INTERVAL_MS) return 'rate_limited'
  lastChangeAt = now

  if (Object.keys(patch).length > 0) updatePreferences(patch)
  if (wantsJarvis) requestUiMode('jarvis', source)
  return 'applied'
}
