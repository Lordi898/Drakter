/**
 * Nivel real del audio que suena (pista remota de WebRTC), para mover la boca del personaje.
 * Usa la toma de salida de `levels.ts` (el mismo AudioContext y el mismo analizador que los
 * visualizadores de Jarvis). Sin suscriptores no pide la toma ni hay temporizador.
 */
import { acquireOutputTap, readTimeDomain, setOutputTapStream, TIME_DOMAIN_SAMPLES } from './levels'

const FRAME_MS = 33 // ~30 fps
const GATE = 0.012 // RMS por debajo del cual se considera silencio
const FULL = 0.16 // RMS que abre la boca del todo
const ATTACK = 0.65
const RELEASE = 0.3

type Listener = (level: number) => void

const listeners = new Set<Listener>()
const buffer = new Float32Array(TIME_DOMAIN_SAMPLES)
let release: (() => void) | null = null
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
  if (document.hidden || !readTimeDomain('output', buffer)) return
  const raw = levelFromSamples(buffer)
  smoothed += (raw - smoothed) * (raw > smoothed ? ATTACK : RELEASE)
  if (smoothed < 0.01) smoothed = 0
  for (const listener of listeners) listener(smoothed)
}

function stop(): void {
  if (timer !== null) clearInterval(timer)
  timer = null
  release?.()
  release = null
  smoothed = 0
}

function start(): void {
  stop()
  release = acquireOutputTap()
  timer = setInterval(sample, FRAME_MS)
}

/** El cliente de voz avisa de la pista remota actual (o `null` al cerrar la conexión). */
export function setOutputStream(next: MediaStream | null): void {
  setOutputTapStream(next)
  smoothed = 0
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
