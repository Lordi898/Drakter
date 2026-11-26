/**
 * Base de las estaciones de la Holomesa: cada sección es un holograma que se alza sobre un emisor de la
 * mesa, con su cono de proyección, un volumen invisible para el ratón y un selector de elementos. El
 * contenido se reconstruye entero cuando cambian los datos (es raro y barato); el cono y el volumen no.
 */
import * as THREE from 'three'
import type { CharacterState } from '@/character/types'
import type { HoloSnapshot, PickInfo, SectionId } from '../../model'
import { disposeTree, type Materials } from '../materials'

export type TagKind = 'hi' | 'warn' | ''

/** Etiqueta anclada a un punto del holograma (se dibuja en el Stage, no en el DOM). */
export interface Tag {
  readonly p: THREE.Vector3
  readonly t: string
  readonly k: TagKind
}

/** Contexto por fotograma que comparten las estaciones. */
export interface Ctx {
  readonly camera: THREE.Camera
  /** 0 Ahorro · 0,6 Equilibrado · 1 Cine */
  readonly quality: number
  readonly reduced: boolean
  readonly agent: CharacterState
  readonly voice: number
  readonly nowHours: number
  /** Hay un trabajo de indexado en marcha (haz del Almacén). */
  readonly indexing: boolean
}

export interface Station {
  readonly id: SectionId
  readonly name: string
  readonly key: string
  readonly pos: THREE.Vector3
  readonly padR: number
  readonly height: number
  readonly yaw: number
  readonly group: THREE.Group
  readonly proxy: THREE.Mesh
  /** Resumen de una línea para el carril y la etiqueta de la vista general. */
  metric: string
  build: number
  dim: number
  hover: number
  focus: number
  setData(s: HoloSnapshot): void
  update(t: number, dt: number, c: Ctx): void
  pick(rc: THREE.Raycaster): PickInfo | null
  clearPick(): void
  tags(): Tag[]
  dispose(): void
}

export const C = { ice: 0x6fd6ff, deep: 0x2f86d8, white: 0xdff6ff, teal: 0x6cf2d6, steel: 0x8fb4ff, warm: 0xffd08a, amber: 0xffb050, past: 0x1f5f8f, dark: 0x15405f }
export const ease = (x: number): number => (x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x))
export const clamp01 = (x: number): number => Math.min(1, Math.max(0, x))
export const tmpM = new THREE.Matrix4()
export const tmpQ = new THREE.Quaternion()
export const tmpS = new THREE.Vector3()
export const tmpP = new THREE.Vector3()
export const yAxis = new THREE.Vector3(0, 1, 0)
/** Punto local de `o` en coordenadas de mundo (vector nuevo: las etiquetas lo guardan). */
export const W = (o: THREE.Object3D, x: number, y: number, z: number): THREE.Vector3 => o.localToWorld(new THREE.Vector3(x, y, z))

const fq = new THREE.Quaternion()
/** Orienta un plano hacia la cámara aunque su padre esté girado. */
export function face(o: THREE.Object3D, cam: THREE.Camera): void {
  o.parent!.getWorldQuaternion(fq)
  o.quaternion.copy(fq.invert().multiply(cam.quaternion))
}

/** Raycast contra una malla instanciada; deja resaltada la instancia tocada (o ninguna). */
export function pickInstanced(rc: THREE.Raycaster, mesh: THREE.InstancedMesh | null): number {
  if (!mesh || mesh.count === 0) return -1
  const id = rc.intersectObject(mesh, false)[0]?.instanceId ?? -1
  ;(mesh.material as THREE.ShaderMaterial).uniforms.uPick!.value = id
  return id
}

export function clearInstancedPick(mesh: THREE.InstancedMesh | null): void {
  if (mesh) (mesh.material as THREE.ShaderMaterial).uniforms.uPick!.value = -1
}

/** InstancedMesh que admite 0 elementos (Three necesita al menos una instancia reservada). */
export function instanced(geo: THREE.BufferGeometry, mat: THREE.Material, n: number): THREE.InstancedMesh {
  const m = new THREE.InstancedMesh(geo, mat, Math.max(1, n))
  m.count = n
  return m
}

export interface Base {
  readonly id: SectionId
  readonly name: string
  readonly key: string
  readonly pos: THREE.Vector3
  readonly padR: number
  readonly height: number
  readonly yaw: number
  readonly group: THREE.Group
  /** Orientado a la cámara general. */
  readonly body: THREE.Group
  readonly proxy: THREE.Mesh
  readonly M: Materials
  /** Registra un material del contenido (se libera al reconstruir). */
  reg<T extends THREE.ShaderMaterial>(m: T): T
  /** Vacía el contenido anterior y devuelve un grupo nuevo dentro de `body`. */
  rebuild(): THREE.Group
  /** Copia build/dim/hover/focus a los uniformes de todos los materiales. */
  apply(st: { build: number; dim: number; hover: number; focus: number }): void
  dispose(): void
}

export function base(M: Materials, id: SectionId, name: string, key: string, pos: THREE.Vector3, padR: number, height: number): Base {
  const group = new THREE.Group()
  group.position.copy(pos)
  const yaw = Math.atan2(0 - pos.x, 18 - pos.z)
  const body = new THREE.Group()
  body.rotation.y = yaw
  group.add(body)
  const fixed: THREE.ShaderMaterial[] = []
  let content: THREE.ShaderMaterial[] = []
  const prep = <T extends THREE.ShaderMaterial>(m: T): T => {
    if (m.uniforms.uHeight) {
      m.uniforms.uBase!.value = 0
      m.uniforms.uHeight.value = height
    }
    return m
  }
  const beam = new THREE.Mesh(new THREE.CylinderGeometry(padR * 1.08, padR * 0.92, height * 0.95, 48, 1, true), prep(M.beamMat()))
  fixed.push(beam.material)
  beam.position.y = height * 0.475
  group.add(beam)
  const proxy = new THREE.Mesh(new THREE.CylinderGeometry(padR * 1.2, padR * 1.2, height + 0.6, 12), new THREE.MeshBasicMaterial({ visible: false }))
  proxy.position.y = (height + 0.6) / 2
  group.add(proxy)
  let holder: THREE.Group | null = null
  return {
    id, name, key, pos, padR, height, yaw, group, body, proxy, M,
    reg(m) {
      content.push(prep(m))
      return m
    },
    rebuild() {
      if (holder) {
        body.remove(holder)
        disposeTree(holder)
      }
      content = []
      holder = new THREE.Group()
      body.add(holder)
      return holder
    },
    apply(st) {
      const hv = st.hover + st.focus * 0.25
      for (const list of [fixed, content])
        for (const m of list) {
          const u = m.uniforms
          if (u.uBuild) u.uBuild.value = st.build
          if (u.uDim) u.uDim.value = st.dim
          if (u.uHover) u.uHover.value = hv
        }
    },
    dispose() {
      disposeTree(group)
    }
  }
}

/** Plano con halo que mira a la cámara (núcleos de luz). */
export function billboard(M: Materials, color: number, size: number, strength = 1): THREE.Mesh {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(size, size), M.glowMat(color, strength))
  m.renderOrder = 2
  return m
}

/** Estado común mutable de una estación. */
export function stationState(b: Base) {
  return {
    id: b.id, name: b.name, key: b.key, pos: b.pos, padR: b.padR, height: b.height, yaw: b.yaw,
    group: b.group, proxy: b.proxy,
    metric: '', build: 0, dim: 0, hover: 0, focus: 0
  }
}
