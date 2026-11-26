/**
 * Espectro y forma de onda del micrófono (`input`) y de la voz que suena (`output`), para el modo
 * Jarvis. Se leen por fotograma (pull), sin eventos ni React. El análisis es local: nada se graba
 * ni sale del renderer. Sin usuarios (`acquireAudioTaps`) no hay AudioContext.
 *
 * CONTRATO congelado en J0; esto es un stub (siempre «sin señal»). La implementación es de W7:
 * compartirá el `AnalyserNode` de salida con `outputLevel.ts` y `webrtcClient` llamará a
 * `setInputStream` al abrir el micrófono.
 */
export type AudioTap = 'input' | 'output'

/** Bandas que devuelve `readSpectrum` y muestras de `readWaveform`. */
export const SPECTRUM_BANDS = 64
export const WAVEFORM_SAMPLES = 256

let inputStream: MediaStream | null = null
let users = 0

/**
 * Rellena `out` (longitud `SPECTRUM_BANDS`, 0..255, graves primero). Devuelve `false` si no hay
 * señal; entonces `out` no se toca.
 */
export function readSpectrum(tap: AudioTap, out: Uint8Array): boolean {
  void tap
  void out
  return false
}

/** Rellena `out` (longitud `WAVEFORM_SAMPLES`, -1..1). Devuelve `false` si no hay señal. */
export function readWaveform(tap: AudioTap, out: Float32Array): boolean {
  void tap
  void out
  return false
}

/** Cuenta de referencias de los analizadores. Devuelve la baja (idempotente). */
export function acquireAudioTaps(): () => void {
  users += 1
  let released = false
  return () => {
    if (released) return
    released = true
    users -= 1
  }
}

/** Pista local del micrófono; `null` al cerrarlo. La llama el cliente de voz. */
export function setInputStream(stream: MediaStream | null): void {
  inputStream = stream
  void inputStream
  void users
}
