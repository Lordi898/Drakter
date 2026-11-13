/**
 * Contrato del cliente de voz del renderer (plan de voz v2 §4.3). CONGELADO por WP0.
 * El cliente WebRTC (WP8a) se registra aquí; la UI (WP8b) lo lee sin depender de él.
 *
 * Micrófono, calculado en el renderer (no viaja en `voice.state`):
 *   mic = !client?.micOpen() ? 'off' : voiceState.mode === 'conversation' ? 'live' : 'standby'
 */
export type MicState = 'off' | 'standby' | 'live'

export interface VoiceClient {
  start(): Promise<void>
  stop(): void
  setMicOpen(open: boolean): Promise<void>
  micOpen(): boolean
  connected(): boolean
  onChange(cb: () => void): () => void
}

let current: VoiceClient | null = null

export function registerVoiceClient(c: VoiceClient): void {
  current = c
}

export function getVoiceClient(): VoiceClient | null {
  return current
}
