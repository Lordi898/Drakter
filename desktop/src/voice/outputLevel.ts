/**
 * Nivel real del audio que suena (pista remota de WebRTC), para mover la boca del personaje.
 * Sin suscriptores no hay AudioContext ni temporizador: el coste fuera del habla es cero.
 * El analizador no se conecta al destino: el sonido sigue saliendo solo por el <audio> del cliente.
 */

const FRAME_MS = 33 // ~30 fps
const GATE = 0.012 // RMS por debajo del cual se considera silencio
const FULL = 0.16 // RMS que abre la boca del todo
const ATTACK = 0.65
const RELEASE = 0.3

type Listener = (level: number) => void

const listeners = new Set<Listener>()
let stream: MediaStream | null = null
let ctx: AudioContext | null = null
let source: MediaStreamAudioSourceNode | null = null
let analyser: AnalyserNode | null = null
let buffer: Float32Array<ArrayBuffer> | null = null
let timer: ReturnType<typeof setInterval> | null = null
let smoothed = 0

/** Nivel 0..1 de una ventana de muestras: RMS con umbral y curva perceptual. */
export function levelFromSamples(samples: Float32Array): number {
  let sum = 0
  for (let i = 0; i < samples.length; i++) sum += samples[i]! * samples[i]!
  const rms = Math.sqrt(sum / Math.max(1, samples.length))
  if (rms <= GATE) return 0
  return Math.sqrt(Math.min(1, (rms - GATE) / (FULL - GATE)))
}

function sample(): void {
  if (!analyser || !buffer || document.hidden) return
  analyser.getFloatTimeDomainData(buffer)
  const raw = levelFromSamples(buffer)
  smoothed += (raw - smoothed) * (raw > smoothed ? ATTACK : RELEASE)
  if (smoothed < 0.01) smoothed = 0
  for (const listener of listeners) listener(smoothed)
}

function stop(): void {
  if (timer !== null) clearInterval(timer)
  timer = null
  source?.disconnect()
  source = null
  analyser = null
  buffer = null
  const old = ctx
  ctx = null
  if (old) void old.close().catch(() => undefined)
  smoothed = 0
}

function start(): void {
  stop()
  if (!stream || stream.getAudioTracks().length === 0 || listeners.size === 0) return
  try {
    ctx = new AudioContext()
    source = ctx.createMediaStreamSource(stream)
    analyser = ctx.createAnalyser()
    analyser.fftSize = 1024
    buffer = new Float32Array(analyser.fftSize)
    source.connect(analyser)
    void ctx.resume().catch(() => undefined)
    timer = setInterval(sample, FRAME_MS)
  } catch {
    stop() // sin WebAudio la boca simplemente no sigue al audio
  }
}

/** El cliente de voz avisa de la pista remota actual (o `null` al cerrar la conexión). */
export function setOutputStream(next: MediaStream | null): void {
  if (next === stream) return
  stream = next
  if (listeners.size > 0) start()
}

/** Recibe el nivel (0..1, ~30 fps) mientras haya al menos un suscriptor. Devuelve la baja. */
export function subscribeOutputLevel(listener: Listener): () => void {
  listeners.add(listener)
  if (listeners.size === 1) start()
  return () => {
    listeners.delete(listener)
    if (listeners.size === 0) stop()
  }
}
