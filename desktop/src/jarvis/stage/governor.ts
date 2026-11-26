/**
 * Regulador por p90 del tiempo de fotograma (jarvis-arquitectura.md §2.6). Mide ventanas de 3 s del
 * intervalo entre fotogramas seguidos frente al objetivo. Dos ventanas malas seguidas (cuatro con un
 * nivel fijado a mano) bajan un peldaño; 10 s buenas lo suben, con espera doble tras cada recaída.
 */
export interface GovernorVerdict {
  readonly p90ms: number
  /** -1 = bajar un peldaño, +1 = subir uno, 0 = quieto. */
  readonly step: -1 | 0 | 1
}

const WINDOW_MS = 3000
const MIN_SAMPLES = 15
const BAD_RATIO = 1.25
const HYSTERESIS_MS = 10_000

export interface Governor {
  /** Intervalo real entre dos fotogramas seguidos y el intervalo que tocaba. */
  push(deltaMs: number, targetMs: number): void
  /** Llamar cada fotograma; devuelve un veredicto al cerrar cada ventana. */
  tick(now: number, sustainedOnly: boolean): GovernorVerdict | null
  /** Tras cambiar de peldaño: empieza de cero. */
  reset(now: number): void
  readonly p90ms: number
}

export function createGovernor(): Governor {
  const ms = new Float32Array(512)
  const ratio = new Float32Array(512)
  let n = 0
  let start = -1
  let bad = 0
  let goodSince = -1
  let wait = HYSTERESIS_MS
  let lastStep: -1 | 0 | 1 = 0
  let p90 = 0

  const p90of = (a: Float32Array): number => {
    const s = a.slice(0, n).sort()
    return s[Math.min(n - 1, Math.floor(n * 0.9))] ?? 0
  }

  return {
    get p90ms() {
      return p90
    },
    push(deltaMs, targetMs) {
      if (n >= ms.length || targetMs <= 0) return
      ms[n] = deltaMs
      ratio[n] = deltaMs / targetMs
      n++
    },
    reset(now) {
      n = 0
      start = now
      bad = 0
      goodSince = now
    },
    tick(now, sustainedOnly) {
      if (start < 0) this.reset(now)
      if (now - start < WINDOW_MS) return null
      const enough = n >= MIN_SAMPLES
      const worst = enough ? p90of(ratio) : 0
      if (enough) p90 = p90of(ms)
      n = 0
      start = now
      if (!enough) return null // reposo, a demanda u oculto: no hay datos que juzgar
      if (worst > BAD_RATIO) {
        bad++
        goodSince = -1
        if (bad >= (sustainedOnly ? 4 : 2)) {
          bad = 0
          // Recaída justo después de subir: la próxima subida espera el doble.
          if (lastStep === 1) wait = Math.min(wait * 2, 160_000)
          lastStep = -1
          return { p90ms: p90, step: -1 }
        }
        return { p90ms: p90, step: 0 }
      }
      bad = 0
      if (goodSince < 0) goodSince = now
      if (now - goodSince >= wait) {
        goodSince = now
        lastStep = 1
        return { p90ms: p90, step: 1 }
      }
      return { p90ms: p90, step: 0 }
    }
  }
}
