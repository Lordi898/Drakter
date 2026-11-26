/**
 * Kit gráfico de Núcleo: luz aditiva pura con el brillo (núcleo fino + halo) calculado en el shader de
 * cada trazo, sin postprocesado. Todo lo que es «anillo» sale de `RingBuilder` (una malla = una llamada).
 * Portado del prototipo de drakter-97 (`gl/kit.js`). Uniformes y atlas viven en un `Gfx` por instancia
 * para poder liberarlo todo al salir de Jarvis.
 */
import * as THREE from 'three'

export const TAU = Math.PI * 2
export type RGB = readonly [number, number, number]
const hex = (h: number): RGB => [((h >> 16) & 255) / 255, ((h >> 8) & 255) / 255, (h & 255) / 255]

export const C = {
  ice: hex(0xbfeaff), cyan: hex(0x4fd8ff), blue: hex(0x1e90ff), cobalt: hex(0x1b5fd0), deep: hex(0x0f3f9c),
  white: hex(0xf2fbff), amber: hex(0xffb347), red: hex(0xff4d5e), warm: hex(0xfff3d6),
  teal: hex(0x3ef0d0), indigo: hex(0x7b8cff), violet: hex(0xb08cff)
} as const
export type ColorName = keyof typeof C
export const CSS: Readonly<Record<ColorName, string>> = {
  ice: '#bfeaff', cyan: '#4fd8ff', blue: '#1e90ff', cobalt: '#1b5fd0', deep: '#0f3f9c', white: '#f2fbff',
  amber: '#ffb347', red: '#ff4d5e', warm: '#fff3d6', teal: '#3ef0d0', indigo: '#7b8cff', violet: '#b08cff'
}
/** Tonos fríos para distinguir series (proyectos, asignaturas, carpetas). */
export const SERIES: readonly ColorName[] = ['cyan', 'teal', 'indigo', 'violet', 'ice', 'blue']

type U<T> = { value: T }
export interface Uniforms {
  readonly uTime: U<number>
  /** Píxeles físicos por unidad a distancia 1 (tamaño de puntos). */
  readonly uPx: U<number>
  readonly uAtlas: U<THREE.Texture | null>
  /** Elipse del avatar en px físicos (cx, cy, rx, ry): lo que queda detrás se enmascara. */
  readonly uCore: U<THREE.Vector4>
  readonly uCoreZ: U<number>
  readonly uDepth: U<THREE.Vector2>
  readonly uVoice: U<number>
  /** Tamaño del lienzo en px físicos (etiquetas en pantalla). */
  readonly uView: U<THREE.Vector2>
  /** px físicos por px CSS (tamaño de las etiquetas). */
  readonly uLabelScale: U<number>
}

export interface Glyph { u0: number; u1: number; v0: number; v1: number; adv: number }
export interface Glyphs { map: Record<string, Glyph>; cw: number; ch: number; pad: number }

/** Contexto gráfico de una instancia de Núcleo. */
export interface Gfx {
  readonly U: Uniforms
  readonly glyphs: Glyphs
  /** Todo lo creado con el kit, para `dispose`. */
  track<T extends { dispose(): void }>(thing: T): T
  dispose(): void
}

export function createGfx(): Gfx {
  const owned = new Set<{ dispose(): void }>()
  const U: Uniforms = {
    uTime: { value: 0 }, uPx: { value: 800 }, uAtlas: { value: null },
    uCore: { value: new THREE.Vector4(0, 0, 1, 1) }, uCoreZ: { value: 17 }, uDepth: { value: new THREE.Vector2(10, 24) },
    uVoice: { value: 0 }, uView: { value: new THREE.Vector2(1, 1) }, uLabelScale: { value: 1 }
  }
  const glyphs: Glyphs = { map: {}, cw: 0, ch: 0, pad: 0 }
  const gfx: Gfx = {
    U, glyphs,
    track(thing) {
      owned.add(thing)
      return thing
    },
    dispose() {
      for (const o of owned) o.dispose()
      owned.clear()
    }
  }
  makeAtlas(gfx)
  return gfx
}

/** Luz aditiva que deja intacto el alfa del lienzo: el HUD se suma a lo que haya debajo (fondo y avatar). */
export function additive<M extends THREE.Material>(mat: M): M {
  mat.blending = THREE.CustomBlending
  mat.blendEquation = THREE.AddEquation
  mat.blendSrc = THREE.OneFactor
  mat.blendDst = THREE.OneFactor
  mat.blendSrcAlpha = THREE.ZeroFactor
  mat.blendDstAlpha = THREE.OneFactor
  mat.depthTest = false
  mat.depthWrite = false
  mat.transparent = true
  return mat
}

const COMMON_FS = /* glsl */ `
uniform vec4 uCore; uniform float uCoreZ; uniform vec2 uDepth; uniform float uMask;
float depthFade(float z){ return mix(1.3, 0.3, clamp((z-uDepth.x)/(uDepth.y-uDepth.x),0.0,1.0)); }
float lightGain(vec3 c){ float hot = smoothstep(0.82, 0.96, min(c.r, min(c.g, c.b))), warm = smoothstep(0.1, 0.3, c.r - c.b); return mix(0.74, 1.9, hot) + warm*0.7; }
float coreMask(float z){ float e = length((gl_FragCoord.xy-uCore.xy)/uCore.zw); float behind = smoothstep(uCoreZ+0.1, uCoreZ+0.9, z); return 1.0 - uMask*behind*(1.0-smoothstep(0.72,1.06,e))*0.95; }
`

const ARC_VS = /* glsl */ `
attribute vec4 aColor; attribute vec3 aMeta; attribute vec2 aUv;
varying vec4 vColor; varying vec3 vMeta; varying vec2 vUv; varying float vZ;
void main(){ vec4 mv = modelViewMatrix*vec4(position,1.0); vZ = -mv.z; vColor = aColor; vMeta = aMeta; vUv = aUv; gl_Position = projectionMatrix*mv; }`
const ARC_FS = /* glsl */ `
precision highp float;
uniform float uTime, uReveal, uHover, uSel, uOpacity, uBoost; uniform sampler2D uAtlas;
varying vec4 vColor; varying vec3 vMeta; varying vec2 vUv; varying float vZ;
${COMMON_FS}
void main(){
  float st = vMeta.x, d = abs(vUv.y-0.5)*2.0, fy = fwidth(vUv.y)*2.0+1e-5, fx = fwidth(vUv.x)+1e-5, a;
  if (st < 0.5) {
    float ex = clamp(min(vUv.x, 1.0-vUv.x)/fx, 0.0, 1.0), rim = smoothstep(0.62, 1.0, d);
    a = smoothstep(1.0, 1.0-fy, d)*ex*(0.4 + 0.6*rim*rim);
  } else if (st < 1.5) {
    a = (smoothstep(0.2+fy, 0.2, d) + 0.4*exp(-d*d*5.5))*(1.0-smoothstep(0.86, 1.0, d));
  } else if (st < 2.5) {
    float f = fract(vUv.x); a = smoothstep(0.0, fx, f)*smoothstep(0.6, 0.6-fx, f)*smoothstep(1.0, 1.0-fy, d)*0.9;
  } else if (st < 3.5) {
    a = texture2D(uAtlas, vUv).r;
  } else if (st < 4.5) {
    float f = fract(vUv.x - uTime*0.11);
    a = (smoothstep(0.2+fy, 0.2, d) + 0.4*exp(-d*d*5.5))*(1.0-smoothstep(0.86, 1.0, d))*(0.2 + 0.8*f*f*f);
  } else if (st < 5.5) {
    a = smoothstep(1.0, 1.0-fy, d)*(0.12 + 0.42*step(0.5, fract(vUv.x + vUv.y*0.7)));
  } else {
    float m = min(min(vUv.x, 1.0-vUv.x)/fx, (1.0-d)/fy);
    a = clamp(m, 0.0, 1.0)*(0.06 + 0.94*(1.0-smoothstep(1.0, 2.4, m)));
  }
  float lead = (1.0-step(0.9995, uReveal))*smoothstep(0.06, 0.0, uReveal-vMeta.z);
  a *= step(vMeta.z, uReveal)*(1.0+3.0*lead);
  float h = 1.0-step(0.5, abs(vMeta.y-uHover)), s = 1.0-step(0.5, abs(vMeta.y-uSel));
  vec3 col = mix(vColor.rgb, vec3(1.0), 0.42*max(h, s));
  a *= 1.0 + 1.25*h + s*(0.85+0.45*sin(uTime*5.0));
  a *= depthFade(vZ)*coreMask(vZ)*lightGain(vColor.rgb);
  gl_FragColor = vec4(col*a*vColor.a*uOpacity*(1.0+uBoost), 0.0);
}`

export type ArcUniforms = Record<'uReveal' | 'uHover' | 'uSel' | 'uOpacity' | 'uBoost' | 'uMask', U<number>> & { uDepth: U<THREE.Vector2> }
export type ArcMaterial = THREE.ShaderMaterial & { uniforms: ArcUniforms }

export function arcMaterial(gfx: Gfx): ArcMaterial {
  const { U } = gfx
  return gfx.track(additive(new THREE.ShaderMaterial({
    uniforms: { uTime: U.uTime, uAtlas: U.uAtlas, uCore: U.uCore, uCoreZ: U.uCoreZ, uDepth: U.uDepth, uMask: { value: 1 },
      uReveal: { value: 1 }, uHover: { value: -1 }, uSel: { value: -1 }, uOpacity: { value: 1 }, uBoost: { value: 0 } },
    vertexShader: ARC_VS, fragmentShader: ARC_FS, side: THREE.DoubleSide
  }))) as ArcMaterial
}

// ── Atlas de glifos (Saira Condensed 500) para el texto grabado en los anillos y las etiquetas.
const CHARS = ' ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789ÁÉÍÓÚÑÜáéíóúñü.,:;·-–+%/()¿?¡!°#×«»\'"=<>_&@*|…'
function makeAtlas(gfx: Gfx): void {
  const S = 1024, cols = 16, cwp = 64, chp = 80, fs = 52, pad = 8
  const cv = document.createElement('canvas')
  cv.width = cv.height = S
  const g = cv.getContext('2d')
  if (!g) return
  g.fillStyle = '#000'
  g.fillRect(0, 0, S, S)
  g.fillStyle = '#fff'
  g.font = `500 ${fs}px "Saira Condensed", sans-serif`
  g.textBaseline = 'alphabetic'
  const G = gfx.glyphs
  ;[...CHARS].forEach((ch, i) => {
    const x = (i % cols) * cwp, y = Math.floor(i / cols) * chp
    g.fillText(ch, x + pad, y + 58)
    G.map[ch] = { u0: x / S, u1: (x + cwp) / S, v0: 1 - (y + chp) / S, v1: 1 - y / S, adv: g.measureText(ch).width / fs }
  })
  G.cw = cwp / fs
  G.ch = chp / fs
  G.pad = pad / fs
  const tex = new THREE.CanvasTexture(cv)
  tex.generateMipmaps = true
  tex.minFilter = THREE.LinearMipmapLinearFilter
  tex.magFilter = THREE.LinearFilter
  tex.anisotropy = 4
  gfx.U.uAtlas.value = gfx.track(tex)
}
const glyph = (G: Glyphs, ch: string): Glyph => G.map[ch] ?? G.map[ch.toUpperCase()] ?? G.map['?']!

export interface Hit { id: number; r0: number; r1: number; c0: number; c1: number }
export interface ArcOpts {
  col?: RGB; a?: number; st?: number; id?: number; z?: number; u1?: number; seg?: number; hit?: boolean
}
export interface TextOpts { col?: RGB; a?: number; id?: number; align?: 'center' | 'start' | 'end'; inward?: boolean; z?: number; track?: number }

/** Constructor de anillos. Ángulos en «vueltas» (0 = arriba, sentido horario), radios en unidades de mundo. */
export class RingBuilder {
  private p: number[] = []
  private c: number[] = []
  private m: number[] = []
  private uv: number[] = []
  private ix: number[] = []
  private n = 0
  readonly hits: Hit[] = []
  constructor(private readonly gfx: Gfx) {}

  private v(x: number, y: number, z: number, col: RGB, a: number, st: number, id: number, turn: number, u: number, w: number): void {
    this.p.push(x, y, z)
    this.c.push(col[0], col[1], col[2], a)
    this.m.push(st, id, ((turn % 1) + 1) % 1)
    this.uv.push(u, w)
    this.n++
  }
  arc(r0: number, r1: number, c0: number, c1: number, o: ArcOpts = {}): this {
    const { col = C.cyan, a = 1, st = 0, id = 0, z = 0, u1 = 1 } = o
    const n = o.seg ?? Math.max(1, Math.ceil(Math.abs(c1 - c0) * 200)), base = this.n
    for (let i = 0; i <= n; i++) {
      const t = i / n, c = c0 + (c1 - c0) * t, th = Math.PI / 2 - TAU * c, cs = Math.cos(th), sn = Math.sin(th)
      this.v(r0 * cs, r0 * sn, z, col, a, st, id, Math.min(c, 0.9999), t * u1, 0)
      this.v(r1 * cs, r1 * sn, z, col, a, st, id, Math.min(c, 0.9999), t * u1, 1)
    }
    for (let i = 0; i < n; i++) { const k = base + i * 2; this.ix.push(k, k + 1, k + 2, k + 1, k + 3, k + 2) }
    if (id && o.hit !== false) this.hits.push({ id, r0, r1, c0, c1 })
    return this
  }
  line(r: number, c0: number, c1: number, w = 0.06, o: ArcOpts = {}): this { return this.arc(r - w / 2, r + w / 2, c0, c1, { st: 1, ...o }) }
  dash(r: number, c0: number, c1: number, w: number, count: number, o: ArcOpts = {}): this { return this.arc(r - w / 2, r + w / 2, c0, c1, { st: 2, u1: count, ...o }) }
  flow(r: number, c0: number, c1: number, w: number, count: number, o: ArcOpts = {}): this { return this.arc(r - w / 2, r + w / 2, c0, c1, { st: 4, u1: count, ...o }) }
  /** Trazo radial (graduación, aguja). */
  tick(c: number, r0: number, r1: number, w = 0.03, o: ArcOpts = {}): this {
    const { col = C.cyan, a = 1, st = 1, id = 0, z = 0 } = o, th = Math.PI / 2 - TAU * c, cs = Math.cos(th), sn = Math.sin(th)
    const tx = (-sn * w) / 2, ty = (cs * w) / 2, k = this.n
    this.v(r0 * cs - tx, r0 * sn - ty, z, col, a, st, id, c, 0, 0)
    this.v(r0 * cs + tx, r0 * sn + ty, z, col, a, st, id, c, 0, 1)
    this.v(r1 * cs - tx, r1 * sn - ty, z, col, a, st, id, c, 1, 0)
    this.v(r1 * cs + tx, r1 * sn + ty, z, col, a, st, id, c, 1, 1)
    this.ix.push(k, k + 1, k + 2, k + 1, k + 3, k + 2)
    return this
  }
  /** Limbo graduado: n divisiones entre c0 y c1; cada `major` es larga. */
  scale(n: number, r: number, len: number, o: ArcOpts & { c0?: number; c1?: number; major?: number; majorLen?: number; w?: number; out?: boolean } = {}): this {
    const { c0 = 0, c1 = 1, major = 5, majorLen = len * 2, w = 0.022, out = true } = o
    for (let i = 0; i < n; i++) {
      const big = i % major === 0, l = big ? majorLen : len
      this.tick(c0 + ((c1 - c0) * i) / n, out ? r : r - l, out ? r + l : r, big ? w * 1.5 : w, { ...o, a: (o.a ?? 1) * (big ? 1 : 0.6) })
    }
    return this
  }
  /** Texto curvo sobre el arco. Devuelve las vueltas que ocupa. */
  text(str: string, r: number, c: number, size: number, o: TextOpts = {}): number {
    const { col = C.ice, a = 1, id = 0, align = 'center', inward = false, z = 0, track = 0.04 } = o, G = this.gfx.glyphs, dir = inward ? -1 : 1
    const chars = [...str], adv = chars.map((ch) => (glyph(G, ch).adv + track) * size), total = adv.reduce((x, y) => x + y, 0)
    let s = align === 'center' ? -total / 2 : align === 'end' ? -total : 0
    const hw = (G.cw * size) / 2, hh = (G.ch * size) / 2
    chars.forEach((ch, i) => {
      const g = glyph(G, ch), ad = adv[i]!, mid = s + ad / 2
      s += ad
      if (ch === ' ') return
      const cc = c + (dir * mid) / (TAU * r), th = Math.PI / 2 - TAU * cc, cs = Math.cos(th), sn = Math.sin(th)
      const ux = cs * dir, uy = sn * dir, tx = sn * dir, ty = -cs * dir
      const off = (G.cw / 2 - G.pad) * size - (ad - track * size) / 2, cx = r * cs + tx * off, cy = r * sn + ty * off, k = this.n
      this.v(cx - tx * hw - ux * hh, cy - ty * hw - uy * hh, z, col, a, 3, id, cc, g.u0, g.v0)
      this.v(cx + tx * hw - ux * hh, cy + ty * hw - uy * hh, z, col, a, 3, id, cc, g.u1, g.v0)
      this.v(cx - tx * hw + ux * hh, cy - ty * hw + uy * hh, z, col, a, 3, id, cc, g.u0, g.v1)
      this.v(cx + tx * hw + ux * hh, cy + ty * hw + uy * hh, z, col, a, 3, id, cc, g.u1, g.v1)
      this.ix.push(k, k + 1, k + 2, k + 1, k + 3, k + 2)
    })
    return total / (TAU * r)
  }
  /** Ancho (en unidades) de un texto de ese tamaño: para recortar rótulos que no caben. */
  measure(str: string, size: number, track = 0.04): number {
    let w = 0
    for (const ch of str) w += (glyph(this.gfx.glyphs, ch).adv + track) * size
    return w
  }
  hit(id: number, r0: number, r1: number, c0: number, c1: number): this { this.hits.push({ id, r0, r1, c0, c1 }); return this }
  geometry(): THREE.BufferGeometry {
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.Float32BufferAttribute(this.p, 3))
    g.setAttribute('aColor', new THREE.Float32BufferAttribute(this.c, 4))
    g.setAttribute('aMeta', new THREE.Float32BufferAttribute(this.m, 3))
    g.setAttribute('aUv', new THREE.Float32BufferAttribute(this.uv, 2))
    g.setIndex(this.n > 65535 ? new THREE.Uint32BufferAttribute(this.ix, 1) : new THREE.Uint16BufferAttribute(this.ix, 1))
    return g
  }
  mesh(material: ArcMaterial = arcMaterial(this.gfx)): RingMesh {
    const m = new THREE.Mesh(this.geometry(), material) as RingMesh
    m.frustumCulled = false
    m.userData.hits = this.hits
    return m
  }
  /** Sustituye la geometría de una malla ya creada (cuando cambian los datos). */
  into(mesh: RingMesh): RingMesh {
    mesh.geometry.dispose()
    mesh.geometry = this.geometry()
    mesh.userData.hits = this.hits
    return mesh
  }
}
export type RingMesh = THREE.Mesh<THREE.BufferGeometry, ArcMaterial> & { userData: { hits: Hit[] } }

export function disposeMesh(m: THREE.Mesh | THREE.Points | THREE.LineSegments): void {
  m.geometry.dispose()
  const mat = m.material
  if (Array.isArray(mat)) for (const x of mat) x.dispose()
  else mat.dispose()
}

/** Qué elemento hay bajo un punto local del anillo (x, y en su plano). */
export function pickRing(hits: readonly Hit[], x: number, y: number): number {
  const r = Math.hypot(x, y)
  let c = (Math.PI / 2 - Math.atan2(y, x)) / TAU
  c = ((c % 1) + 1) % 1
  for (let i = hits.length - 1; i >= 0; i--) {
    const h = hits[i]!
    if (r < h.r0 || r > h.r1) continue
    if ((c >= h.c0 && c <= h.c1) || (c + 1 >= h.c0 && c + 1 <= h.c1) || (c - 1 >= h.c0 && c - 1 <= h.c1)) return h.id
  }
  return 0
}

// ── Puntos: satélites y nodos, dibujados como discos, anillos, rombos o cuadrados en el shader.
const PT_VS = /* glsl */ `
attribute vec4 aColor; attribute vec3 aMeta; uniform float uPx, uHover, uSel;
varying vec4 vColor; varying float vKind, vH, vZ;
void main(){ vec4 mv = modelViewMatrix*vec4(position,1.0); gl_Position = projectionMatrix*mv; vZ = -mv.z;
  float h = 1.0-step(0.5, abs(aMeta.z-uHover)), s = 1.0-step(0.5, abs(aMeta.z-uSel)); vH = max(h, s);
  vColor = aColor; vKind = aMeta.y; gl_PointSize = max(1.5, aMeta.x*uPx/vZ*(1.0+0.5*vH)); }`
const PT_FS = /* glsl */ `
precision highp float; uniform float uOpacity, uTime; varying vec4 vColor; varying float vKind, vH, vZ;
${COMMON_FS}
void main(){ vec2 p = gl_PointCoord*2.0-1.0; float r = length(p), a;
  if (vKind < 0.5) a = exp(-r*r*5.0);
  else if (vKind < 1.5) a = smoothstep(0.34, 0.26, r) + 0.5*exp(-r*r*4.0);
  else if (vKind < 2.5) a = smoothstep(0.22, 0.15, r) + smoothstep(0.08, 0.0, abs(r-0.62))*0.9 + 0.38*exp(-r*r*3.5);
  else if (vKind < 3.5) { float q = abs(p.x)+abs(p.y); a = smoothstep(0.08, 0.0, abs(q-0.62)) + smoothstep(0.3, 0.22, q) + 0.3*exp(-r*r*4.0); }
  else { float q = max(abs(p.x), abs(p.y)); a = smoothstep(0.08, 0.0, abs(q-0.5)) + smoothstep(0.2, 0.13, q) + 0.3*exp(-r*r*4.0); }
  a *= smoothstep(1.0, 0.88, r)*depthFade(vZ)*coreMask(vZ)*(0.25+0.75*lightGain(vColor.rgb));
  gl_FragColor = vec4(mix(vColor.rgb, vec3(1.0), 0.5*vH)*a*vColor.a*uOpacity*(1.0+vH*(0.8+0.3*sin(uTime*5.0))), 0.0); }`

export type PointsMaterial = THREE.ShaderMaterial & { uniforms: Record<'uHover' | 'uSel' | 'uOpacity' | 'uMask', U<number>> & { uDepth: U<THREE.Vector2> } }
export function pointsMaterial(gfx: Gfx): PointsMaterial {
  const { U } = gfx
  return gfx.track(additive(new THREE.ShaderMaterial({
    uniforms: { uPx: U.uPx, uTime: U.uTime, uCore: U.uCore, uCoreZ: U.uCoreZ, uDepth: U.uDepth, uMask: { value: 1 }, uHover: { value: -1 }, uSel: { value: -1 }, uOpacity: { value: 1 } },
    vertexShader: PT_VS, fragmentShader: PT_FS
  }))) as PointsMaterial
}

export interface PointCloud {
  readonly pts: THREE.Points<THREE.BufferGeometry, PointsMaterial>
  readonly mat: PointsMaterial
  set(i: number, x: number, y: number, z: number): void
  /** kind: 0 polvo, 1 disco, 2 anillo, 3 rombo, 4 cuadrado. */
  style(i: number, c: RGB, a: number, size: number, kind: number, id: number): void
  flush(colors?: boolean): void
}
/** Nube de puntos con atributos editables. */
export function makePoints(gfx: Gfx, n: number, material: PointsMaterial = pointsMaterial(gfx)): PointCloud {
  const g = gfx.track(new THREE.BufferGeometry()), pos = new Float32Array(Math.max(1, n) * 3), col = new Float32Array(Math.max(1, n) * 4), meta = new Float32Array(Math.max(1, n) * 3)
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3))
  g.setAttribute('aColor', new THREE.BufferAttribute(col, 4))
  g.setAttribute('aMeta', new THREE.BufferAttribute(meta, 3))
  g.setDrawRange(0, n)
  const pts = new THREE.Points(g, material)
  pts.frustumCulled = false
  return {
    pts, mat: material,
    set(i, x, y, z) { pos[i * 3] = x; pos[i * 3 + 1] = y; pos[i * 3 + 2] = z },
    style(i, c, a, size, kind, id) { col.set([c[0], c[1], c[2], a], i * 4); meta.set([size, kind, id], i * 3) },
    flush(colors = false) {
      g.attributes.position!.needsUpdate = true
      if (colors) { g.attributes.aColor!.needsUpdate = true; g.attributes.aMeta!.needsUpdate = true }
    }
  }
}

// ── Polvo en órbita alrededor del núcleo (todo el movimiento en el shader de vértices).
export interface Dust {
  readonly pts: THREE.Points
  readonly uniforms: Record<'uGather' | 'uOpacity' | 'uSpin', U<number>> & { uTint: U<THREE.Vector3> }
  setCount(k: number): void
}
export function makeDust(gfx: Gfx, n: number): Dust {
  const { U } = gfx
  const g = gfx.track(new THREE.BufferGeometry()), seed = new Float32Array(n * 4), size = new Float32Array(n)
  for (let i = 0; i < n; i++) {
    const u = Math.random(), rr = 2.2 + Math.pow(u, 0.7) * 13
    seed.set([rr, Math.random() * TAU, (Math.random() - 0.5) * (4 + rr * 0.7), ((0.25 + Math.random()) * (Math.random() < 0.5 ? 1 : 0.6)) / rr], i * 4)
    size[i] = 0.022 + Math.pow(Math.random(), 5) * 0.11
  }
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 3), 3))
  g.setAttribute('aSeed', new THREE.BufferAttribute(seed, 4))
  g.setAttribute('aSize', new THREE.BufferAttribute(size, 1))
  const uniforms = { uGather: { value: 1 }, uOpacity: { value: 1 }, uSpin: { value: 1 }, uTint: { value: new THREE.Vector3(0.31, 0.85, 1) } }
  const mat = gfx.track(additive(new THREE.ShaderMaterial({
    uniforms: { uTime: U.uTime, uPx: U.uPx, ...uniforms },
    vertexShader: /* glsl */ `attribute vec4 aSeed; attribute float aSize; uniform float uTime, uPx, uGather, uSpin; varying float vA;
      void main(){ float ang = aSeed.y + uTime*aSeed.w*uSpin; float rr = aSeed.x*(1.0+(1.0-uGather)*2.6);
        vec3 p = vec3(cos(ang)*rr, aSeed.z*(0.3+0.7*uGather) + sin(uTime*0.3+aSeed.y*7.0)*0.25, sin(ang)*rr);
        vec4 mv = modelViewMatrix*vec4(p,1.0); gl_Position = projectionMatrix*mv; gl_PointSize = max(1.0, aSize*uPx/(-mv.z));
        vA = (0.35+0.65*sin(uTime*(0.6+aSeed.w*3.0)+aSeed.y*13.0)*0.5+0.5)*clamp(1.6-(-mv.z)/26.0, 0.15, 1.0); }`,
    fragmentShader: /* glsl */ `precision mediump float; uniform float uOpacity; uniform vec3 uTint; varying float vA;
      void main(){ vec2 p = gl_PointCoord*2.0-1.0; float a = exp(-dot(p,p)*4.5); gl_FragColor = vec4(uTint*a*vA*uOpacity*0.62, 0.0); }`
  })))
  const pts = new THREE.Points(g, mat)
  pts.frustumCulled = false
  return { pts, uniforms, setCount(k) { g.setDrawRange(0, Math.min(n, k)) } }
}

// ── Aristas con pulsos que las recorren.
export type LinesMaterial = THREE.ShaderMaterial & { uniforms: Record<'uOpacity' | 'uMask', U<number>> & { uDepth: U<THREE.Vector2> } }
export function linesMaterial(gfx: Gfx): LinesMaterial {
  const { U } = gfx
  return gfx.track(additive(new THREE.ShaderMaterial({
    uniforms: { uTime: U.uTime, uOpacity: { value: 1 }, uDepth: U.uDepth, uCore: U.uCore, uCoreZ: U.uCoreZ, uMask: { value: 1 } },
    vertexShader: /* glsl */ `attribute vec4 aColor; attribute vec2 aT; varying vec4 vColor; varying vec2 vT; varying float vZ;
      void main(){ vec4 mv = modelViewMatrix*vec4(position,1.0); vZ = -mv.z; vColor = aColor; vT = aT; gl_Position = projectionMatrix*mv; }`,
    fragmentShader: /* glsl */ `precision highp float; uniform float uTime, uOpacity; varying vec4 vColor; varying vec2 vT; varying float vZ;
      ${COMMON_FS}
      void main(){ float f = fract(vT.x - uTime*0.3 + vT.y), g = min(f, 1.0-f); float a = vColor.a*(0.34 + 1.9*exp(-g*g*140.0))*depthFade(vZ)*coreMask(vZ);
        gl_FragColor = vec4(vColor.rgb*a*uOpacity, 0.0); }`
  }))) as LinesMaterial
}
