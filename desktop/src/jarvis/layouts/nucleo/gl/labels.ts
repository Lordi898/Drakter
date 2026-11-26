/**
 * Etiquetas flotantes en el Stage (no en el DOM): cada etiqueta es texto plano del atlas, en px de
 * pantalla, anclado a un punto 3D. El ancla se proyecta en el shader de vértices, así que un grafo que
 * gira no cuesta CPU ni escrituras DOM; la geometría solo se rehace cuando cambia el conjunto.
 * El texto viene de datos del usuario: se dibuja glifo a glifo, nunca se interpreta.
 */
import * as THREE from 'three'
import { C, additive, type Gfx, type RGB } from './kit'

export interface Label {
  readonly x: number
  readonly y: number
  readonly z: number
  readonly text: string
  readonly strong?: boolean
  readonly tone?: 'late' | 'soon' | 'open' | 'done' | ''
}

export interface LabelBatch {
  readonly mesh: THREE.Mesh
  /** Rehace las etiquetas si cambió el conjunto (texto, tono o realce). */
  set(list: readonly Label[]): void
  /** Mueve el ancla de la etiqueta i sin rehacer la geometría. */
  move(i: number, x: number, y: number, z: number): void
  flush(): void
  readonly uniforms: { uOpacity: { value: number }; uScale: { value: number } }
}

const MAX_CHARS = 34
const SIZE = 13 // px CSS del texto normal

const VS = /* glsl */ `
attribute vec2 aOff; attribute vec2 aUv; attribute vec4 aColor;
uniform vec2 uView; uniform float uScale;
varying vec2 vUv; varying vec4 vColor;
void main(){
  vec4 clip = projectionMatrix*modelViewMatrix*vec4(position,1.0);
  clip.xy += vec2(aOff.x, -aOff.y)*uScale*2.0/uView*clip.w;
  gl_Position = clip; vUv = aUv; vColor = aColor;
}`
const FS = /* glsl */ `
precision mediump float; uniform sampler2D uAtlas; uniform float uOpacity;
varying vec2 vUv; varying vec4 vColor;
void main(){ float a = texture2D(uAtlas, vUv).r; gl_FragColor = vec4(vColor.rgb*a*vColor.a*uOpacity*1.35, 0.0); }`

const toneColor = (l: Label): RGB => (l.tone === 'late' ? C.red : l.tone === 'soon' ? C.amber : l.strong ? C.white : C.ice)

export function createLabels(gfx: Gfx): LabelBatch {
  const uniforms = { uOpacity: { value: 1 }, uScale: gfx.U.uLabelScale }
  const mat = gfx.track(additive(new THREE.ShaderMaterial({ uniforms: { uAtlas: gfx.U.uAtlas, uView: gfx.U.uView, ...uniforms }, vertexShader: VS, fragmentShader: FS })))
  const geom = gfx.track(new THREE.BufferGeometry())
  const mesh = new THREE.Mesh(geom, mat)
  mesh.frustumCulled = false
  mesh.visible = false
  let key = ''
  let ranges: [number, number][] = []
  let pos = new Float32Array(0)

  return {
    mesh, uniforms,
    set(list) {
      const k = list.map((l) => `${l.text}|${l.tone ?? ''}|${l.strong ? 1 : 0}`).join('\n')
      if (k === key) { list.forEach((l, i) => this.move(i, l.x, l.y, l.z)); return }
      key = k
      const G = gfx.glyphs, P: number[] = [], O: number[] = [], UV: number[] = [], COL: number[] = [], IX: number[] = []
      ranges = []
      let n = 0
      for (const l of list) {
        const size = l.strong ? SIZE * 1.15 : SIZE, col = toneColor(l), a = l.strong ? 1 : 0.85
        const text = l.text.length > MAX_CHARS ? `${l.text.slice(0, MAX_CHARS - 1)}…` : l.text
        const start = n
        let x = SIZE // a 1 em del punto
        const hw = (G.cw * size) / 2, hh = (G.ch * size) / 2
        for (const ch of text) {
          const g = G.map[ch] ?? G.map['?']!, adv = (g.adv + 0.03) * size
          if (ch !== ' ') {
            const cx = x + (G.cw / 2 - G.pad) * size, cy = -hh * 0.18
            const quad: [number, number, number, number][] = [
              [cx - hw, cy + hh, g.u0, g.v0], [cx + hw, cy + hh, g.u1, g.v0], [cx - hw, cy - hh, g.u0, g.v1], [cx + hw, cy - hh, g.u1, g.v1]
            ]
            for (const [ox, oy, u, v] of quad) { P.push(l.x, l.y, l.z); O.push(ox, oy); UV.push(u, v); COL.push(col[0], col[1], col[2], a); n++ }
            const b = n - 4
            IX.push(b, b + 1, b + 2, b + 1, b + 3, b + 2)
          }
          x += adv
        }
        ranges.push([start, n])
      }
      pos = new Float32Array(P)
      geom.setAttribute('position', new THREE.BufferAttribute(pos, 3))
      geom.setAttribute('aOff', new THREE.Float32BufferAttribute(O, 2))
      geom.setAttribute('aUv', new THREE.Float32BufferAttribute(UV, 2))
      geom.setAttribute('aColor', new THREE.Float32BufferAttribute(COL, 4))
      geom.setIndex(IX)
      mesh.visible = n > 0
    },
    move(i, x, y, z) {
      const r = ranges[i]
      if (!r) return
      for (let v = r[0]; v < r[1]; v++) { pos[v * 3] = x; pos[v * 3 + 1] = y; pos[v * 3 + 2] = z }
    },
    flush() {
      const a = geom.getAttribute('position')
      if (a) a.needsUpdate = true
    }
  }
}
