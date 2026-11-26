/** Geometrías pequeñas con UV 0..1 por cara: el shader holográfico dibuja los bordes como líneas de luz. */
import * as THREE from 'three'

/** Losa curva (sector de anillo con grosor): radios r0..r1, ángulos a0..a1, alturas y0..y1. */
export function arcSlab(r0: number, r1: number, a0: number, a1: number, y0: number, y1: number, seg = 16): THREE.BufferGeometry {
  const P: number[] = [], N: number[] = [], UV: number[] = [], I: number[] = []
  const quad = (a: THREE.Vector3, b: THREE.Vector3, c: THREE.Vector3, d: THREE.Vector3, n: THREE.Vector3, u0: number, u1: number): void => {
    const k = P.length / 3
    for (const v of [a, b, c, d]) {
      P.push(v.x, v.y, v.z)
      N.push(n.x, n.y, n.z)
    }
    UV.push(u0, 0, u1, 0, u1, 1, u0, 1)
    I.push(k, k + 1, k + 2, k, k + 2, k + 3)
  }
  const pt = (r: number, a: number, y: number): THREE.Vector3 => new THREE.Vector3(Math.cos(a) * r, y, Math.sin(a) * r)
  for (let i = 0; i < seg; i++) {
    const t0 = i / seg, t1 = (i + 1) / seg
    const aa = a0 + (a1 - a0) * t0, ab = a0 + (a1 - a0) * t1, am = (aa + ab) / 2
    const out = new THREE.Vector3(Math.cos(am), 0, Math.sin(am))
    quad(pt(r0, aa, y1), pt(r0, ab, y1), pt(r1, ab, y1), pt(r1, aa, y1), new THREE.Vector3(0, 1, 0), t0, t1)
    quad(pt(r0, aa, y0), pt(r0, ab, y0), pt(r1, ab, y0), pt(r1, aa, y0), new THREE.Vector3(0, -1, 0), t0, t1)
    quad(pt(r1, aa, y0), pt(r1, ab, y0), pt(r1, ab, y1), pt(r1, aa, y1), out, t0, t1)
    quad(pt(r0, aa, y0), pt(r0, ab, y0), pt(r0, ab, y1), pt(r0, aa, y1), out.clone().negate(), t0, t1)
  }
  const cap = (a: number): void => {
    const n = new THREE.Vector3(-Math.sin(a), 0, Math.cos(a))
    quad(pt(r0, a, y0), pt(r1, a, y0), pt(r1, a, y1), pt(r0, a, y1), n, 0, 1)
  }
  cap(a0)
  cap(a1)
  const g = new THREE.BufferGeometry()
  g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3))
  g.setAttribute('normal', new THREE.Float32BufferAttribute(N, 3))
  g.setAttribute('uv', new THREE.Float32BufferAttribute(UV, 2))
  g.setIndex(I)
  return g
}

/** Círculo como polilínea cerrada. */
export function circlePts(r: number, n = 96, y = 0): THREE.Vector3[] {
  return Array.from({ length: n + 1 }, (_, i) => {
    const a = (i / n) * Math.PI * 2
    return new THREE.Vector3(Math.cos(a) * r, y, Math.sin(a) * r)
  })
}

/** Segmentos de varias polilíneas en una sola geometría, con `aT` (0..1 a lo largo) y `aSeed` por tramo. */
export function segments(lines: readonly (readonly THREE.Vector3[])[]): THREE.BufferGeometry {
  const P: number[] = [], T: number[] = [], S: number[] = []
  lines.forEach((l, k) => {
    const seed = (k * 0.618) % 1
    for (let i = 0; i < l.length - 1; i++) {
      const a = l[i]!, b = l[i + 1]!
      P.push(a.x, a.y, a.z, b.x, b.y, b.z)
      T.push(i / (l.length - 1), (i + 1) / (l.length - 1))
      S.push(seed, seed)
    }
  })
  const g = new THREE.BufferGeometry()
  g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3))
  g.setAttribute('aT', new THREE.Float32BufferAttribute(T, 1))
  g.setAttribute('aSeed', new THREE.Float32BufferAttribute(S, 1))
  return g
}

/** Aristas de una caja como polilíneas (andamios de las maquetas). */
export function boxEdges(w: number, h: number, d: number, cx = 0, cy = 0, cz = 0): THREE.Vector3[][] {
  const x = w / 2, z = d / 2
  const v = (a: number, b: number, c: number): THREE.Vector3 => new THREE.Vector3(cx + a, cy + b, cz + c)
  const L: THREE.Vector3[][] = []
  for (const [a, c] of [[-x, -z], [x, -z], [x, z], [-x, z]] as const) L.push([v(a, 0, c), v(a, h, c)])
  for (const y of [0, h]) L.push([v(-x, y, -z), v(x, y, -z), v(x, y, z), v(-x, y, z), v(-x, y, -z)])
  return L
}

/** Convierte polilíneas en pares de segmentos sueltos (para `LineSegments`). */
export function pairs(lines: readonly (readonly THREE.Vector3[])[]): THREE.Vector3[][] {
  return lines.flatMap((l) => l.slice(0, -1).map((p, k) => [p, l[k + 1]!]))
}
