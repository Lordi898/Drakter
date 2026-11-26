/**
 * ALMACÉN: disco bajo la peana con los recursos reales agrupados por tipo y, por dentro, su estado de
 * indexación; la corona exterior marca los recursos tocados cada día (60 días) y un barrido gira encima.
 */
import { C, RingBuilder, disposeMesh, type RingMesh } from '../gl/kit'
import { fit, inwardAt, type ModuleDef } from './base'

export interface AlmState { sweep: RingMesh | null; group: number }
export const almState = (): AlmState => ({ sweep: null, group: 0 })

export const almacen: ModuleDef<AlmState> = {
  id: 'almacen', name: 'Almacén', key: '6', single: true, rIn: 2.8, rOut: 4.75,
  home: { pos: [0, -2.85, 0], rx: -1.4, rz: 0, scale: 1.2, spin: 0.03 },
  kpi: ({ model }) => {
    const s = model.store
    if (!s) return 'cargando el almacén…'
    return s.total ? `${s.total} recursos recientes · ${Math.round((s.indexed / s.total) * 100)} % indexado${s.pending ? ` · ${s.pending} pendientes` : ''}` : 'el almacén está vacío'
  },
  buildDetail(b, { model }) {
    const s = model.store
    b.line(2.8, 0, 1, 0.05, { a: 0.7 }).line(4.24, 0, 1, 0.03, { a: 0.45, col: C.blue })
    if (s && s.total) {
      let c = 0
      for (const g of s.groups) {
        const w = g.count / s.total, col = C[g.col]
        b.arc(2.9, 3.52, c + 0.004, c + w - 0.004, { col, a: 0.78, id: g.num })
        const t = fit(b, g.name.toUpperCase(), 0.17, w * 6.28 * 3.21 - 0.1)
        if (t) b.text(t, 3.21, c + w / 2, 0.17, { col: C.white, a: 0.95, inward: inwardAt(c + w / 2) })
        let k = c + 0.004
        for (const kid of g.kids) {
          const kw = (kid.count / g.count) * (w - 0.008)
          b.arc(3.6, 4.12, k + 0.0015, k + kw - 0.0015, { st: 6, col: kid.key === 'failed' ? C.red : kid.key === 'pending' ? C.amber : col, a: 0.9, id: kid.num })
          b.arc(3.6, 3.6 + 0.52 * (kid.key === 'indexed' ? 1 : 0.35), k + 0.0015, k + kw - 0.0015, { col, a: 0.3, hit: false })
          const kt = fit(b, kid.name.toUpperCase(), 0.125, kw * 6.28 * 3.86 - 0.08)
          if (kt) b.text(kt, 3.9, k + kw / 2, 0.125, { col, a: 0.95, inward: inwardAt(k + kw / 2) })
          k += kw
        }
        c += w
      }
      const mx = Math.max(1, ...s.perDay)
      s.perDay.forEach((v, i) => { if (v) b.tick((i + 0.5) / 60, 4.27, 4.3 + (v / mx) * 0.42, 0.11, { st: 0, col: i > 52 ? C.cyan : C.cobalt, a: i > 52 ? 0.95 : 0.6 }) })
    } else if (s) b.text('SIN RECURSOS', 3.4, 0.5, 0.2, { a: 0.7, inward: true })
    b.scale(60, 4.75, 0.04, { major: 10, majorLen: 0.1, a: 0.5 })
  },
  sync(m, { gfx }) {
    if (m.s.sweep) return
    const b = new RingBuilder(gfx)
    for (let i = 0; i < 26; i++) b.arc(2.82, 4.74, -i * 0.006, -(i + 1) * 0.006, { col: C.cyan, a: 0.2 * Math.pow(1 - i / 26, 1.6), st: 5, u1: 0.01, seg: 1, hit: false })
    b.tick(0, 2.82, 4.78, 0.05, { col: C.white })
    m.s.sweep = b.mesh()
    m.spin.add(m.s.sweep)
  },
  update(m, t, _dt, f) {
    const sw = m.s.sweep
    if (!sw) return
    sw.rotation.z = -t * 0.55
    sw.material.uniforms.uOpacity.value = m.detailMesh.material.uniforms.uOpacity.value
    sw.material.uniforms.uMask.value = 1 - f
  },
  tip(num, { model }) {
    for (const g of model.store?.groups ?? []) {
      if (g.num === num) return { title: g.name, sub: `${g.count} recurso${g.count === 1 ? '' : 's'}` }
      const k = g.kids.find((x) => x.num === num)
      if (k) return { title: `${g.name} · ${k.name}`, sub: `${k.count} recurso${k.count === 1 ? '' : 's'}`, tone: k.key === 'failed' ? 'error' : k.key === 'pending' ? 'soon' : undefined }
    }
    return null
  },
  click(num, { model }, m) {
    const g = model.store?.groups.find((x) => x.num === num || x.kids.some((k) => k.num === num))
    if (g) m.s.group = g.num
    return { kind: 'select' }
  },
  dispose(m) {
    if (m.s.sweep) disposeMesh(m.s.sweep)
  }
}
