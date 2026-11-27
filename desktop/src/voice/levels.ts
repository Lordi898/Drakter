/**
 * Espectro y forma de onda del micrófono (`input`) y de la voz que suena (`output`), para el modo
 * Jarvis y la boca del personaje. Se leen por fotograma (pull), sin eventos ni React. El análisis es
 * local: nada se graba ni sale del renderer.
 *
 * Un único `AudioContext` y un `AnalyserNode` por toma, creados solo mientras haya demanda
 * (`acquireAudioTaps` o la boca vía `outputLevel.ts`) y una pista. Sin usuarios no hay AudioContext;
 * con la ventana oculta se suspende. Los analizadores no se conectan al destino: no suena nada más
 * ni se añade latencia a la voz, que sigue por su `<audio>` y por WebRTC.
 */
export type AudioTap = 'input' | 'output'

/** Bandas que devuelve `readSpectrum` y muestras de `readWaveform`. */
export const SPECTRUM_BANDS = 64
export const WAVEFORM_SAMPLES = 256
/** Ventana del analizador (la misma que usaba la boca: su nivel no cambia). */
export const TIME_DOMAIN_SAMPLES = 1024

/** Rango de las bandas: lo que importa de una voz. Escala logarítmica, graves primero. */
const BAND_MIN_HZ = 80
const BAND_MAX_HZ = 8000
const MIN_DB = -90
const MAX_DB = -25
const SPECTRUM_SMOOTHING = 0.7

interface TapNode {
  readonly stream: MediaStream
  readonly source: MediaStreamAudioSourceNode
  readonly analyser: AnalyserNode
}

const streams: Record<AudioTap, MediaStream | null> = { input: null, output: null }
const nodes: Record<AudioTap, TapNode | null> = { input: null, output: null }
/** `acquireAudioTaps` pide las dos tomas; la boca solo la de salida. */
let allUsers = 0
let outputOnlyUsers = 0
let ctx: AudioContext | null = null
/** Con el modo flotante activo la ventana se oculta, pero sus niveles siguen haciendo falta (§4.4). */
let awakeHolders = 0
let bandEdges: Uint16Array | null = null // SPECTRUM_BANDS + 1 índices de bin
const freq = new Uint8Array(TIME_DOMAIN_SAMPLES / 2)
const time = new Float32Array(TIME_DOMAIN_SAMPLES)

function wanted(tap: AudioTap): boolean {
  const users = tap === 'output' ? allUsers + outputOnlyUsers : allUsers
  const stream = streams[tap]
  return users > 0 && stream !== null && stream.getAudioTracks().length > 0
}

function onVisibility(): void {
  if (!ctx) return
  if (document.hidden && awakeHolders === 0) void ctx.suspend().catch(() => undefined)
  else void ctx.resume().catch(() => undefined)
}

function computeBandEdges(sampleRate: number): Uint16Array {
  const bins = TIME_DOMAIN_SAMPLES / 2
  const hzPerBin = sampleRate / TIME_DOMAIN_SAMPLES
  const edges = new Uint16Array(SPECTRUM_BANDS + 1)
  const ratio = BAND_MAX_HZ / BAND_MIN_HZ
  for (let i = 0; i <= SPECTRUM_BANDS; i++) {
    const hz = BAND_MIN_HZ * ratio ** (i / SPECTRUM_BANDS)
    edges[i] = Math.min(bins, Math.round(hz / hzPerBin))
  }
  // Cada banda cubre al menos un bin (en graves, varias bandas caen en el mismo).
  for (let i = 1; i <= SPECTRUM_BANDS; i++) if (edges[i]! <= edges[i - 1]!) edges[i] = Math.min(bins, edges[i - 1]! + 1)
  return edges
}

function disconnect(tap: AudioTap): void {
  const node = nodes[tap]
  nodes[tap] = null
  node?.source.disconnect()
}

/** Ajusta el grafo a la demanda y las pistas actuales. Idempotente. */
function reconcile(): void {
  const need = { input: wanted('input'), output: wanted('output') }
  for (const tap of ['input', 'output'] as const) {
    const node = nodes[tap]
    if (node && (!need[tap] || node.stream !== streams[tap])) disconnect(tap)
  }
  if (!need.input && !need.output) {
    const old = ctx
    ctx = null
    bandEdges = null
    if (old) {
      document.removeEventListener('visibilitychange', onVisibility)
      void old.close().catch(() => undefined)
    }
    return
  }
  try {
    if (!ctx) {
      ctx = new AudioContext()
      bandEdges = computeBandEdges(ctx.sampleRate)
      document.addEventListener('visibilitychange', onVisibility)
      onVisibility()
    }
    for (const tap of ['input', 'output'] as const) {
      const stream = streams[tap]
      if (!need[tap] || nodes[tap] || !stream) continue
      const source = ctx.createMediaStreamSource(stream)
      const analyser = ctx.createAnalyser()
      analyser.fftSize = TIME_DOMAIN_SAMPLES
      analyser.minDecibels = MIN_DB
      analyser.maxDecibels = MAX_DB
      analyser.smoothingTimeConstant = SPECTRUM_SMOOTHING
      source.connect(analyser)
      nodes[tap] = { stream, source, analyser }
    }
  } catch {
    // Sin WebAudio no hay visualizadores ni boca que siga al audio; el resto funciona igual.
    disconnect('input')
    disconnect('output')
  }
}

function liveAnalyser(tap: AudioTap): AnalyserNode | null {
  return ctx?.state === 'running' ? (nodes[tap]?.analyser ?? null) : null
}

/**
 * Rellena `out` (longitud `SPECTRUM_BANDS`, 0..255, graves primero). Devuelve `false` si no hay
 * señal; entonces `out` no se toca.
 */
export function readSpectrum(tap: AudioTap, out: Uint8Array): boolean {
  const analyser = liveAnalyser(tap)
  if (!analyser || !bandEdges) return false
  analyser.getByteFrequencyData(freq)
  const n = Math.min(out.length, SPECTRUM_BANDS)
  for (let band = 0; band < n; band++) {
    let peak = 0
    for (let bin = bandEdges[band]!; bin < bandEdges[band + 1]!; bin++) peak = Math.max(peak, freq[bin]!)
    out[band] = peak
  }
  return true
}

/** Rellena `out` (longitud `WAVEFORM_SAMPLES`, -1..1). Devuelve `false` si no hay señal. */
export function readWaveform(tap: AudioTap, out: Float32Array): boolean {
  const analyser = liveAnalyser(tap)
  if (!analyser) return false
  analyser.getFloatTimeDomainData(time)
  // Ventana de ~21 ms reducida a 256 puntos por media (filtro paso bajo sencillo, sin aliasing visible).
  const step = TIME_DOMAIN_SAMPLES / WAVEFORM_SAMPLES
  const n = Math.min(out.length, WAVEFORM_SAMPLES)
  for (let i = 0; i < n; i++) {
    let sum = 0
    for (let k = 0; k < step; k++) sum += time[i * step + k]!
    out[i] = sum / step
  }
  return true
}

/** Cuenta de referencias de los analizadores. Devuelve la baja (idempotente). */
export function acquireAudioTaps(): () => void {
  allUsers += 1
  reconcile()
  let released = false
  return () => {
    if (released) return
    released = true
    allUsers -= 1
    reconcile()
  }
}

/**
 * Impide que el contexto se suspenda con la ventana oculta mientras se mantenga (modo flotante).
 * Devuelve la baja (idempotente).
 */
export function holdAudioAwake(): () => void {
  awakeHolders += 1
  onVisibility()
  let released = false
  return () => {
    if (released) return
    released = true
    awakeHolders -= 1
    onVisibility()
  }
}

/** Pista local del micrófono; `null` al cerrarlo. La llama el cliente de voz. */
export function setInputStream(stream: MediaStream | null): void {
  if (stream === streams.input) return
  streams.input = stream
  reconcile()
}

// ---- Uso interno de `outputLevel.ts` (boca del personaje): misma toma de salida, sin otro contexto ----

/** Pista remota que suena (la voz de Drakter); `null` al cerrar la conexión. */
export function setOutputTapStream(stream: MediaStream | null): void {
  if (stream === streams.output) return
  streams.output = stream
  reconcile()
}

/** Pide solo la toma de salida. Devuelve la baja (idempotente). */
export function acquireOutputTap(): () => void {
  outputOnlyUsers += 1
  reconcile()
  let released = false
  return () => {
    if (released) return
    released = true
    outputOnlyUsers -= 1
    reconcile()
  }
}

/** Ventana cruda de `TIME_DOMAIN_SAMPLES` muestras de una toma. `false` si no hay señal. */
export function readTimeDomain(tap: AudioTap, out: Float32Array<ArrayBuffer>): boolean {
  const analyser = liveAnalyser(tap)
  if (!analyser) return false
  analyser.getFloatTimeDomainData(out)
  return true
}

