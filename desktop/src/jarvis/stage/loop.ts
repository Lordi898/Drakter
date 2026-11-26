/**
 * Planificador del bucle único: `requestAnimationFrame` con límite de fps. Espera con un temporizador
 * hasta justo antes del fotograma que toca, así a 20-30 fps el hilo no despierta 60 veces por segundo.
 * Intervalo 0 = a demanda: solo dibuja tras `request()`.
 */
export interface Loop {
  setInterval(ms: number): void
  request(): void
  pause(): void
  resume(): void
  dispose(): void
  readonly running: boolean
}

/** `steady` = este fotograma sigue a otro del ritmo normal: su intervalo sirve para el regulador. */
export type DrawFn = (now: number, steady: boolean) => void

const VSYNC_SLACK = 4 // ms: margen para que un rAF que llega un poco antes cuente como el que toca
const TIMER_LEAD = 12 // ms: el temporizador despierta antes y el rAF siguiente cuadra con el vsync

export function createLoop(draw: DrawFn): Loop {
  let interval = 1000 / 30
  let last = -1
  let steadyChain = false
  let raf = 0
  let timer = 0
  let wanted = false
  let paused = false
  let disposed = false

  const cancel = (): void => {
    if (raf) cancelAnimationFrame(raf)
    if (timer) clearTimeout(timer)
    raf = 0
    timer = 0
  }

  const onFrame = (now: number): void => {
    raf = 0
    if (paused || disposed) return
    const due = interval > 0 && (last < 0 || now - last >= interval - VSYNC_SLACK)
    if (due || wanted) {
      const steady = steadyChain && due && last >= 0
      wanted = false
      last = now
      steadyChain = interval > 0
      draw(now, steady)
    }
    schedule()
  }

  function schedule(): void {
    if (paused || disposed || raf) return
    if (interval <= 0 && !wanted) {
      steadyChain = false
      return
    }
    const wait = wanted || last < 0 ? 0 : interval - (performance.now() - last) - TIMER_LEAD
    if (wait > 0) {
      if (!timer)
        timer = window.setTimeout(() => {
          timer = 0
          schedule()
        }, wait)
      return
    }
    if (timer) clearTimeout(timer)
    timer = 0
    raf = requestAnimationFrame(onFrame)
  }

  return {
    get running() {
      return !paused && !disposed && (raf !== 0 || timer !== 0)
    },
    setInterval(ms) {
      if (ms === interval) return
      interval = ms
      steadyChain = false
      cancel()
      schedule()
    },
    request() {
      wanted = true
      if (timer) {
        clearTimeout(timer)
        timer = 0
      }
      schedule()
    },
    pause() {
      paused = true
      steadyChain = false
      cancel()
    },
    resume() {
      if (!paused) return
      paused = false
      wanted = true
      schedule()
    },
    dispose() {
      disposed = true
      cancel()
    }
  }
}
