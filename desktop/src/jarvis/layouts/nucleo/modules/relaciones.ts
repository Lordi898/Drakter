/**
 * RELACIONES: constelación 3D de las entidades reales del Workspace y sus vínculos (tabla común de
 * relaciones). Las fuerzas se calculan una vez al llegar los datos; las etiquetas van en el Stage.
 */
import * as THREE from 'three'
import type { EntityType } from '@/modules/relationships/types'
import { C, RingBuilder, disposeMesh, linesMaterial, makePoints, type ColorName, type LinesMaterial, type PointCloud } from '../gl/kit'
import { createLabels, type Label, type LabelBatch } from '../gl/labels'
import { ENTITY_ES } from '../model'
import { type ModuleDef } from './base'

export const TYPE_COL: Readonly<Record<EntityType, ColorName>> = {
  project: 'white', subject: 'violet', task: 'cyan', habit: 'teal', calendar_event: 'indigo', time_block: 'blue', class_session: 'indigo', resource: 'ice', folder: 'ice'
}
const KIND: Readonly<Record<EntityType, number>> = { project: 2, subject: 4, task: 1, resource: 3, folder: 3, calendar_event: 1, time_block: 1, class_session: 1, habit: 1 }
const MAX_NODES = 140

export interface RelState {
  P: THREE.Vector3[]
  inner: THREE.Group | null
  pts: PointCloud | null
  lines: THREE.LineSegments | null
  ecol: Float32Array
  globe: THREE.Mesh[]
  depth: THREE.Vector2
  yaw: number; pitch: number; vy: number
  filter: EntityType | null
  key: string
  labels: LabelBatch | null
  nodes: { num: number; id: string; name: string; type: EntityType; deg: number }[]
  edges: { a: number; b: number; rel: string }[]
}
export const relState = (): RelState => ({ P: [], inner: null, pts: null, lines: null, ecol: new Float32Array(0), globe: [], depth: new THREE.Vector2(10, 30), yaw: 0.4, pitch: 0.28, vy: 0.11, filter: null, key: '', labels: null, nodes: [], edges: [] })

const rng = (seed: number) => { let a = seed >>> 0; return () => { a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296 } }

export function nearOf(s: RelState, num: number): Set<number> {
  const out = new Set([num])
  for (const e of s.edges) { const A = s.nodes[e.a]!, B = s.nodes[e.b]!; if (A.num === num) out.add(B.num); if (B.num === num) out.add(A.num) }
  return out
}

function restyle(m: { hover: number; sel: number; s: RelState }): void {
  const s = m.s
  if (!s.pts || !s.lines) return
  const focus = m.hover || m.sel, near = focus ? nearOf(s, focus) : null
  s.nodes.forEach((n, i) => {
    const on = (!near || near.has(n.num)) && (!s.filter || n.type === s.filter)
    s.pts!.style(i, C[TYPE_COL[n.type]], on ? 1 : 0.42, 0.26 + Math.min(n.deg, 9) * 0.034 + (n.type === 'project' ? 0.2 : n.type === 'subject' ? 0.1 : 0), KIND[n.type], n.num)
  })
  s.edges.forEach((e, i) => {
    const A = s.nodes[e.a]!, B = s.nodes[e.b]!, on = (!focus || A.num === focus || B.num === focus) && (!s.filter || A.type === s.filter || B.type === s.filter)
    const ca = C[TYPE_COL[A.type]], cb = C[TYPE_COL[B.type]], al = on ? (focus ? 1.2 : 0.62) : 0.13
    s.ecol.set([ca[0], ca[1], ca[2], al, cb[0], cb[1], cb[2], al], i * 8)
  })
  s.pts.flush(true)
  s.lines.geometry.attributes.aColor!.needsUpdate = true
}

export const relaciones: ModuleDef<RelState> = {
  id: 'relaciones', name: 'Relaciones', key: '5', cloud: true, rIn: 0, rOut: 0,
  home: { pos: [0, 5.4, -7.5], rx: 0, rz: 0, scale: 2.0, spin: 0 },
  kpi: ({ model }) => (model.graph ? `${model.graph.nodes.length} entidades · ${model.graph.edges.length} vínculos` : 'cargando relaciones…'),
  buildDetail(b, { model }) {
    b.line(4.72, 0, 1, 0.05, { a: 0.85 }).scale(240, 4.72, 0.045, { major: 10, majorLen: 0.11, a: 0.55 }).dash(4.5, 0, 1, 0.025, 90, { a: 0.3, col: C.blue })
    const g = model.graph
    b.text(g ? `${g.nodes.length} ENTIDADES · ${g.edges.length} VÍNCULOS` : 'RELACIONES', 4.92, 0, 0.17, { a: 0.7 })
    b.text(g && !g.edges.length ? 'AÚN NO HAY VÍNCULOS' : 'ARRASTRA PARA GIRAR', 4.92, 0.5, 0.15, { a: 0.5, inward: true })
  },
  sync(m, { gfx, model }) {
    const s = m.s
    if (!s.inner) {
      s.inner = new THREE.Group()
      m.group.add(s.inner)
      m.labelParent = s.inner
      const gb = new RingBuilder(gfx)
      gb.line(4.45, 0, 1, 0.03, { a: 0.3, col: C.blue }).scale(72, 4.45, 0.05, { major: 6, majorLen: 0.12, a: 0.35, col: C.blue })
      s.globe = [[Math.PI / 2, 0], [0, 0], [0, Math.PI / 2], [0, Math.PI / 4]].map(([rx, ry]) => {
        const g = gb.mesh()
        g.rotation.set(rx!, ry!, 0)
        g.material.uniforms.uMask.value = 0
        g.material.uniforms.uDepth = { value: s.depth }
        s.inner!.add(g)
        return g
      })
      s.labels = createLabels(gfx)
      s.inner.add(s.labels.mesh)
    }
    // Se reutilizan los materiales: liberarlos mientras el Stage aún compila (compileAsync) rompe a Three.
    const oldPts = s.pts?.mat, oldLines = s.lines?.material as LinesMaterial | undefined
    if (s.pts) { s.inner.remove(s.pts.pts); s.pts.pts.geometry.dispose(); s.pts = null }
    if (s.lines) { s.inner.remove(s.lines); s.lines.geometry.dispose(); s.lines = null }
    const g = model.graph
    if (!g) { s.nodes = []; s.edges = []; return }
    // Los más conectados primero; el resto no cabe sin volverse ruido.
    const keep = [...g.nodes.keys()].sort((a, b) => g.nodes[b]!.deg - g.nodes[a]!.deg).slice(0, MAX_NODES)
    const remap = new Map(keep.map((old, i) => [old, i]))
    s.nodes = keep.map((i) => ({ ...g.nodes[i]!, deg: 0 }))
    s.edges = []
    for (const e of g.edges) { const a = remap.get(e.a), b = remap.get(e.b); if (a === undefined || b === undefined) continue; s.edges.push({ a, b, rel: e.rel }); s.nodes[a]!.deg++; s.nodes[b]!.deg++ }
    const N = s.nodes.length, r = rng(77)
    const P = s.nodes.map(() => new THREE.Vector3(r() - 0.5, r() - 0.5, r() - 0.5).normalize().multiplyScalar(1 + r() * 2.5))
    const F = s.nodes.map(() => new THREE.Vector3()), d = new THREE.Vector3()
    const iters = Math.min(260, Math.floor(2.5e6 / Math.max(1, N * N)))
    for (let it = 0; it < iters; it++) {
      for (const f of F) f.set(0, 0, 0)
      for (let i = 0; i < N; i++) for (let j = i + 1; j < N; j++) { d.subVectors(P[i]!, P[j]!); const l = Math.max(0.25, d.length()); d.multiplyScalar(1.5 / (l * l * l)); F[i]!.add(d); F[j]!.sub(d) }
      for (const e of s.edges) { d.subVectors(P[e.b]!, P[e.a]!); const l = d.length(); d.multiplyScalar(((l - 1.35) * 0.09) / Math.max(l, 0.01)); F[e.a]!.add(d); F[e.b]!.sub(d) }
      for (let i = 0; i < N; i++) { F[i]!.addScaledVector(P[i]!, -0.03); P[i]!.addScaledVector(F[i]!, 0.35) }
    }
    // Las fuerzas deciden quién queda cerca de quién; después se reparte en una corteza que rodea al avatar sin taparlo.
    const order = P.map((p, i) => [p.length(), i] as const).sort((a, b) => a[0] - b[0])
    order.forEach(([, i], k) => { P[i]!.normalize().multiplyScalar(2.75 + 1.55 * Math.pow(k / Math.max(1, N - 1), 0.8)); P[i]!.y *= 0.9 })
    s.P = P
    s.pts = makePoints(gfx, N, oldPts)
    s.nodes.forEach((_, i) => s.pts!.set(i, P[i]!.x, P[i]!.y, P[i]!.z))
    s.pts.flush()
    s.pts.mat.uniforms.uDepth = { value: s.depth }
    s.inner.add(s.pts.pts)
    const geo = new THREE.BufferGeometry(), pos = new Float32Array(Math.max(1, s.edges.length) * 6), tt = new Float32Array(Math.max(1, s.edges.length) * 4)
    s.ecol = new Float32Array(Math.max(1, s.edges.length) * 8)
    s.edges.forEach((e, i) => { const A = P[e.a]!, B = P[e.b]!; pos.set([A.x, A.y, A.z, B.x, B.y, B.z], i * 6); tt.set([0, i * 0.37, 1, i * 0.37], i * 4) })
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    geo.setAttribute('aColor', new THREE.BufferAttribute(s.ecol, 4))
    geo.setAttribute('aT', new THREE.BufferAttribute(tt, 2))
    geo.setDrawRange(0, s.edges.length * 2)
    const mat = oldLines ?? linesMaterial(gfx)
    mat.uniforms.uDepth = { value: s.depth }
    s.lines = new THREE.LineSegments(geo, mat)
    s.lines.frustumCulled = false
    s.inner.add(s.lines)
    s.key = ''
  },
  update(m, _t, dt, f, sc) {
    const s = m.s
    if (!s.inner) return
    s.yaw += dt * (m.dragging ? 0 : s.vy + (m.hover ? -s.vy * 0.8 : 0)) * (f > 0.5 ? 1 : 0.6)
    s.vy += (0.11 - s.vy) * (1 - Math.exp(-dt * 0.8))
    s.inner.rotation.set(s.pitch, s.yaw, 0)
    const cd = sc.camera.position.distanceTo(m.group.position), sr = 4.7 * m.group.scale.x
    s.depth.set(cd - sr, cd + sr * 0.9)
    for (const g of s.globe) (g.material as THREE.ShaderMaterial).uniforms.uOpacity!.value = m.homeOpacity * f
    const o = (0.85 + 0.15 * f) * m.homeOpacity
    if (s.pts && s.lines) {
      const pu = s.pts.mat.uniforms, lu = (s.lines.material as THREE.ShaderMaterial).uniforms
      pu.uOpacity.value = o
      lu.uOpacity!.value = o * (0.7 + 0.3 * f)
      pu.uHover.value = m.hover || -1
      pu.uSel.value = m.sel || -1
      pu.uMask.value = 1 - f
      lu.uMask!.value = 1 - f
    }
    const key = `${m.hover}|${m.sel}|${s.filter}|${f > 0.6}`
    if (s.key !== key) {
      s.key = key
      restyle(m)
      // Etiquetas: solo cambian con el foco, el filtro o la sección; su posición la proyecta el shader.
      const focus = m.hover || m.sel, near = focus ? nearOf(s, focus) : null, list: Label[] = []
      if (f > 0.6) s.nodes.forEach((n, i) => {
        const show = near ? near.has(n.num) : s.filter ? n.type === s.filter : n.type === 'project' || n.type === 'subject' || n.deg >= 4
        if (!show || list.length > 13) return
        const p = s.P[i]!
        list.push({ x: p.x, y: p.y, z: p.z, text: n.name, strong: n.num === focus })
      })
      s.labels?.set(list)
    }
    if (s.labels) s.labels.uniforms.uOpacity.value = Math.max(0, (f - 0.6) / 0.4) * m.homeOpacity
  },
  drag(m, dx, dy) {
    const s = m.s
    s.yaw += dx * 0.006
    s.pitch = Math.min(1.1, Math.max(-1.1, s.pitch + dy * 0.005))
    s.vy = Math.min(1.2, Math.max(-1.2, dx * 0.02)) || s.vy
  },
  pickScreen(m, mx, my, sc) {
    const s = m.s
    if (!s.inner) return 0
    let best = 0, bd = 22
    const v = new THREE.Vector3()
    s.nodes.forEach((n, i) => {
      if (s.filter && n.type !== s.filter) return
      const p = sc.project(v.copy(s.P[i]!).applyMatrix4(s.inner!.matrixWorld)), d = Math.hypot(p.x - mx, p.y - my)
      if (d < bd) { bd = d; best = n.num }
    })
    return best
  },
  tip(num, _ctx, m) {
    const n = m.s.nodes.find((x) => x.num === num)
    return n ? { title: n.name, sub: `${ENTITY_ES[n.type]} · ${n.deg} vínculo${n.deg === 1 ? '' : 's'}`, hint: 'clic para fijarla' } : null
  },
  click: () => ({ kind: 'select' }),
  dispose(m) {
    const s = m.s
    if (s.pts) disposeMesh(s.pts.pts)
    if (s.lines) disposeMesh(s.lines)
    for (const g of s.globe) disposeMesh(g)
  }
}
