/** Interpolaciones gobernadas por el bucle del Stage (se paran con la ventana oculta) y que se pueden rematar. */
export const ease = {
  linear: (t: number) => t,
  outExpo: (t: number) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t)),
  outCubic: (t: number) => 1 - Math.pow(1 - t, 3),
  inCubic: (t: number) => t * t * t,
  inOut: (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
  outBack: (t: number) => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2) }
}

interface Tw { t: number; dur: number; e: (t: number) => number; update?: (k: number) => void; done?: () => void; tag: string; dead: boolean }

export interface Tweens {
  tween(o: { dur?: number; delay?: number; ease?: (t: number) => number; update?: (k: number) => void; done?: () => void; tag?: string }): void
  after(delay: number, fn: () => void, tag?: string): void
  tick(dt: number): void
  /** Remata (o cancela) las de esa etiqueta; rematar aplica su estado final en orden. */
  flush(tag: string, finish?: boolean): void
  active(tag: string): boolean
}

export function createTweens(): Tweens {
  const list: Tw[] = []
  const T: Tweens = {
    tween({ dur = 0.5, delay = 0, ease: e = ease.outExpo, update, done, tag = '' }) {
      list.push({ t: -delay, dur: Math.max(dur, 1e-4), e, update, done, tag, dead: false })
    },
    after(delay, fn, tag = '') { T.tween({ dur: 0.0001, delay, done: fn, tag }) },
    tick(dt) {
      for (let i = 0; i < list.length; i++) {
        const tw = list[i]!
        if (tw.dead) continue
        tw.t += dt
        if (tw.t < 0) continue
        const k = Math.min(1, tw.t / tw.dur)
        tw.update?.(tw.e(k))
        if (k >= 1) { tw.dead = true; tw.done?.() }
      }
      for (let i = list.length - 1; i >= 0; i--) if (list[i]!.dead) list.splice(i, 1)
    },
    flush(tag, finish = true) {
      for (let guard = 0; guard < 20; guard++) {
        const l = list.filter((t) => !t.dead && t.tag === tag)
        if (!l.length) break
        l.sort((a, b) => a.dur - a.t - (b.dur - b.t))
        for (const tw of l) { tw.dead = true; if (finish) { tw.update?.(tw.e(1)); tw.done?.() } }
      }
    },
    active: (tag) => list.some((t) => !t.dead && t.tag === tag)
  }
  return T
}
