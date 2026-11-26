/**
 * 3D de datos de los sectores (sobre `world.sectorGroup`): grafo de relaciones, skyline de carga por
 * proyecto y núcleo de documentos del Almacén. Cada pieza recibe datos con `setData` (al cambiar la
 * instantánea, nunca por fotograma) y solo anima mientras su sector está cerca del rumbo.
 * Shaders y formas: prototipo `research/jarvis-hud/visor/src/scene.ts`.
 */
import * as THREE from 'three'
import type { StageFrame } from '@/jarvis/stage/types'
import { BAR_FS, BAR_VS, EDGE_FS, EDGE_VS, NODE_FS, NODE_VS } from './shaders'
import { D, type VisorWorld } from './world'

const ADD = { transparent: true, depthWrite: false, depthTest: false, blending: THREE.CustomBlending, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor, premultipliedAlpha: true } as const

function disposeTree(o: THREE.Object3D): void {
  o.traverse((x) => {
    const m = x as THREE.Mesh
    m.geometry?.dispose()
    const mat = m.material as THREE.Material | THREE.Material[] | undefined
    if (Array.isArray(mat)) mat.forEach((y) => y.dispose())
    else mat?.dispose()
  })
}

// ───────────────────────────── Grafo (Relaciones, sector 5)
export interface GraphNode { readonly id: string; readonly color: string; readonly size: number }
export interface GraphPart {
  setData(nodes: readonly GraphNode[], edges: readonly (readonly [number, number])[]): void
  setHighlight(hover: number, selected: number): void
  /** Nodo más cercano al punto de pantalla (px CSS), o -1. */
  pick(x: number, y: number): number
  /** Posición en pantalla del nodo `i` (para etiquetas DOM). */
  screenOf(i: number): { x: number; y: number; visible: boolean }
  dispose(): void
}

/** Disposición por fuerzas, determinista (semilla por índice) y acotada en iteraciones. */
function layoutGraph(n: number, edges: readonly (readonly [number, number])[]): THREE.Vector3[] {
  const gp = Array.from({ length: n }, (_, i) => new THREE.Vector3(Math.cos(i * 2.4) * 200, Math.sin(i * 1.7) * 160, Math.sin(i * 2.4) * 200))
  const f = gp.map(() => new THREE.Vector3()), d = new THREE.Vector3()
  const iters = n > 40 ? 180 : 320
  for (let it = 0; it < iters; it++) {
    for (const v of f) v.set(0, 0, 0)
    for (let i = 0; i < n; i++)
      for (let j = i + 1; j < n; j++) {
        d.copy(gp[i]!).sub(gp[j]!)
        const l = Math.max(30, d.length())
        d.multiplyScalar(9000 / (l * l * l)); f[i]!.add(d); f[j]!.sub(d)
      }
    for (const [a, b] of edges) {
      d.copy(gp[b]!).sub(gp[a]!)
      const l = d.length()
      d.multiplyScalar(((l - 150) * 0.02) / Math.max(l, 1)); f[a]!.add(d); f[b]!.sub(d)
    }
    for (let i = 0; i < n; i++) { f[i]!.addScaledVector(gp[i]!, -0.02); gp[i]!.add(f[i]!.clampLength(0, 30)) }
  }
  const c = new THREE.Vector3()
  gp.forEach((v) => c.add(v))
  if (n) c.multiplyScalar(1 / n)
  const r = Math.max(1, ...gp.map((v) => v.sub(c).length()))
  const k = Math.min(1, 300 / r) // que quepa en el panel
  gp.forEach((v) => v.multiplyScalar(k))
  return gp
}

export function createGraph(world: VisorWorld): GraphPart {
  const SECTOR = 5
  const root = world.sectorGroup(SECTOR, 0, D + 260, 10)
  const spin = new THREE.Group(); spin.scale.setScalar(1.6); root.add(spin)
  const nodeU = { uPR: { value: 1 }, uTime: { value: 0 } }
  const edgeU = { uTime: { value: 0 }, uPulse: { value: 1 }, uCol: { value: new THREE.Color('#4fb8ff') } }
  const nodeMat = new THREE.ShaderMaterial({ vertexShader: NODE_VS, fragmentShader: NODE_FS, uniforms: nodeU, ...ADD })
  const edgeMat = new THREE.ShaderMaterial({ vertexShader: EDGE_VS, fragmentShader: EDGE_FS, uniforms: edgeU, ...ADD })
  let nodes: THREE.Points | null = null, edgesObj: THREE.LineSegments | null = null, pos: THREE.Vector3[] = [], hi = new Float32Array(0)
  for (const [r, tilt] of [[330, 0.25], [390, -0.4]] as const) {
    const g = new THREE.BufferGeometry().setFromPoints(Array.from({ length: 129 }, (_, i) => new THREE.Vector3(Math.cos((i / 128) * Math.PI * 2) * r, 0, Math.sin((i / 128) * Math.PI * 2) * r)))
    const l = new THREE.Line(g, new THREE.LineBasicMaterial({ color: '#16507e', transparent: true, blending: THREE.AdditiveBlending, depthTest: false }))
    l.rotation.x = Math.PI / 2 - 0.35 + tilt; l.rotation.z = tilt; l.renderOrder = 4; spin.add(l)
  }
  const wp = new THREE.Vector3()
  let hover = -1, sel = -1, hiDirty = false
  const off = world.onFrame((f: StageFrame) => {
    if (!world.near(SECTOR, 0.85)) return
    nodeU.uPR.value = world.pointScale; nodeU.uTime.value = f.time; edgeU.uTime.value = f.time
    // Giro lento solo con movimiento permitido; quieto, las etiquetas no se reescriben.
    if (!f.reducedMotion && !world.idle) { spin.rotation.y += f.dt * 0.06; spin.rotation.x = Math.sin(f.time * 0.13) * 0.14 }
    if (hiDirty && nodes) { for (let i = 0; i < hi.length; i++) hi[i] = i === hover || i === sel ? 1 : 0; (nodes.geometry.attributes.aHi as THREE.BufferAttribute).needsUpdate = true; hiDirty = false }
  })
  return {
    setData(list, edges) {
      if (nodes) { spin.remove(nodes); nodes.geometry.dispose() }
      if (edgesObj) { spin.remove(edgesObj); edgesObj.geometry.dispose() }
      nodes = edgesObj = null
      pos = layoutGraph(list.length, edges)
      if (!list.length) return
      hi = new Float32Array(list.length)
      const ng = new THREE.BufferGeometry()
      ng.setAttribute('position', new THREE.Float32BufferAttribute(pos.flatMap((v) => [v.x, v.y, v.z]), 3))
      ng.setAttribute('aSize', new THREE.Float32BufferAttribute(list.map((n) => n.size), 1))
      ng.setAttribute('aCol', new THREE.Float32BufferAttribute(list.flatMap((n) => new THREE.Color(n.color).toArray()), 3))
      ng.setAttribute('aHi', new THREE.BufferAttribute(hi, 1))
      nodes = new THREE.Points(ng, nodeMat); nodes.renderOrder = 6; nodes.frustumCulled = false
      const p: number[] = [], t: number[] = [], s: number[] = []
      edges.forEach(([a, b], k) => { p.push(...pos[a]!.toArray(), ...pos[b]!.toArray()); t.push(0, 1); const sd = (k * 0.618) % 1; s.push(sd, sd) })
      const eg = new THREE.BufferGeometry()
      eg.setAttribute('position', new THREE.Float32BufferAttribute(p, 3)); eg.setAttribute('aT', new THREE.Float32BufferAttribute(t, 1)); eg.setAttribute('aSeed', new THREE.Float32BufferAttribute(s, 1))
      edgesObj = new THREE.LineSegments(eg, edgeMat); edgesObj.renderOrder = 5; edgesObj.frustumCulled = false
      spin.add(edgesObj, nodes); hiDirty = true
    },
    setHighlight(h, s) { if (h !== hover || s !== sel) { hover = h; sel = s; hiDirty = true } },
    pick(x, y) {
      if (!nodes || !world.near(SECTOR, 0.5)) return -1
      let best = -1, bd = 24
      for (let i = 0; i < pos.length; i++) {
        wp.copy(pos[i]!); nodes.localToWorld(wp)
        const s = world.toScreen(wp), d = Math.hypot(s.x - x, s.y - y)
        if (s.visible && d < bd) { bd = d; best = i }
      }
      return best
    },
    screenOf(i) {
      if (!nodes || !pos[i]) return { x: 0, y: 0, visible: false }
      wp.copy(pos[i]!); nodes.localToWorld(wp)
      return world.toScreen(wp)
    },
    dispose() { off(); root.removeFromParent(); disposeTree(root); nodeMat.dispose(); edgeMat.dispose() }
  }
}

// ───────────────────────────── Skyline (Tareas y proyectos, sector 2)
export interface SkylinePart {
  /** `cells[p][w]` = tareas abiertas del proyecto `p` que vencen en la semana `w` (0 = esta). */
  setData(cells: readonly (readonly number[])[], colors: readonly string[]): void
  /** Columna bajo el punto de pantalla, o null. */
  pick(x: number, y: number): { proj: number; week: number } | null
  dispose(): void
}

export const SKY_WEEKS = 8

export function createSkyline(world: VisorWorld): SkylinePart {
  const SECTOR = 2
  const root = world.sectorGroup(SECTOR, 0, D + 60, -150)
  const spin = new THREE.Group(); spin.rotation.x = 0.42; root.add(spin)
  const grid = new THREE.GridHelper(560, 14, 0x1a5f93, 0x0c3150)
  const gm = grid.material as THREE.Material; gm.transparent = true; gm.blending = THREE.AdditiveBlending; gm.depthTest = false; grid.renderOrder = 4; spin.add(grid)
  const barU = { uGrow: { value: 0 }, uTime: { value: 0 } }
  const mat = new THREE.ShaderMaterial({ vertexShader: BAR_VS, fragmentShader: BAR_FS, uniforms: barU, ...ADD })
  let skyT = 0
  let bars: THREE.InstancedMesh | null = null, heights = new Float32Array(0), rows = 0
  const off = world.onFrame((f) => {
    if (!world.near(SECTOR, 0.85)) return
    const want = world.near(SECTOR, 0.4) ? 1 : 0.05
    barU.uGrow.value += (want - barU.uGrow.value) * (1 - Math.exp(-f.dt * 4)); if (Math.abs(want - barU.uGrow.value) < 0.002) barU.uGrow.value = want
    if (!f.reducedMotion && !world.idle) { skyT += f.dt; spin.rotation.y = Math.sin(skyT * 0.15) * 0.35 + 0.35; barU.uTime.value = skyT }
  })
  const m = new THREE.Matrix4(), inv = new THREE.Matrix4(), box = new THREE.Box3(), r2 = new THREE.Ray(), hit = new THREE.Vector3()
  return {
    setData(cells, colors) {
      if (bars) { spin.remove(bars); bars.geometry.dispose() }
      bars = null; rows = cells.length
      const n = rows * SKY_WEEKS
      if (!n) return
      const geo = new THREE.BoxGeometry(1, 1, 1), col = new Float32Array(n * 3)
      heights = new Float32Array(n)
      bars = new THREE.InstancedMesh(geo, mat, n)
      let k = 0
      cells.forEach((row, p) => row.forEach((v, w) => {
        m.makeScale(34, 1, 34).setPosition((w - (SKY_WEEKS - 1) / 2) * 62, 0, (p - (rows - 1) / 2) * 62)
        bars!.setMatrixAt(k, m); new THREE.Color(colors[p] ?? '#8be9ff').toArray(col, k * 3)
        heights[k] = v > 0 ? 14 + Math.min(v, 12) * 22 : 3; k++
      }))
      geo.setAttribute('aCol', new THREE.InstancedBufferAttribute(col, 3)); geo.setAttribute('aH', new THREE.InstancedBufferAttribute(heights, 1))
      bars.frustumCulled = false; bars.renderOrder = 6; spin.add(bars)
    },
    pick(x, y) {
      if (!bars || !world.near(SECTOR, 0.4)) return null
      const ray = world.ray(x, y).ray
      bars.updateMatrixWorld()
      let best: { k: number; d: number } | null = null
      for (let k = 0; k < heights.length; k++) {
        bars.getMatrixAt(k, m); m.premultiply(bars.matrixWorld); inv.copy(m).invert(); r2.copy(ray).applyMatrix4(inv)
        box.min.set(-0.5, 0, -0.5); box.max.set(0.5, heights[k]! * barU.uGrow.value, 0.5)
        if (r2.intersectBox(box, hit)) { const d = hit.applyMatrix4(m).distanceTo(ray.origin); if (!best || d < best.d) best = { k, d } }
      }
      return best ? { proj: Math.floor(best.k / SKY_WEEKS), week: best.k % SKY_WEEKS } : null
    },
    dispose() { off(); root.removeFromParent(); disposeTree(root); mat.dispose() }
  }
}

// ───────────────────────────── Núcleo de documentos (Almacén, sector 6)
export interface DocCorePart {
  /** Un punto por documento (con tope): `groups` = [color, cuántos, encendidos]. */
  setData(groups: readonly (readonly [string, number, number])[]): void
  dispose(): void
}

const CORE_MAX = 1500

export function createDocCore(world: VisorWorld): DocCorePart {
  const SECTOR = 6
  const root = world.sectorGroup(SECTOR, -6, D + 200, 0)
  const spin = new THREE.Group(); spin.rotation.z = 0.08; root.add(spin)
  const u = { uPR: { value: 1 }, uTime: { value: 0 } }
  const mat = new THREE.ShaderMaterial({ vertexShader: NODE_VS, fragmentShader: NODE_FS, uniforms: u, ...ADD })
  const ring = new THREE.Mesh(new THREE.RingGeometry(250, 258, 96), new THREE.MeshBasicMaterial({ color: '#8be9ff', transparent: true, opacity: 0.5, blending: THREE.AdditiveBlending, depthTest: false, side: THREE.DoubleSide }))
  ring.rotation.x = -Math.PI / 2 + 0.25; ring.renderOrder = 7; root.add(ring)
  let pts: THREE.Points | null = null
  const off = world.onFrame((f) => {
    if (!world.near(SECTOR, 0.85)) return
    u.uPR.value = world.pointScale
    if (f.reducedMotion || world.idle) return
    u.uTime.value = f.time; spin.rotation.y += f.dt * 0.18
    const sy = ((f.time * 0.12) % 1) * 640 - 320
    ring.position.y = sy; (ring.material as THREE.MeshBasicMaterial).opacity = 0.5 * Math.sin(((sy + 320) / 640) * Math.PI)
  })
  return {
    setData(groups) {
      if (pts) { spin.remove(pts); pts.geometry.dispose() }
      pts = null
      const total = groups.reduce((s, g) => s + g[1], 0)
      if (!total) return
      const scale = Math.min(1, CORE_MAX / total), n = Math.max(1, Math.round(total * scale))
      const p = new Float32Array(n * 3), c = new Float32Array(n * 3), sz = new Float32Array(n), col = new THREE.Color()
      let k = 0
      groups.forEach(([hex, count, lit], gi) => {
        const m = Math.round(count * scale), on = Math.round(lit * scale)
        for (let j = 0; j < m && k < n; j++, k++) {
          const t = k / n, a = t * Math.PI * 2 * 26 + gi * 0.6, r = 120 + gi * 26 + Math.sin(k) * 10
          p.set([Math.cos(a) * r, (t - 0.5) * 620, Math.sin(a) * r], k * 3)
          col.set(hex).multiplyScalar(j < on ? 1 : 0.5).toArray(c, k * 3); sz[k] = (j < on ? 6 : 4.5) * (n < 60 ? 2 : 1)
        }
      })
      const g = new THREE.BufferGeometry()
      g.setAttribute('position', new THREE.BufferAttribute(p.subarray(0, k * 3), 3)); g.setAttribute('aCol', new THREE.BufferAttribute(c.subarray(0, k * 3), 3))
      g.setAttribute('aSize', new THREE.BufferAttribute(sz.subarray(0, k), 1)); g.setAttribute('aHi', new THREE.BufferAttribute(new Float32Array(k), 1))
      pts = new THREE.Points(g, mat); pts.renderOrder = 6; pts.frustumCulled = false; spin.add(pts)
    },
    dispose() { off(); root.removeFromParent(); disposeTree(root); mat.dispose() }
  }
}
