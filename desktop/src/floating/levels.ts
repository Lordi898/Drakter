/**
 * Reenvío de niveles de voz a la página flotante (CONTRACT §4.4): ~30 Hz y SOLO mientras main pida
 * (`floating:levels-demand`). `out` es la voz que suena y `in` el micrófono, ambos 0..1, con la misma
 * curva que la boca del personaje (`outputLevel.ts`). Se usa un temporizador y no
 * `requestAnimationFrame`, porque la ventana principal está oculta mientras dura el modo; y se
 * mantiene despierto el `AudioContext` de `levels.ts`, que si no se suspendería al ocultarse.
 */
import { acquireAudioTaps, holdAudioAwake, readTimeDomain, TIME_DOMAIN_SAMPLES } from '@/voice/levels'
import { levelFromSamples } from '@/voice/outputLevel'
import type { FloatingApi } from './api'

const FRAME_MS = 33
const ATTACK = 0.65
const RELEASE = 0.3

/** Sigue la demanda de main. Devuelve la baja. */
export function startLevelsForwarder(api: FloatingApi): () => void {
  const buffer = new Float32Array(TIME_DOMAIN_SAMPLES)
  let timer: ReturnType<typeof setInterval> | null = null
  let releaseTaps: (() => void) | null = null
  let releaseAwake: (() => void) | null = null
  let out = 0
  let input = 0

  const smooth = (previous: number, raw: number): number => {
    const next = previous + (raw - previous) * (raw > previous ? ATTACK : RELEASE)
    return next < 0.01 ? 0 : next
  }

  const tick = (): void => {
    out = smooth(out, readTimeDomain('output', buffer) ? levelFromSamples(buffer) : 0)
    input = smooth(input, readTimeDomain('input', buffer) ? levelFromSamples(buffer) : 0)
    api.reportLevels(out, input)
  }

  const stop = (): void => {
    if (timer !== null) clearInterval(timer)
    timer = null
    releaseTaps?.()
    releaseAwake?.()
    releaseTaps = releaseAwake = null
    out = input = 0
  }

  const start = (): void => {
    if (timer !== null) return
    releaseAwake = holdAudioAwake()
    releaseTaps = acquireAudioTaps()
    timer = setInterval(tick, FRAME_MS)
  }

  const unsubscribe = api.onLevelsDemand((on) => (on ? start() : stop()))
  return () => {
    unsubscribe()
    stop()
  }
}
