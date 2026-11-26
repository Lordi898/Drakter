/** RELACIONES: red flotante con las relaciones reales (disposición por fuerzas, calculada al cambiar los datos). */
import * as THREE from 'three'
import type { EntityType } from '@/modules/relationships/types'
import { ENTITY_TYPE_LABEL } from '@/modules/relationships/types'
import type { HmNode, HoloSnapshot, PickInfo } from '../../model'
import { circlePts, segments } from '../geo'
import type { Materials } from '../materials'
import { base, billboard, C, face, stationState, type Station, type Tag } from './base'

const CY = 2.05
const MAX_NODES = 60

const KIND_COLOR: Record<EntityType, number> = {
  project: 0x67d8ff, subject: 0x9fb8ff, task: 0x4f9cf0, habit: 0x7ff0d8, calendar_event: 0x6cf2d6,
  time_block: 0xffd08a, class_session: 0x8fa8ff, resource: 0xc6e6ff, folder: 0x8fb4cc
}

export function relaciones(M: Materials, pos: THREE.Vector3): Station {
  const b = base(M, 'relaciones', 'Relaciones', '8', pos, 1.45, 3.9)
  let net: THREE.Group | null = null
  let shell: THREE.LineSegments | null = null
  let hub: THREE.Mesh | null = null
  let pts: THREE.Points | null = null
  let nodes: HmNode[] = []
  let E: (readonly [number, number])[] = []
  let P: THREE.Vector3[] = []
  let deg: number[] = []
  let hubIdx = -1
  let picked = -1

  const s: Station = {
    ...stationState(b),
    setData(snap: HoloSnapshot) {
      const root = b.rebuild()
      // Los nodos más conectados primero; los sueltos no aportan a la red.
      const allDeg = new Map<string, number>()
      for (const [a, c] of snap.graph.edges) {
        allDeg.set(a, (allDeg.get(a) ?? 0) + 1)
        allDeg.set(c, (allDeg.get(c) ?? 0) + 1)
      }
      nodes = snap.graph.nodes.filter((n) => allDeg.has(n.id)).sort((a, c) => (allDeg.get(c.id) ?? 0) - (allDeg.get(a.id) ?? 0)).slice(0, MAX_NODES)
      const idx = new Map(nodes.map((n, i) => [n.id, i]))
      E = snap.graph.edges.flatMap(([a, c]) => {
        const ia = idx.get(a), ic = idx.get(c)
        return ia !== undefined && ic !== undefined && ia !== ic ? [[ia, ic] as const] : []
      })
      deg = nodes.map((_, i) => E.filter(([a, c]) => a === i || c === i).length)
      hubIdx = deg.length ? deg.indexOf(Math.max(...deg)) : -1
      // Disposición por fuerzas (semilla fija: la red no baila entre recargas).
      let sd = 3
      const r = (): number => (sd = (sd * 16807) % 2147483647) / 2147483647 - 0.5
      P = nodes.map((_, i) => (i === hubIdx ? new THREE.Vector3() : new THREE.Vector3(r(), r(), r()).multiplyScalar(2)))
      const V = P.map(() => new THREE.Vector3()), f = new THREE.Vector3()
      for (let it = 0; it < 220; it++) {
        for (let i = 0; i < P.length; i++)
          for (let j = i + 1; j < P.length; j++) {
            f.subVectors(P[i]!, P[j]!)
            f.multiplyScalar(0.012 / Math.max(0.02, f.lengthSq()))
            V[i]!.add(f)
            V[j]!.sub(f)
          }
        for (const [a, c] of E) {
          f.subVectors(P[c]!, P[a]!)
          f.multiplyScalar((f.length() - 0.55) * 0.04)
          V[a]!.add(f)
          V[c]!.sub(f)
        }
        for (let i = 0; i < P.length; i++) {
          V[i]!.addScaledVector(P[i]!, -0.004)
          if (i !== hubIdx) P[i]!.add(V[i]!)
          V[i]!.multiplyScalar(0.6)
        }
      }
      const maxR = Math.max(0.001, ...P.map((p) => p.length()))
      for (const p of P) p.multiplyScalar(1.3 / maxR).add(new THREE.Vector3(0, CY, 0))

      net = new THREE.Group()
      net.scale.setScalar(1.25)
      net.position.y = -0.5
      root.add(net)
      pts = null
      hub = null
      if (nodes.length) {
        const g = new THREE.BufferGeometry().setFromPoints(P)
        g.setAttribute('aSize', new THREE.Float32BufferAttribute(nodes.map((_, i) => (i === hubIdx ? 3.2 : 1.1 + Math.sqrt(deg[i]!) * 0.55)), 1))
        g.setAttribute('aSeed', new THREE.Float32BufferAttribute(nodes.map((_, i) => (i * 0.37) % 1), 1))
        g.setAttribute('aCol', new THREE.Float32BufferAttribute(nodes.flatMap((n, i) => new THREE.Color(i === hubIdx ? 0xffffff : KIND_COLOR[n.kind]).toArray()), 3))
        pts = new THREE.Points(g, b.reg(M.pointMat(C.ice, 8)))
        net.add(pts)
        if (E.length) net.add(new THREE.LineSegments(segments(E.map(([a, c]) => [P[a]!, P[c]!])), b.reg(M.lineMat(C.ice, 0.75, true))))
        hub = billboard(M, 0xbff0ff, 1.1, 0.9)
        b.reg(hub.material as THREE.ShaderMaterial)
        hub.position.copy(P[hubIdx]!)
        net.add(hub)
      }
      shell = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.IcosahedronGeometry(1.62, 1)), b.reg(M.lineMat(C.ice, 0.22)))
      shell.position.y = CY
      net.add(shell)
      const eq = new THREE.Line(new THREE.BufferGeometry().setFromPoints(circlePts(1.75, 96)), b.reg(M.lineMat(C.ice, 0.4)))
      eq.position.y = CY
      net.add(eq)
      s.metric =
        snap.graph.load !== 'ready' ? (snap.graph.load === 'error' ? 'sin datos' : 'cargando…')
          : nodes.length ? `${nodes.length} entidades · ${E.length} relaciones` : 'aún no hay relaciones'
      picked = -1
    },
    update(t, dt, c) {
      b.apply(s)
      if (!net) return
      net.rotation.y += dt * (c.reduced ? 0 : 0.09 * (picked >= 0 ? 0.08 : 1))
      if (shell && !c.reduced) {
        shell.rotation.y = -t * 0.05
        shell.rotation.x = t * 0.03
      }
      if (hub) face(hub, c.camera)
      if (pts) (pts.material as THREE.ShaderMaterial).uniforms.uPick!.value = picked
    },
    pick(rc): PickInfo | null {
      if (!pts) return null
      rc.params.Points = { threshold: 0.09 }
      picked = rc.intersectObject(pts, false)[0]?.index ?? -1
      const n = nodes[picked]
      if (!n) return null
      const nb = E.filter(([a, c]) => a === picked || c === picked).map(([a, c]) => nodes[a === picked ? c : a]!.label)
      return {
        key: 'g:' + n.id,
        title: n.label,
        sub: `${ENTITY_TYPE_LABEL[n.kind].toLowerCase()} · ${nb.length} relaciones`,
        lines: [nb.slice(0, 4).join(', ') + (nb.length > 4 ? '…' : '')],
        ref: { kind: 'entity', id: n.id, entityType: n.kind }
      }
    },
    clearPick() {
      picked = -1
    },
    tags(): Tag[] {
      if (!net) return []
      return nodes.flatMap((n, i) => (i === hubIdx || deg[i]! >= 3 ? [{ p: net!.localToWorld(P[i]!.clone()), t: n.label, k: i === hubIdx ? ('hi' as const) : ('' as const) }] : [])).slice(0, 14)
    },
    dispose: () => b.dispose()
  }
  return s
}
