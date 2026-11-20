import { useSyncExternalStore } from 'react'
import { fetchSettings, saveSetting } from '@/pages/today/requests'
import { describeError } from '@/services/api'
import { notify } from '@/services/notify'
import type { ServerEvent } from '@/services/protocol'
import { subscribeLinkStatus, subscribeResync, subscribeServerEvents } from '@/services/ws'
import { getVoiceClient, type MicState } from '@/voice/contract'

type VoiceStateEvent = Extract<ServerEvent, { type: 'voice.state' }>['payload']

/** Estado de voz del renderer: ajuste del altavoz, snapshot `voice.state` y micrófono derivado. */
export interface VoiceSnapshot {
  readonly ttsEnabled: boolean
  readonly voiceState: VoiceStateEvent | null
  readonly mic: MicState
}

const TTS_KEY = 'voice_tts_enabled'
const WAKE_KEY = 'voice_wake_enabled'

let ttsEnabled = true
let wakeEnabled = true
let voiceState: VoiceStateEvent | null = null
let voiceFault = false
let wasConnected = false
let lastFault: { key: string; at: number } | null = null
const FAULT_DEDUP_MS = 30_000
let unsubscribeClient: (() => void) | null = null
let boundClient: ReturnType<typeof getVoiceClient> = null
let snapshot: VoiceSnapshot = compute()
const listeners = new Set<() => void>()

function computeMic(): MicState {
  if (voiceFault) return 'error'
  const client = getVoiceClient()
  if (!client?.micOpen()) return 'off'
  return voiceState?.mode === 'conversation' ? 'live' : 'standby'
}

function compute(): VoiceSnapshot {
  return { ttsEnabled, voiceState, mic: computeMic() }
}

function refreshSnapshot(): void {
  // El cliente de voz se registra cuando WP8a lo monta: se engancha al primer cambio que vea.
  const client = getVoiceClient()
  if (client !== boundClient) {
    unsubscribeClient?.()
    boundClient = client
    unsubscribeClient = client ? client.onChange(refreshSnapshot) : null
  }
  const next = compute()
  if (
    next.ttsEnabled === snapshot.ttsEnabled &&
    next.voiceState === snapshot.voiceState &&
    next.mic === snapshot.mic
  ) {
    return
  }
  snapshot = next
  listeners.forEach((listener) => listener())
}

const asBool = (value: string | null | undefined, fallback: boolean): boolean =>
  value == null ? fallback : value === 'true'

async function loadSettings(): Promise<void> {
  try {
    const { items } = await fetchSettings()
    ttsEnabled = asBool(items.find((i) => i.key === TTS_KEY)?.value, true)
    wakeEnabled = asBool(items.find((i) => i.key === WAKE_KEY)?.value, true)
    refreshSnapshot()
  } catch {
    console.warn('No se pudieron leer los ajustes de voz.')
  }
}

const STAGE_LABEL: Record<string, string> = {
  transport: 'la conexión de audio',
  stt: 'el reconocimiento de voz',
  turn: 'el turno de voz',
  tts: 'la síntesis de voz',
  ipc: 'el servicio de voz',
  wake: 'la palabra de activación'
}

const CODE_TEXT: Record<string, string> = {
  stt_unavailable: 'No está disponible el reconocimiento de voz.',
  tts_unavailable: 'No está disponible la síntesis de voz.',
  models_missing: 'Faltan los modelos de voz.',
  pipeline_build_failed: 'No se pudo preparar la voz.',
  pipeline_failed: 'La voz se interrumpió.',
  service_failed: 'El servicio de voz falló.',
  stt_fallback: 'Se usa el reconocimiento de voz de respaldo.'
}

/** Texto del aviso: el `message` del backend si viene; si no, uno según el código. */
function faultText(code: string, stage: string, message?: string): string {
  return message?.trim() || CODE_TEXT[code] || `Fallo en ${STAGE_LABEL[stage] ?? 'la voz'}.`
}

/** Un aviso por fallo: el mismo error repetido dentro de la ventana no vuelve a mostrarse. */
function reportFault(key: string, title: string, body?: string): void {
  voiceFault = true
  const now = Date.now()
  const repeated = lastFault?.key === key && now - lastFault.at < FAULT_DEDUP_MS
  lastFault = { key, at: now }
  refreshSnapshot()
  if (!repeated) notify({ tone: 'error', title, ...(body === undefined ? {} : { body }) })
}

subscribeServerEvents((event) => {
  if (event.type === 'voice.error') {
    const { code, stage } = event.payload
    reportFault(`error|${stage}|${code}`, 'Problema con la voz', faultText(code, stage))
    return
  }
  if (event.type !== 'voice.state') return
  voiceState = event.payload
  const connected = event.payload.connected
  if (connected) {
    voiceFault = false
    lastFault = null
  } else if (wasConnected) {
    reportFault('disconnected', 'La voz se desconectó', 'Drakter intentará reconectar.')
  }
  wasConnected = connected
  refreshSnapshot()
})
subscribeResync(() => void loadSettings())
subscribeLinkStatus((status) => {
  if (status === 'open') void loadSettings()
})

/** Guarda `voice_tts_enabled` de forma optimista; si falla, vuelve atrás y avisa. */
export async function setTtsEnabled(next: boolean): Promise<void> {
  const previous = ttsEnabled
  ttsEnabled = next
  refreshSnapshot()
  try {
    await saveSetting(TTS_KEY, String(next))
  } catch (error) {
    ttsEnabled = previous
    refreshSnapshot()
    notify({ tone: 'error', title: 'No se pudo cambiar la lectura en voz alta', body: describeError(error, 'Inténtalo de nuevo.') })
  }
}

/** Valor leído de `voice_wake_enabled` (para la sección Voz de Configuración). */
export function getWakeEnabled(): boolean {
  return wakeEnabled
}

export async function setWakeEnabled(next: boolean): Promise<void> {
  const previous = wakeEnabled
  wakeEnabled = next
  try {
    await saveSetting(WAKE_KEY, String(next))
  } catch (error) {
    wakeEnabled = previous
    throw error
  }
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  refreshSnapshot() // por si el cliente de voz se registró después de cargar el módulo
  return () => {
    listeners.delete(listener)
  }
}

export function useVoice(): VoiceSnapshot {
  return useSyncExternalStore(subscribe, () => snapshot)
}
