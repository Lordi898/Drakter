/** TAREAS Y PROYECTOS: una órbita por proyecto (avance real) con las tareas abiertas como satélites. */
import * as THREE from 'three'
import { C, TAU, disposeMesh, makePoints, type ColorName, type PointCloud } from '../gl/kit'
import { createLabels, type Label, type LabelBatch } from '../gl/labels'
import type { VTask } from '../model'
import { type ModuleDef } from './base'

interface Orbit { readonly id: string | null; readonly name: string; readonly col: ColorName; readonly percent: number | null }
interface Sat { readonly t: VTask; readonly oi: number; readonly base: number; readonly speed: number; x: number; y: number }
export interface TareasState { orbits: Orbit[]; sats: Sat[]; pts: PointCloud | null; labels: LabelBatch | null; labelKey: string }

const MAX_ORBITS = 5, MAX_SATS = 160
const rH = (i: number) => 4.95 + i * 0.2
const rD = (i: number) => 2.98 + i * 0.41
const lerp = (a: number, b: number, t: number) => a + (b - a) * t
export const tareasState = (): TareasState => ({ orbits: [], sats: [], pts: null, labels: null, labelKey: '' })

function orbitsOf(projects: readonly { id: string; name: string; col: ColorName; percent: number }[] | null, tasks: readonly VTask[]): Orbit[] {
  const withTasks = new Set(tasks.map((t) => t.projectId))
  const out: Orbit[] = (projects ?? []).filter((p) => withTasks.has(p.id) || (projects?.length ?? 0) <= MAX_ORBITS).slice(0, MAX_ORBITS - (withTasks.has(null) ? 1 : 0)).map((p) => ({ id: p.id, name: p.name, col: p.col, percent: p.percent }))
  if (tasks.some((t) => !t.projectId || !out.some((o) => o.id === t.projectId))) out.push({ id: null, name: 'Sueltas', col: 'ice', percent: null })
  return out
}

export const tareas: ModuleDef<TareasState> = {
  id: 'tareas', name: 'Tareas', key: '2', rIn: 4.85, rOut: 5.95,
  home: { pos: [0, 0, 0], rx: -1.02, rz: 0.11, scale: 1, spin: 0 },
  kpi: ({ model }) => {
    if (!model.tasks) return 'cargando tareas…'
    const open = model.tasks.filter((t) => !t.done).length, late = model.tasks.filter((t) => t.tone === 'late').length
    return `${open} abiertas${late ? ` · ${late} vencida${late === 1 ? '' : 's'}` : ''}`
  },
  buildHome(b, l, { model }, m) {
    m.s.orbits = orbitsOf(model.projects, model.tasks ?? [])
    m.s.orbits.forEach((o, i) => {
      b.line(rH(i), 0, 1, 0.035, { a: 0.3, col: C[o.col] })
      if (o.percent !== null) b.flow(rH(i), i * 0.17, i * 0.17 + o.percent, 0.05, 3, { col: C[o.col], a: 0.8 })
    })
    b.scale(120, 5.86, 0.05, { major: 10, majorLen: 0.12, a: 0.5 })
    const open = model.tasks?.filter((t) => !t.done).length ?? 0, late = model.tasks?.filter((t) => t.tone === 'late').length ?? 0
    const w = l.text(model.tasks ? `TAREAS · ${open} ABIERTAS EN ${m.s.orbits.length} ÓRBITAS` : 'TAREAS', 6.14, 0.415, 0.2, { a: 0.85, inward: true })
    if (late) l.text(`${late} VENCIDA${late > 1 ? 'S' : ''}`, 6.14, 0.415 - w / 2 - 0.012, 0.2, { col: C.red, a: 1, inward: true, align: 'start' })
  },
  buildDetail(b, _ctx, m) {
    m.s.orbits.forEach((o, i) => {
      const r = rD(i), c0 = 0.03 + i * 0.2, p = o.percent ?? 0
      b.line(r, 0, 1, 0.04, { a: 0.32, col: C[o.col] })
      if (o.percent !== null) b.flow(r, c0, c0 + p * 0.94, 0.1, 4, { col: C[o.col], a: 1 }).dash(r + 0.085, c0, c0 + 0.94, 0.03, 47, { col: C[o.col], a: 0.3 })
      b.tick(c0, r - 0.13, r + 0.13, 0.04, { col: C.white })
      b.text(`${o.name.toUpperCase().slice(0, 28)}${o.percent !== null ? ` · ${Math.round(p * 100)} %` : ''}`, r + 0.15, c0 + 0.006, 0.15, { align: 'start', col: C[o.col], inward: c0 > 0.3 && c0 < 0.7 })
    })
    b.line(4.72, 0, 1, 0.05, { a: 0.8 }).scale(180, 4.72, 0.05, { major: 15, majorLen: 0.12, a: 0.6 }).dash(2.76, 0, 1, 0.035, 120, { a: 0.5, col: C.blue })
  },
  sync(m, { gfx, model }) {
    const s = m.s
    if (s.pts) { m.group.remove(s.pts.pts); disposeMesh(s.pts.pts) }
    const tasks = (model.tasks ?? []).filter((t) => !t.done).slice(0, MAX_SATS)
    const per = new Map<number, number>()
    s.sats = tasks.map((t) => {
      let oi = s.orbits.findIndex((o) => o.id === t.projectId)
      if (oi < 0) oi = s.orbits.length - 1
      const j = per.get(oi) ?? 0
      per.set(oi, j + 1)
      return { t, oi, base: 0, speed: (oi % 2 ? -1 : 1) * (0.0075 - oi * 0.0009), x: 0, y: 0 }
    })
    for (const sat of s.sats) (sat as { base: number }).base = sat.oi * 0.13 + s.sats.filter((x) => x.oi === sat.oi).indexOf(sat) / Math.max(1, per.get(sat.oi) ?? 1)
    s.pts = makePoints(gfx, s.sats.length)
    s.sats.forEach((sat, i) => {
      const t = sat.t, col = t.tone === 'late' ? C.red : t.tone === 'soon' ? C.amber : C[s.orbits[sat.oi]?.col ?? 'cyan']
      s.pts!.style(i, col, 1, 0.27 + t.prio * 0.1, t.tone === 'open' ? 2 : 3, t.num)
    })
    s.pts.flush(true)
    m.group.add(s.pts.pts)
    if (!s.labels) { s.labels = createLabels(gfx); m.group.add(s.labels.mesh) }
    s.labelKey = ''
  },
  update(m, t, _dt, f) {
    const s = m.s
    if (!s.pts) return
    for (let i = 0; i < s.sats.length; i++) {
      const sat = s.sats[i]!, r = lerp(rH(sat.oi), rD(sat.oi), f)
      const th = Math.PI / 2 - TAU * (sat.base + t * sat.speed * (m.hover === sat.t.num || m.sel === sat.t.num ? 0.15 : 1))
      sat.x = r * Math.cos(th)
      sat.y = r * Math.sin(th)
      s.pts.set(i, sat.x, sat.y, 0)
    }
    s.pts.flush()
    const u = s.pts.mat.uniforms
    u.uHover.value = m.hover || -1
    u.uSel.value = m.sel || -1
    u.uOpacity.value = m.homeMesh.material.uniforms.uOpacity.value * (1 - f) + f
    u.uMask.value = 1 - f
    // Etiquetas (en el Stage): vencidas, que vencen pronto y la señalada.
    if (s.labels) {
      const list: Label[] = []
      if (f > 0.6) for (const sat of s.sats) {
        const on = sat.t.num === m.hover || sat.t.num === m.sel
        if (!(on || sat.t.tone === 'late' || sat.t.tone === 'soon') || list.length > 9) continue
        list.push({ x: sat.x, y: sat.y, z: 0, text: sat.t.title, strong: on, tone: sat.t.tone === 'open' ? '' : sat.t.tone })
      }
      s.labels.set(list)
      s.labels.flush()
      s.labels.uniforms.uOpacity.value = Math.max(0, (f - 0.6) / 0.4)
    }
  },
  pickScreen(m, mx, my, sc) {
    let best = 0, bd = 20
    const v = new THREE.Vector3()
    for (const sat of m.s.sats) {
      const p = sc.project(v.set(sat.x, sat.y, 0).applyMatrix4(m.group.matrixWorld)), d = Math.hypot(p.x - mx, p.y - my)
      if (d < bd) { bd = d; best = sat.t.num }
    }
    return best
  },
  tip(num, { model }) {
    const t = model.tasks?.find((x) => x.num === num)
    return t ? { title: t.title, sub: `${t.projectName ?? 'sin proyecto'} · ${t.dueText} · prioridad ${['baja', 'alta', 'urgente'][t.prio - 1]}`, hint: 'clic para seleccionarla', tone: t.tone === 'late' ? 'late' : t.tone === 'soon' ? 'soon' : undefined } : null
  },
  click: () => ({ kind: 'select' }),
  dispose(m) {
    if (m.s.pts) disposeMesh(m.s.pts.pts)
  }
}
