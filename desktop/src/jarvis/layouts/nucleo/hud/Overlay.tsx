/**
 * Superposiciones de Núcleo: descripción emergente, retícula de fijación (de Visor) y alertas con
 * barrido (de Visor). Todas se mueven por ref; su bucle solo corre mientras hay algo que animar.
 */
import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'
import type { Tip } from '../modules/base'

export interface OverlayApi {
  /** Descripción del elemento del lienzo bajo el puntero (o null). */
  setTip(tip: Tip | null): void
  /** Posición del puntero (px CSS). */
  move(x: number, y: number): void
  /** Objetivo en el lienzo (centro y radio en px), o null. Se pide por función en cada paso. */
  setCanvasTarget(get: (() => { x: number; y: number; r: number } | null) | null): void
}

type Box = { x: number; y: number; w: number; h: number }

export const Overlay = forwardRef<OverlayApi, { readonly reduced: boolean; readonly root: HTMLElement | null }>(function Overlay({ reduced, root }, api) {
  const tipEl = useRef<HTMLDivElement>(null)
  const lockEl = useRef<HTMLDivElement>(null)
  const st = useRef({ tip: null as Tip | null, mx: 0, my: 0, el: null as HTMLElement | null, canvas: null as (() => { x: number; y: number; r: number } | null) | null, box: { x: 0, y: 0, w: 60, h: 60 } as Box, on: 0, raf: 0, last: 0, label: '' })

  const kick = (): void => {
    const s = st.current
    if (s.raf) return
    s.last = performance.now()
    s.raf = requestAnimationFrame(step)
  }
  const step = (now: number): void => {
    const s = st.current, el = lockEl.current
    s.raf = 0
    const dt = Math.min(0.05, (now - s.last) / 1000)
    s.last = now
    let target: Box | null = null
    if (s.el?.isConnected) { const r = s.el.getBoundingClientRect(); if (r.width > 0) target = { x: r.left - 6, y: r.top - 6, w: r.width + 12, h: r.height + 12 } }
    else if (s.canvas) { const c = s.canvas(); if (c) target = { x: c.x - c.r, y: c.y - c.r, w: c.r * 2, h: c.r * 2 } }
    const want = target ? 1 : 0
    s.on += (want - s.on) * (1 - Math.exp(-dt * 14))
    const k = 1 - Math.exp(-dt * (reduced ? 60 : 16)), b = s.box
    if (target) { if (s.on < 0.05) Object.assign(b, { x: s.mx - 30, y: s.my - 30, w: 60, h: 60 }); b.x += (target.x - b.x) * k; b.y += (target.y - b.y) * k; b.w += (target.w - b.w) * k; b.h += (target.h - b.h) * k }
    if (el) {
      el.style.opacity = s.on.toFixed(3)
      el.style.transform = `translate3d(${b.x.toFixed(1)}px,${b.y.toFixed(1)}px,0)`
      el.style.width = `${b.w.toFixed(1)}px`
      el.style.height = `${b.h.toFixed(1)}px`
    }
    const moving = target ? Math.abs(target.x - b.x) + Math.abs(target.y - b.y) + Math.abs(target.w - b.w) > 0.5 || s.on < 0.99 || !!s.canvas : s.on > 0.01
    if (moving) { s.raf = requestAnimationFrame(step) }
  }

  const setLockLabel = (text: string, tone = ''): void => {
    const el = lockEl.current
    if (!el) return
    el.className = `nx-lock ${tone}`
    const b = el.querySelector('b')
    if (b && st.current.label !== text) { st.current.label = text; b.textContent = text }
  }

  useImperativeHandle(api, () => ({
    setTip(tip) {
      const s = st.current, t = tipEl.current
      s.tip = tip
      if (!t) return
      if (!tip) { t.classList.remove('on'); return }
      t.className = `nx-tip on ${tip.tone ?? ''}`
      const [b, sp, em] = t.children as unknown as HTMLElement[]
      b!.textContent = tip.title
      sp!.textContent = tip.sub
      em!.textContent = tip.hint ?? ''
      place()
      if (s.canvas) { setLockLabel(tip.title.slice(0, 40), tip.tone ?? ''); kick() }
    },
    move(x, y) {
      st.current.mx = x
      st.current.my = y
      if (st.current.tip) place()
    },
    setCanvasTarget(get) { st.current.canvas = get; kick() }
  }))

  const place = (): void => {
    const t = tipEl.current, s = st.current
    if (!t) return
    const w = t.offsetWidth
    t.style.transform = `translate(${Math.min(window.innerWidth - w - 12, s.mx + 18)}px,${Math.max(8, s.my - 12)}px)`
  }

  // Elementos del HUD con `data-lock`: la retícula vuela hasta ellos.
  useEffect(() => {
    if (!root) return
    const over = (e: PointerEvent): void => {
      const t = (e.target as HTMLElement).closest?.<HTMLElement>('[data-lock]')
      if (!t || !root.contains(t) || t === st.current.el) return
      st.current.el = t
      setLockLabel(t.dataset.lock ?? '')
      kick()
    }
    const out = (e: PointerEvent): void => {
      const from = (e.target as HTMLElement).closest?.('[data-lock]'), to = (e.relatedTarget as HTMLElement | null)?.closest?.('[data-lock]')
      if (from && !to) { st.current.el = null; kick() }
    }
    root.addEventListener('pointerover', over)
    root.addEventListener('pointerout', out)
    return () => { root.removeEventListener('pointerover', over); root.removeEventListener('pointerout', out); cancelAnimationFrame(st.current.raf) }
  }, [root])

  return (
    <>
      <div className="nx-tip" ref={tipEl} aria-hidden="true"><b /><span /><em /></div>
      <div className="nx-lock" ref={lockEl} aria-hidden="true"><i /><i /><i /><i /><b /></div>
    </>
  )
})

export interface Alert { readonly id: number; readonly kind: 'info' | 'ok' | 'warn' | 'error'; readonly title: string; readonly text: string; readonly at: string }

export function Alerts({ alerts }: { readonly alerts: readonly Alert[] }) {
  return (
    <div className="nx-alerts" role="status" aria-live="polite">
      {alerts.map((a) => (
        <div key={a.id} className={`nx-alert ${a.kind}`} role={a.kind === 'error' ? 'alert' : undefined}>
          <b>{a.title}</b><p>{a.text}</p><time>{a.at}</time>
        </div>
      ))}
    </div>
  )
}

/** Alertas: máximo tres, cada una se va sola a los 7 s (las de error a los 12 s). */
export function useAlerts(): { alerts: readonly Alert[]; push: (kind: Alert['kind'], title: string, text: string) => void } {
  const [alerts, setAlerts] = useState<readonly Alert[]>([])
  const seq = useRef(0)
  const push = useRef((kind: Alert['kind'], title: string, text: string) => {
    const id = ++seq.current, d = new Date()
    const at = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
    setAlerts((list) => [{ id, kind, title, text, at }, ...list].slice(0, 3))
    setTimeout(() => setAlerts((list) => list.filter((a) => a.id !== id)), kind === 'error' ? 12_000 : 7_000)
  }).current
  return { alerts, push }
}
