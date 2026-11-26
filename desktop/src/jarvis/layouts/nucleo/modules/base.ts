/**
 * Base de los seis instrumentos del astrolabio. Cada uno tiene un anillo «de cabecera» (vista núcleo),
 * sus rótulos en otra malla fija (para leerse siempre aunque el anillo gire) y la versión desplegada
 * (vista sección). Los paneles en DOM los pinta React (`hud/panels`), no el módulo.
 */
import * as THREE from 'three'
import { RingBuilder, TAU, disposeMesh, pickRing, type Gfx, type RingMesh } from '../gl/kit'
import type { Label } from '../gl/labels'
import type { IdMap, NucleoModel } from '../model'

export type ModuleId = 'hoy' | 'tareas' | 'habitos' | 'calendario' | 'relaciones' | 'almacen'

export interface ModuleCtx {
  readonly gfx: Gfx
  readonly ids: IdMap
  model: NucleoModel
}
/** Proyección a px CSS para seleccionar y etiquetar en pantalla. */
export interface SceneCtx {
  readonly camera: THREE.Camera
  project(world: THREE.Vector3): { x: number; y: number }
}

export interface Tip { readonly title: string; readonly sub: string; readonly hint?: string; readonly tone?: 'late' | 'soon' | 'error' }

/** Lo que pide un clic en el anillo; lo ejecuta el anfitrión con la API real. */
export type ClickAction = { kind: 'select' } | { kind: 'toggleTask'; id: string } | { kind: 'toggleHabit'; id: string }

export interface ModuleDef<S = unknown> {
  readonly id: ModuleId
  readonly name: string
  readonly key: string
  readonly rIn: number
  readonly rOut: number
  readonly single?: boolean
  readonly cloud?: boolean
  readonly home: { readonly pos: readonly [number, number, number]; readonly rx: number; readonly rz: number; readonly scale: number; readonly spin: number }
  /** Resumen de una línea (cabecera de sección y descripción del anillo). */
  kpi(ctx: ModuleCtx): string
  buildHome?(b: RingBuilder, labels: RingBuilder, ctx: ModuleCtx, m: Mod<S>): void
  buildDetail(b: RingBuilder, ctx: ModuleCtx, m: Mod<S>): void
  /** Partes dinámicas (satélites, nodos): se rehacen al cambiar los datos. */
  sync?(m: Mod<S>, ctx: ModuleCtx): void
  update?(m: Mod<S>, t: number, dt: number, f: number, s: SceneCtx): void
  pick?(m: Mod<S>, x: number, y: number): number
  pickScreen?(m: Mod<S>, mx: number, my: number, s: SceneCtx): number
  /** Etiquetas en el Stage, en coordenadas del grupo `labelParent`. */
  labels?(m: Mod<S>, f: number): readonly Label[]
  tip(num: number, ctx: ModuleCtx, m: Mod<S>): Tip | null
  click(num: number, ctx: ModuleCtx, m: Mod<S>): ClickAction
  drag?(m: Mod<S>, dx: number, dy: number): void
  dispose?(m: Mod<S>): void
}

export interface Mod<S = unknown> {
  readonly def: ModuleDef<S>
  readonly id: ModuleId
  readonly group: THREE.Group
  readonly spin: THREE.Group
  homeMesh: RingMesh
  labelMesh: RingMesh | null
  detailMesh: RingMesh
  hover: number
  sel: number
  f: number
  intro: number
  boost: number
  spinA: number
  homeOpacity: number
  dragging: boolean
  /** Estado propio del módulo (satélites, grafo…). */
  s: S
  /** Grupo donde cuelgan sus etiquetas (sigue la misma transformación que sus puntos). */
  labelParent: THREE.Object3D
  rebuild(ctx: ModuleCtx): void
  dispose(): void
}

export function makeModule<S>(def: ModuleDef<S>, ctx: ModuleCtx, state: S): Mod<S> {
  const group = new THREE.Group(), spin = new THREE.Group()
  group.add(spin)
  const empty = new RingBuilder(ctx.gfx)
  const m: Mod<S> = {
    def, id: def.id, group, spin, homeMesh: empty.mesh(), labelMesh: null, detailMesh: null as unknown as RingMesh,
    hover: 0, sel: 0, f: 0, intro: 0, boost: 0, spinA: def.home.spin ? Math.random() * TAU : 0, homeOpacity: 0, dragging: false,
    s: state, labelParent: group,
    rebuild(c) {
      const bd = new RingBuilder(c.gfx)
      def.buildDetail(bd, c, m)
      bd.into(m.detailMesh)
      if (!def.single) {
        const h = new RingBuilder(c.gfx), l = new RingBuilder(c.gfx)
        def.buildHome?.(h, l, c, m)
        h.into(m.homeMesh)
        if (m.labelMesh) l.into(m.labelMesh)
      }
      def.sync?.(m, c)
    },
    dispose() {
      def.dispose?.(m)
      disposeMesh(m.detailMesh)
      if (!def.single) { disposeMesh(m.homeMesh); if (m.labelMesh) disposeMesh(m.labelMesh) }
    }
  }
  const bd = new RingBuilder(ctx.gfx)
  def.buildDetail(bd, ctx, m)
  m.detailMesh = bd.mesh()
  if (def.single) {
    disposeMesh(m.homeMesh)
    m.homeMesh = m.detailMesh
    spin.add(m.detailMesh)
  } else {
    const bh = new RingBuilder(ctx.gfx), bl = new RingBuilder(ctx.gfx)
    def.buildHome?.(bh, bl, ctx, m)
    bh.into(m.homeMesh)
    m.labelMesh = bl.mesh(m.homeMesh.material)
    m.detailMesh.visible = false
    spin.add(m.homeMesh)
    group.add(m.labelMesh, m.detailMesh)
  }
  def.sync?.(m, ctx)
  return m
}

export const pickDetail = (m: Mod, x: number, y: number): number => (m.def.pick ? (m.def.pick as ModuleDef['pick'])!(m, x, y) : pickRing(m.detailMesh.userData.hits, x, y))

/** Recorta un rótulo a la longitud de arco disponible. */
export function fit(b: RingBuilder, text: string, size: number, room: number): string {
  if (b.measure(text, size) <= room) return text
  let t = text
  while (t.length > 3 && b.measure(`${t}.`, size) > room) t = t.slice(0, -1)
  return t.length > 3 ? `${t}.` : ''
}
/** El texto del lado de abajo del anillo se lee hacia dentro. */
export const inwardAt = (c: number): boolean => { const x = ((c % 1) + 1) % 1; return x > 0.25 && x < 0.75 }
