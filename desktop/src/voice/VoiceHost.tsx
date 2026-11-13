/**
 * Arranca el cliente de voz cuando el enlace con el backend está listo. No pinta nada:
 * lo monta `AppShell` (WP8b). Recargar el renderer solo renegocia; los modelos siguen en `voice/`.
 */
import { useEffect } from 'react'
import { voiceClient } from './webrtcClient'

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

export function VoiceHost(): null {
  useEffect(() => {
    let alive = true
    const apply = (connection: unknown): void => {
      if (!alive || !isRecord(connection)) return
      const state = connection['state']
      // En `restarting` se mantiene: el cliente reintenta solo con backoff.
      if (state === 'ready') void voiceClient.start()
      else if (state === 'failed' || state === 'stopped') voiceClient.stop()
    }
    const unsubscribe = window.api.subscribe('connection', apply)
    void window.api.getConnection().then(apply, () => undefined)
    return () => {
      alive = false
      unsubscribe()
      voiceClient.stop()
    }
  }, [])
  return null
}
