/**
 * Paneles radiales de la vista de sección. Su canto interior sigue el arco del anillo desplegado: el
 * recorte va en un hijo de fondo (un clip-path en el panel cortaría la línea guía). El reparto se
 * calcula al cambiar de sección, de contenido o de tamaño, nunca por fotograma.
 */
import { useLayoutEffect, useRef } from 'react'
import type { FocusFrame } from '../gl/scene'
import type { PanelDef, Slot } from './content'

const SLOTS: readonly Slot[] = ['lt', 'lb', 'rt', 'rb']
const clamp = (x: number, a: number, b: number) => Math.min(b, Math.max(a, x))

function layout(root: HTMLElement, frame: FocusFrame): void {
  const W = root.clientWidth, H = root.clientHeight
  const R0 = frame.r + Math.max(18, H * 0.022), K = frame.ry / frame.r, cx = frame.cx, cy = frame.cy
  const sect = root.parentElement?.querySelector<HTMLElement>('.nx-sect'), nav = root.parentElement?.querySelector<HTMLElement>('.nx-nav')
  const top = (sect ? sect.offsetTop + sect.offsetHeight : 90) + 12, bot = (nav ? nav.offsetTop : H - 70) - 14, gap = 9, mx = 42
  const ends: Record<string, number> = {}
  for (const p of root.querySelectorAll<HTMLElement>('.nx-rp')) {
    const s = p.dataset.slot as Slot, left = s[0] === 'l', isTop = s[1] === 't'
    const R = R0 * (isTop ? 0.95 : 1.1), xa = (y: number) => R * Math.sqrt(Math.max(0, 1 - ((y - cy) / (R * K)) ** 2))
    const y0 = isTop ? top : Math.max(cy + gap, (ends[s[0]!] ?? 0) + gap * 2), yMax = isTop ? bot - 190 : bot
    const inner = p.lastElementChild as HTMLElement
    p.style.height = 'auto'
    inner.style.height = 'auto'
    const need = inner.scrollHeight + 10
    inner.style.height = ''
    const y1 = Math.min(yMax, y0 + Math.max(need, 150)), h = Math.max(60, y1 - y0)
    if (isTop) ends[s[0]!] = y1
    const far = isTop ? y0 : y1, near = isTop ? y1 : y0
    const wMax = Math.min(cx - xa(far) - mx - 6, cx - mx - 60, 640), safe = Math.max(200, cx - xa(near) - mx - 20), w = Math.max(wMax, safe + 20)
    p.style.cssText = `left:${left ? mx : W - mx - w}px;top:${y0}px;width:${w}px;height:${h}px;--safe:${safe}px`
    const pts: [number, number][] = []
    for (let i = 0; i <= 18; i++) { const y = y0 + (h * i) / 18, x = clamp(cx - xa(y) - mx, 40, w); pts.push([left ? x : w - x, y - y0]) }
    const poly: [number, number][] = left ? [[0, 0], ...pts, [0, h]] : [[w, 0], ...pts, [w, h]]
    const bg = p.firstElementChild as HTMLElement
    bg.style.clipPath = `polygon(${poly.map(([x, y]) => `${x.toFixed(1)}px ${y.toFixed(1)}px`).join(',')})`
    const sv = p.children[1] as SVGSVGElement
    sv.setAttribute('viewBox', `0 0 ${w} ${h}`)
    sv.children[0]!.setAttribute('d', `M${poly.map(([x, y]) => `${x.toFixed(1)} ${y.toFixed(1)}`).join('L')}Z`)
    const [gx, gy] = pts[isTop ? 13 : 5]!, gd = left ? 1 : -1, ex = gx + gd * (R0 * 0.085 + 16), ey = gy + (cy - (y0 + gy)) * 0.12 // línea guía hacia el anillo
    sv.children[1]!.setAttribute('d', `M${(gx - gd * 26).toFixed(1)} ${gy.toFixed(1)}L${gx.toFixed(1)} ${gy.toFixed(1)}L${ex.toFixed(1)} ${ey.toFixed(1)}`)
    sv.children[2]!.setAttribute('cx', ex.toFixed(1))
    sv.children[2]!.setAttribute('cy', ey.toFixed(1))
  }
}

export function RadialPanels({ panels, show, frame, version }: { readonly panels: readonly PanelDef[]; readonly show: boolean; readonly frame: () => FocusFrame | null; readonly version: string }) {
  const ref = useRef<HTMLDivElement>(null)
  useLayoutEffect(() => {
    const root = ref.current, f = frame()
    if (!root || !f || !show) return
    layout(root, f)
    const onResize = (): void => { const g = frame(); if (g) layout(root, g) }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [frame, show, version])
  return (
    <div className="nx-panels" ref={ref}>
      {SLOTS.map((slot) => {
        const d = panels.find((x) => x.slot === slot)
        return (
          <article key={slot} className={`nx-rp ${slot} ui ${show && d ? 'show' : ''}`} data-slot={slot} aria-hidden={!show || !d}>
            <i className="bgc" />
            <svg className="edge" aria-hidden="true"><path /><path className="lead" /><circle r="3" /></svg>
            <div className="in">
              {d ? (
                <>
                  <h3><b>{d.title}</b><span>{d.meta ?? ''}</span></h3>
                  {d.hero ? <div className={`nx-hero ${d.hero.tone ?? ''}`}><b>{d.hero.big}</b><span>{d.hero.small}</span></div> : null}
                  {d.body}
                </>
              ) : null}
            </div>
          </article>
        )
      })}
    </div>
  )
}
