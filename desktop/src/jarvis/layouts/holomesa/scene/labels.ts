/**
 * Etiquetas, tags y tooltip de la Holomesa dibujados EN EL STAGE (lección medida del prototipo: la
 * composición de nodos DOM movidos por fotograma disparaba la CPU en reposo). Cada texto distinto se
 * pinta una vez en un atlas (canvas 2D, sin `shadowBlur`) y todas las etiquetas visibles son UNA malla
 * instanciada en espacio de pantalla. Por fotograma solo se suben posiciones y opacidades.
 * El texto llega del usuario: se pinta con `fillText`, nunca como HTML.
 */
import * as THREE from 'three'

export type LabelStyle = 'station' | 'tag' | 'tip'
export type LabelTone = 'hi' | 'warn' | ''

export interface LabelSpec {
  /** Identidad estable (para el fundido); el contenido puede cambiar con la misma clave. */
  readonly id: string
  readonly style: LabelStyle
  readonly tone: LabelTone
  /** Primera línea destacada y, opcionalmente, más líneas secundarias. */
  readonly lines: readonly string[]
  /** Punto de anclaje en px CSS. */
  readonly x: number
  readonly y: number
}

interface Glyph {
  readonly u0: number
  readonly v0: number
  readonly u1: number
  readonly v1: number
  /** Tamaño en px CSS y desplazamiento del rectángulo respecto al anclaje. */
  readonly w: number
  readonly h: number
  readonly ox: number
  readonly oy: number
}

interface Live {
  glyph: Glyph
  content: string
  x: number
  y: number
  alpha: number
  target: number
}

const MAX = 96
const ATLAS = 2048
const FONT = '"Recursive Variable", ui-sans-serif, system-ui, sans-serif'
const MONO = '"Recursive Variable", ui-monospace, monospace'
const TONE_COLOR: Record<LabelTone, string> = { hi: '#eafaff', warn: '#ffc27a', '': '#a9dcf5' }
const ACCENT: Record<LabelTone, string> = { hi: 'rgba(169,236,255,0.9)', warn: 'rgba(255,176,80,0.9)', '': 'rgba(111,214,255,0.55)' }

const clipText = (t: string, max: number): string => (t.length > max ? t.slice(0, max - 1) + '…' : t)

export interface LabelRenderer {
  /** Etiquetas de este fotograma (las que no vengan se desvanecen). Devuelve si hay fundidos en curso. */
  set(specs: readonly LabelSpec[], dt: number, reduced: boolean): boolean
  render(renderer: THREE.WebGLRenderer, width: number, height: number): void
  dispose(): void
}

export function createLabelRenderer(): LabelRenderer {
  const canvas = document.createElement('canvas')
  const scale = Math.min(2, Math.max(1, window.devicePixelRatio || 1))
  canvas.width = ATLAS
  canvas.height = ATLAS
  const g = canvas.getContext('2d')!
  const texture = new THREE.CanvasTexture(canvas)
  texture.flipY = false
  texture.generateMipmaps = false
  texture.minFilter = THREE.LinearFilter
  texture.magFilter = THREE.LinearFilter

  const glyphs = new Map<string, Glyph>()
  let shelfX = 0, shelfY = 0, shelfH = 0
  let dirty = false

  const measure = (spec: LabelSpec): { w: number; h: number; fonts: string[]; texts: string[] } => {
    const head = spec.style === 'tag' ? `500 12px ${FONT}` : `600 13px ${FONT}`
    const sub = `400 12px ${MONO}`
    const max = spec.style === 'tip' ? 60 : spec.style === 'station' ? 44 : 40
    const texts = spec.lines.map((l) => clipText(l, max))
    const fonts = texts.map((_, i) => (i === 0 ? head : sub))
    let w = 0
    texts.forEach((t, i) => {
      g.font = fonts[i]!
      w = Math.max(w, g.measureText(t).width)
    })
    const lineH = 16
    return { w: Math.ceil(w) + 18, h: texts.length * lineH + 8, fonts, texts }
  }

  const draw = (key: string, spec: LabelSpec): Glyph | null => {
    const m = measure(spec)
    const dot = spec.style === 'station' ? 10 : 0
    const W = m.w + dot, H = m.h + (spec.style === 'station' ? 10 : 0)
    const pw = Math.ceil(W * scale) + 2, ph = Math.ceil(H * scale) + 2
    if (shelfX + pw > ATLAS) {
      shelfX = 0
      shelfY += shelfH
      shelfH = 0
    }
    if (shelfY + ph > ATLAS) return null
    const x0 = shelfX, y0 = shelfY
    shelfX += pw
    shelfH = Math.max(shelfH, ph)
    g.save()
    g.translate(x0 + 1, y0 + 1)
    g.scale(scale, scale)
    g.clearRect(0, 0, W, H)
    // Placa oscura semiopaca (legibilidad sobre luz aditiva) y filo de color: sin sombras ni desenfoques.
    const bx = dot, by = 0
    g.fillStyle = spec.style === 'tip' ? 'rgba(2,10,20,0.9)' : 'rgba(1,6,14,0.72)'
    g.fillRect(bx, by, m.w, m.h)
    g.fillStyle = ACCENT[spec.tone]
    g.fillRect(bx, by, 2, m.h)
    g.strokeStyle = 'rgba(111,214,255,0.28)'
    g.lineWidth = 1
    g.strokeRect(bx + 0.5, by + 0.5, m.w - 1, m.h - 1)
    if (dot) {
      // Punto de anclaje y tallo hacia la placa.
      g.fillStyle = ACCENT[spec.tone]
      g.beginPath()
      g.arc(4, H - 4, 3, 0, Math.PI * 2)
      g.fill()
      g.fillRect(4, m.h, 1, H - m.h - 6)
    }
    g.textBaseline = 'middle'
    m.texts.forEach((t, i) => {
      g.font = m.fonts[i]!
      g.fillStyle = i === 0 ? TONE_COLOR[spec.tone] : '#8fb4cc'
      g.fillText(t, bx + 9, by + 4 + 8 + i * 16)
    })
    g.restore()
    dirty = true
    // Estación: el anclaje es el punto (abajo a la izquierda). Tag: centrado encima. Tip: abajo a la derecha del cursor.
    const ox = spec.style === 'station' ? -4 : spec.style === 'tag' ? -W / 2 : 18
    const oy = spec.style === 'station' ? -(H - 4) : spec.style === 'tag' ? -H - 4 : 16
    const glyph = { u0: (x0 + 1) / ATLAS, v0: (y0 + 1) / ATLAS, u1: (x0 + 1 + W * scale) / ATLAS, v1: (y0 + 1 + H * scale) / ATLAS, w: W, h: H, ox, oy }
    glyphs.set(key, glyph)
    return glyph
  }

  const reset = (): void => {
    glyphs.clear()
    g.clearRect(0, 0, ATLAS, ATLAS)
    shelfX = shelfY = shelfH = 0
    dirty = true
  }

  const glyphFor = (key: string, spec: LabelSpec): Glyph | null => glyphs.get(key) ?? draw(key, spec)

  // Malla: un quad instanciado (0..1) en espacio de pantalla.
  const geo = new THREE.InstancedBufferGeometry()
  geo.setAttribute('position', new THREE.Float32BufferAttribute([0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0], 3))
  geo.setIndex([0, 2, 1, 1, 2, 3])
  const aRect = new THREE.InstancedBufferAttribute(new Float32Array(MAX * 4), 4)
  const aUv = new THREE.InstancedBufferAttribute(new Float32Array(MAX * 4), 4)
  const aAlpha = new THREE.InstancedBufferAttribute(new Float32Array(MAX), 1)
  for (const a of [aRect, aUv, aAlpha]) a.setUsage(THREE.DynamicDrawUsage)
  geo.setAttribute('aRect', aRect)
  geo.setAttribute('aUv', aUv)
  geo.setAttribute('aAlpha', aAlpha)
  geo.instanceCount = 0
  const mat = new THREE.ShaderMaterial({
    uniforms: { uAtlas: { value: texture }, uView: { value: new THREE.Vector2(1, 1) } },
    vertexShader: /* glsl */ `
      attribute vec4 aRect; attribute vec4 aUv; attribute float aAlpha; uniform vec2 uView;
      varying vec2 vUv; varying float vA;
      void main(){ vec2 px = aRect.xy + position.xy * aRect.zw;
        vUv = mix(aUv.xy, aUv.zw, position.xy); vA = aAlpha;
        gl_Position = vec4(px.x / uView.x * 2.0 - 1.0, 1.0 - px.y / uView.y * 2.0, 0.0, 1.0); }`,
    fragmentShader: /* glsl */ `
      uniform sampler2D uAtlas; varying vec2 vUv; varying float vA;
      void main(){ vec4 t = texture2D(uAtlas, vUv); gl_FragColor = vec4(t.rgb, t.a * vA); }`,
    transparent: true,
    depthTest: false,
    depthWrite: false,
    blending: THREE.NormalBlending
  })
  const mesh = new THREE.Mesh(geo, mat)
  mesh.frustumCulled = false
  const scene = new THREE.Scene()
  scene.add(mesh)
  const cam = new THREE.Camera()

  const live = new Map<string, Live>()

  return {
    set(specs, dt, reduced) {
      const k = reduced ? 1 : Math.min(1, dt * 10)
      for (const l of live.values()) l.target = 0
      for (const s of specs) {
        const content = `${s.style}|${s.tone}|${s.lines.join('\n')}`
        let glyph = glyphFor(content, s)
        if (!glyph) {
          reset()
          for (const l of live.values()) l.alpha = 0
          live.clear()
          glyph = glyphFor(content, s)
          if (!glyph) continue
        }
        const cur = live.get(s.id)
        if (cur) {
          cur.glyph = glyph
          cur.content = content
          cur.x = s.x
          cur.y = s.y
          cur.target = 1
        } else live.set(s.id, { glyph, content, x: s.x, y: s.y, alpha: 0, target: 1 })
      }
      let n = 0
      let fading = false
      for (const [id, l] of live) {
        l.alpha += (l.target - l.alpha) * k
        if (Math.abs(l.target - l.alpha) < 0.01) l.alpha = l.target
        else fading = true
        if (l.alpha <= 0) {
          live.delete(id)
          continue
        }
        if (n >= MAX) continue
        const gl = l.glyph
        const x = Math.round(l.x + gl.ox), y = Math.round(l.y + gl.oy)
        // Solo se suben a la GPU los atributos que cambian (en reposo, ninguno).
        if (aRect.getX(n) !== x || aRect.getY(n) !== y || aRect.getZ(n) !== gl.w || aRect.getW(n) !== gl.h) {
          aRect.setXYZW(n, x, y, gl.w, gl.h)
          aRect.needsUpdate = true
        }
        if (aUv.getX(n) !== gl.u0 || aUv.getY(n) !== gl.v0) {
          aUv.setXYZW(n, gl.u0, gl.v0, gl.u1, gl.v1)
          aUv.needsUpdate = true
        }
        if (aAlpha.getX(n) !== l.alpha) {
          aAlpha.setX(n, l.alpha)
          aAlpha.needsUpdate = true
        }
        n++
      }
      geo.instanceCount = n
      if (dirty) {
        texture.needsUpdate = true
        dirty = false
      }
      return fading
    },
    render(renderer, width, height) {
      if (geo.instanceCount === 0) return
      ;(mat.uniforms.uView!.value as THREE.Vector2).set(width, height)
      renderer.render(scene, cam)
    },
    dispose() {
      geo.dispose()
      mat.dispose()
      texture.dispose()
      live.clear()
      glyphs.clear()
    }
  }
}
