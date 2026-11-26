import { lazy, Suspense, useEffect, type ComponentType } from 'react'
import { useGlobalShortcuts } from '@/app/useGlobalShortcuts'
import { startNotificationFeed } from '@/modules/notifications'
import { subscribeServerEvents } from '@/services/ws'
import { requestAppearance } from '@/stores/appearance'
import { getPreferences } from '@/stores/preferences'
import { requestUiMode } from '@/stores/uiMode'

// VoiceHost (WP8a) va en su propio chunk; si la build no lo trae, el glob queda vacío.
const voiceHostModules = import.meta.glob<{ VoiceHost: ComponentType }>('../voice/VoiceHost.tsx')
const voiceHostLoader = Object.values(voiceHostModules)[0]
const VoiceHost = voiceHostLoader
  ? lazy(async () => ({ default: (await voiceHostLoader()).VoiceHost }))
  : null

/** `ui.mode`/`ui.appearance` (voz o agente) y la bandeja piden cambios; los stores deciden si proceden. */
function useUiModeRequests(): void {
  useEffect(
    () =>
      subscribeServerEvents((event) => {
        if (event.type === 'ui.mode') requestUiMode(event.payload.mode, event.payload.source)
        else if (event.type === 'ui.appearance')
          requestAppearance({ avatar: event.payload.avatar, layout: event.payload.layout }, event.payload.source)
      }),
    []
  )

  useEffect(() => {
    if (typeof window.api === 'undefined') return
    return window.api.ui.onModeToggle(() => requestUiMode('toggle', 'tray'))
  }, [])

  // Siempre se arranca en Drakter; solo si el usuario lo eligió, se vuelve al último modo tras el primer pintado.
  useEffect(() => {
    const { jarvisStartup, lastUiMode } = getPreferences()
    if (jarvisStartup !== 'last' || lastUiMode !== 'jarvis') return
    const frame = requestAnimationFrame(() => requestUiMode('jarvis', 'startup'))
    return () => cancelAnimationFrame(frame)
  }, [])
}

/**
 * Lo que vive mientras la app está abierta, sea cual sea el modo de interfaz: la voz (desmontarla
 * cortaría WebRTC), el feed de notificaciones, los atajos comunes y las peticiones de cambio de modo.
 * No pinta nada.
 */
export function SessionHosts() {
  useGlobalShortcuts()
  useUiModeRequests()
  useEffect(() => startNotificationFeed(), [])

  return VoiceHost ? (
    <Suspense fallback={null}>
      <VoiceHost />
    </Suspense>
  ) : null
}
