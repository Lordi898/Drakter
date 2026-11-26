/** Las 7 estaciones en abanico alrededor de la mesa (el avatar preside al fondo) y el orbe de reserva. */
import * as THREE from 'three'
import type { CharacterState } from '@/character/types'
import { circlePts } from '../geo'
import type { Materials } from '../materials'
import { HEAD } from '../table'
import { almacen } from './almacen'
import { billboard, C, face, type Ctx, type Station } from './base'
import { calendario } from './calendario'
import { habitos } from './habitos'
import { hoy } from './hoy'
import { proyectos } from './proyectos'
import { relaciones } from './relaciones'
import { tareas } from './tareas'

export type { Ctx, Station, Tag } from './base'

export function createStations(M: Materials): Station[] {
  const at = (deg: number, r = 6.6): THREE.Vector3 => {
    const a = (deg * Math.PI) / 180
    return new THREE.Vector3(Math.sin(a) * r, 0, -Math.cos(a) * r)
  }
  return [hoy(M), calendario(M, at(-62)), tareas(M, at(-108)), proyectos(M, at(-150, 6.9)), habitos(M, at(150, 6.9)), relaciones(M, at(108)), almacen(M, at(62))]
}

export interface Orb {
  readonly group: THREE.Group
  update(t: number, dt: number, c: Ctx, visible: number): void
}

const ORB_COLOR: Partial<Record<CharacterState, number>> = { error: 0xffa060, success: 0xf4fbff, offline: 0x2a4a66 }

/** Orbe holográfico propio: preside la mesa mientras el avatar se construye o si no puede cargarse. */
export function createOrb(M: Materials): Orb {
  const group = new THREE.Group()
  group.position.set(HEAD.x, 2.35, HEAD.z)
  const N = 900, P: number[] = [], S: number[] = [], Z: number[] = []
  for (let i = 0; i < N; i++) {
    const y = 1 - (i / (N - 1)) * 2, rr = Math.sqrt(1 - y * y), th = i * 2.399963
    P.push(Math.cos(th) * rr * 0.9, y * 0.9, Math.sin(th) * rr * 0.9)
    S.push(0.5 + Math.random() * 0.8)
    Z.push(Math.random())
  }
  const g = new THREE.BufferGeometry()
  g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3))
  g.setAttribute('aSize', new THREE.Float32BufferAttribute(S, 1))
  g.setAttribute('aSeed', new THREE.Float32BufferAttribute(Z, 1))
  const pm = M.pointMat(0x8fe2ff, 1.5)
  const pts = new THREE.Points(g, pm)
  group.add(pts)
  const rings = [1.15, 1.32].map((r, i) => {
    const l = new THREE.Line(new THREE.BufferGeometry().setFromPoints(circlePts(r, 128)), M.lineMat(i ? C.white : C.ice, 0.6))
    group.add(l)
    return l
  })
  const core = billboard(M, 0xbff0ff, 2.2, 1.2)
  group.add(core)
  const beam = new THREE.Mesh(new THREE.CylinderGeometry(1.0, 1.3, 2.3, 48, 1, true), M.beamMat())
  beam.position.y = -1.2
  group.add(beam)
  const col = new THREE.Color()
  const uColor = pm.uniforms.uColor!.value as THREE.Color
  return {
    group,
    update(t, dt, c, vis) {
      group.visible = vis > 0.01
      if (!group.visible) return
      const st = c.agent, k = c.reduced ? 0.2 : 1
      pts.rotation.y += dt * (st === 'thinking' ? 1.2 : st === 'executing' ? 0.8 : 0.25) * k
      const s = 0.9 + Math.sin(t * 1.6) * 0.03 * k + c.voice * 0.35 + (st === 'listening' ? 0.08 : 0)
      pts.scale.setScalar(s * vis)
      rings[0]!.rotation.set(1.2 + Math.sin(t * 0.4) * 0.2 * k, t * 0.5 * k, 0)
      rings[1]!.rotation.set(1.9, 0, t * 0.3 * k)
      face(core, c.camera)
      core.scale.setScalar((0.8 + c.voice * 0.9) * vis)
      col.set(ORB_COLOR[st] ?? 0x8fe2ff)
      uColor.lerp(col, Math.min(1, dt * 4))
    }
  }
}
