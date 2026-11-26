/** PROYECTOS: maquetas sobre una plataforma giratoria; lo sólido está hecho, los andamios quedan. */
import * as THREE from 'three'
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js'
import type { HmProject, HoloSnapshot, PickInfo } from '../../model'
import { arcSlab, boxEdges, pairs, segments } from '../geo'
import type { Materials } from '../materials'
import { base, C, clamp01, clearInstancedPick, ease, instanced, pickInstanced, stationState, tmpM, tmpP, tmpQ, tmpS, W, type Station, type Tag } from './base'

const OFFS = [[-0.52, -0.52], [0.52, -0.52], [-0.52, 0.52], [0.52, 0.52]] as const
const COLORS = [0x67d8ff, 0x8fb4ff, 0x7df0e0, 0xb9d9ff]

/** Pseudoaleatorio estable por proyecto: la maqueta no cambia de forma entre recargas. */
function heights(id: string, n: number): number[] {
  let h = 2166136261
  for (let i = 0; i < id.length; i++) h = Math.imul(h ^ id.charCodeAt(i), 16777619)
  return Array.from({ length: n }, () => {
    h = Math.imul(h ^ (h >>> 13), 1274126177)
    return 0.25 + ((h >>> 0) % 1000) / 1000 * 0.75
  })
}

export function proyectos(M: Materials, pos: THREE.Vector3): Station {
  const b = base(M, 'proyectos', 'Proyectos', '4', pos, 1.55, 2.4)
  let spin: THREE.Group | null = null
  let projects: readonly HmProject[] = []
  let bl: { p: number; x: number; z: number; h: number }[] = []
  let tallest: number[] = []
  let builds: THREE.InstancedMesh | null = null
  let picked = -1
  let ang = 0
  /** Las maquetas ya están levantadas: sus matrices no cambian (gira el grupo, no las instancias). */
  let settled = false

  const s: Station = {
    ...stationState(b),
    setData(snap: HoloSnapshot) {
      const root = b.rebuild()
      projects = snap.projects.items.slice(0, 4)
      spin = new THREE.Group()
      root.add(spin)
      spin.add(new THREE.Mesh(arcSlab(1.3, 1.42, 0, Math.PI * 2, 0, 0.07, 96), b.reg(M.holoMat({ color: C.ice, fill: 0.25 }))))
      const plots = instanced(new THREE.BoxGeometry(0.92, 0.04, 0.92), b.reg(M.holoMat({ color: C.ice, fill: 0.12 })), projects.length)
      bl = []
      tallest = []
      const scaffold: THREE.Vector3[][] = []
      const rings: THREE.BufferGeometry[] = []
      projects.forEach((p, i) => {
        const [ox, oz] = OFFS[i]!
        tmpM.makeTranslation(ox, 0.1, oz)
        plots.setMatrixAt(i, tmpM)
        const n = Math.max(3, Math.min(9, p.total || 3))
        const hs = heights(p.id, n)
        const solid = Math.round(n * p.progress)
        tallest.push(Math.max(...hs.map((v) => 0.2 + v * 1.25)))
        hs.forEach((v, j) => {
          const x = ox - 0.25 + (j % 3) * 0.25, z = oz - 0.25 + Math.floor(j / 3) * 0.25, h = 0.2 + v * 1.25
          if (j < solid) bl.push({ p: i, x, z, h })
          else scaffold.push(...boxEdges(0.17, h, 0.17, x, 0.12, z))
        })
        if (p.progress > 0.005) {
          const rg = arcSlab(0.5, 0.55, -Math.PI / 2, -Math.PI / 2 + p.progress * Math.PI * 2, 0.12, 0.15, 32)
          rg.translate(ox, 0, oz)
          rings.push(rg)
        }
      })
      spin.add(plots)
      builds = instanced(new THREE.BoxGeometry(1, 1, 1), b.reg(M.holoMat({ color: C.ice, fill: 0.09, fresnel: 0.5 })), bl.length)
      bl.forEach((x, i) => builds!.setColorAt(i, new THREE.Color(COLORS[x.p] ?? C.ice)))
      spin.add(builds)
      if (scaffold.length) spin.add(new THREE.LineSegments(segments(pairs(scaffold)), b.reg(M.lineMat(C.steel, 0.32))))
      if (rings.length) {
        spin.add(new THREE.Mesh(mergeGeometries(rings), b.reg(M.holoMat({ color: C.white, fill: 0.55 }))))
        for (const g of rings) g.dispose()
      }
      const lead = projects[0]
      s.metric =
        snap.projects.load !== 'ready' ? (snap.projects.load === 'error' ? 'sin datos' : 'cargando…')
          : lead ? `${snap.projects.items.length} activos · ${lead.name} al ${Math.round(lead.progress * 100)} %` : 'sin proyectos activos'
      picked = -1
      settled = false
    },
    update(_t, dt, c) {
      b.apply(s)
      if (!spin || !builds) return
      ang += dt * (c.reduced ? 0 : 0.12 * (1 - s.focus * 0.6) * (picked >= 0 ? 0.15 : 1))
      spin.rotation.y = ang
      if (settled && s.build >= 1) return
      settled = s.build >= 1
      bl.forEach((x, i) => {
        const g = ease(clamp01(s.build * 1.8 - i * 0.03)), hh = x.h * g + 0.001
        tmpM.compose(tmpP.set(x.x, 0.12 + hh / 2, x.z), tmpQ.identity(), tmpS.set(0.17, hh, 0.17))
        builds!.setMatrixAt(i, tmpM)
      })
      builds.instanceMatrix.needsUpdate = true
      builds.computeBoundingSphere()
    },
    pick(rc): PickInfo | null {
      picked = pickInstanced(rc, builds)
      const p = projects[bl[picked]?.p ?? -1]
      if (!p) return null
      return {
        key: 'proj:' + p.id,
        title: p.name,
        sub: `${Math.round(p.progress * 100)} %${p.due ? ` · objetivo ${p.due}` : ''}`,
        lines: [`${p.completed}/${p.total} tareas hechas`, ...(p.overdue ? [`${p.overdue} vencidas`] : [])],
        ref: { kind: 'project', id: p.id }
      }
    },
    clearPick() {
      picked = -1
      clearInstancedPick(builds)
    },
    tags(): Tag[] {
      if (!spin) return []
      return projects.map((p, i) => ({
        p: W(spin!, OFFS[i]![0], 0.4 + (tallest[i] ?? 1) * s.build, OFFS[i]![1]),
        t: `${p.name} ${Math.round(p.progress * 100)} %`,
        k: p.overdue > 0 ? 'warn' : i === 0 ? 'hi' : ''
      }))
    },
    dispose: () => b.dispose()
  }
  return s
}
