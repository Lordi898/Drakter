/**
 * Piezas comunes de los sectores del Visor: lienzo 2D con ritmo limitado, estados de una instantánea
 * (cargando, sin conexión, error, vacío), fila de indicadores y acciones con aviso.
 * Reglas de rendimiento (visor-port.md §4): un lienzo solo se redibuja si cambian sus datos o su minuto,
 * o durante su animación de entrada; nunca fuera de su sector ni con su panel plegado.
 */
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import type { Snapshot } from '@/jarvis/data'
import type { SectionId } from '@/navigation/sections'
import { ApiError, describeError } from '@/services/api'
import { addNotification } from '@/stores/notifications'
import { WorldContext } from '../Panel'

/** Navegación del Visor para los sectores: abrir una sección en Drakter (vuelve al modo normal). */
export interface VisorNav {
  readonly openInDrakter: (section: SectionId) => void
  readonly reducedMotion: boolean
}
export const NavContext = createContext<VisorNav>({ openInDrakter: () => undefined, reducedMotion: false })
export const useVisorNav = (): VisorNav => useContext(NavContext)

/** Minuto actual (cambia una vez por minuto, alineado al reloj): relojes y cuentas atrás sin escrituras por segundo. */
export function useMinute(): number {
  const [m, setM] = useState(() => Math.floor(Date.now() / 60000))
  useEffect(() => {
    let t = 0
    const arm = (): void => { t = window.setTimeout(() => { setM(Math.floor(Date.now() / 60000)); arm() }, 60000 - (Date.now() % 60000) + 50) }
    arm()
    return () => window.clearTimeout(t)
  }, [])
  return m
}

/** Hora local decimal (0-24) del sistema. */
export const nowHours = (): number => { const d = new Date(); return d.getHours() + d.getMinutes() / 60 }

interface Chart2DProps {
  readonly sector: number
  readonly w: number
  readonly h: number
  /** Firma de los datos: el lienzo solo se redibuja si cambia (o cambia el minuto con `clock`). */
  readonly sig: string
  readonly clock?: boolean
  readonly draw: (x: CanvasRenderingContext2D, w: number, h: number, boot: number) => void
  readonly lock?: string
}

/** Lienzo 2D de un panel. La entrada (boot 0→1, ~0,9 s) se repite al llegar al sector. */
export function Chart2D({ sector, w, h, sig, clock, draw, lock }: Chart2DProps) {
  const world = useContext(WorldContext)
  const { reducedMotion } = useVisorNav()
  const ref = useRef<HTMLCanvasElement>(null)
  const drawRef = useRef(draw)
  drawRef.current = draw
  const sigRef = useRef(sig)
  sigRef.current = sig

  useEffect(() => {
    const cv = ref.current
    const x = cv?.getContext('2d')
    if (!cv || !x) return
    if (!world) {
      // «HUD sin lienzo»: se dibuja al cambiar los datos y una vez por minuto.
      const paint = (): void => drawRef.current(x, w, h, 1)
      paint()
      const iv = clock ? window.setInterval(paint, 60000) : 0
      return () => window.clearInterval(iv)
    }
    let drawn = '', boot = reducedMotion ? 1 : 0, wasFocused = false, last = 0, panel: Element | null = null
    return world.onTick((f) => {
      if (!world.near(sector)) { wasFocused = false; return }
      panel ??= cv.closest('.jv-visor-pnl')
      if (panel && !panel.classList.contains('on')) return // plegado: no se pinta bajo opacidad 0
      const focused = world.sector === sector
      if (focused && !wasFocused && !f.reducedMotion) boot = 0
      wasFocused = focused
      const key = `${sigRef.current}|${clock ? Math.floor(Date.now() / 60000) : 0}`
      if (boot >= 1 && key === drawn) return
      boot = f.reducedMotion ? 1 : Math.min(1, boot + (last ? Math.min(0.1, f.time - last) : 0.033) / 0.9)
      last = f.time
      drawRef.current(x, w, h, boot)
      if (boot >= 1) drawn = key
    }, 30)
  }, [world, sector, w, h, clock, reducedMotion])

  // Sin lienzo: redibujo al cambiar la firma.
  useEffect(() => {
    if (world) return
    const x = ref.current?.getContext('2d')
    if (x) drawRef.current(x, w, h, 1)
  }, [world, sig, w, h])

  return <canvas ref={ref} width={w} height={h} style={{ width: w, height: h }} className="jv-visor-chart" data-lock={lock} aria-hidden="true" />
}

/** Estado de una instantánea mientras no hay nada que pintar; `null` si hay datos que mostrar. */
export function SnapNote({ snap, empty, isEmpty }: { readonly snap: Snapshot<unknown>; readonly empty: string; readonly isEmpty: boolean }) {
  if (snap.data === null) {
    if (snap.status === 'loading') return <p className="jv-visor-note">Cargando…</p>
    return (
      <p className="jv-visor-note warn">
        {snap.status === 'offline' ? 'Sin conexión con el servicio local.' : snap.error ?? 'No se ha podido cargar.'}{' '}
        <button type="button" className="link" data-lock="Reintentar" onClick={snap.reload}>Reintentar</button>
      </p>
    )
  }
  if (isEmpty) return <p className="jv-visor-note">{empty}</p>
  if (snap.status === 'offline' || snap.status === 'error') return <p className="jv-visor-note warn small">Datos de hace un momento: {snap.status === 'offline' ? 'sin conexión' : snap.error}</p>
  return null
}

export type Kpi = readonly [value: ReactNode, label: string, warn?: boolean]
export function Kpis({ items }: { readonly items: readonly Kpi[] }) {
  return (
    <div className="jv-visor-kpis">
      {items.map(([v, l, warn]) => (
        <div key={l} className={`kpi ${warn ? 'warn' : ''}`} data-lock={`${l}  ${typeof v === 'string' || typeof v === 'number' ? v : ''}`}>
          <b>{v}</b><span>{l}</span>
        </div>
      ))}
    </div>
  )
}

/**
 * Ejecuta una mutación real (`modules/<x>/api.ts`) y avisa del resultado en las alertas del Visor.
 * Un 409 `confirmation_required` NO es un error: el ticket ya quedó registrado y el diálogo nativo
 * de main pide la aprobación (`ConfirmationHost`); aquí solo se avisa de que espera.
 */
export function useAction(): { readonly busy: string | null; readonly run: (id: string, fn: () => Promise<unknown>, ok: string, after?: () => void) => void } {
  const [busy, setBusy] = useState<string | null>(null)
  const run = (id: string, fn: () => Promise<unknown>, ok: string, after?: () => void): void => {
    if (busy) return
    setBusy(id)
    fn()
      .then(() => addNotification({ tone: 'success', title: ok }))
      .catch((e: unknown) => {
        if (e instanceof ApiError && e.code === 'confirmation_required') addNotification({ tone: 'info', title: 'Pendiente de tu aprobación', body: e.confirmation?.summary.slice(0, 160) })
        else addNotification({ tone: 'error', title: 'No se ha podido completar', body: describeError(e, 'El servicio local no ha respondido.') })
      })
      .finally(() => { setBusy(null); after?.() })
  }
  return { busy, run }
}

/** Días naturales entre dos fechas 'AAAA-MM-DD' (b - a). */
export function dayDiff(a: string, b: string): number {
  return Math.round((Date.UTC(+b.slice(0, 4), +b.slice(5, 7) - 1, +b.slice(8, 10)) - Date.UTC(+a.slice(0, 4), +a.slice(5, 7) - 1, +a.slice(8, 10))) / 86400000)
}
/** 'AAAA-MM-DD' local del sistema. */
export function localDay(d = new Date()): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
/** Fecha de vencimiento de una tarea en la zona local ('AAAA-MM-DD'), o null. */
export function dueDay(t: { readonly due_date: string | null; readonly due_at: string | null }): string | null {
  if (t.due_date) return t.due_date.slice(0, 10)
  return t.due_at ? localDay(new Date(t.due_at)) : null
}
export const PRIORITY_RANK: Record<string, number> = { urgent: 0, high: 1, medium: 2, low: 3 }
export const PRIORITY_ES: Record<string, string> = { urgent: 'urgente', high: 'alta', medium: 'media', low: 'baja' }
export const plural = (n: number, one: string, many: string): string => `${n} ${n === 1 ? one : many}`
