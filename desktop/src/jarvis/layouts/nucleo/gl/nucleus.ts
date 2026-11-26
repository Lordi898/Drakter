/**
 * El núcleo: peana emisora, haz de proyección, halo con el espectro circular de la voz (datos reales de
 * `voice/levels.ts`), ondas de choque y un orbe de puntos que sustituye al avatar si no hay avatar 3D.
 */
import * as THREE from 'three'
import { C, RingBuilder, TAU, additive, disposeMesh, makePoints, type Gfx, type RingMesh } from './kit'

const lerp = (a: number, b: number, t: number) => a + (b - a) * t
const clamp = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x))
const outCubic = (t: number) => 1 - Math.pow(1 - t, 3)

export type ShockKind = 'plain' | 'error' | 'success' | 'warn'

export interface Nucleus {
  readonly group: THREE.Group
  /** Color del estado (lo interpola la escena). */
  readonly tint: THREE.Vector3
  /** 64 bandas 0..255 que se suben como textura en cada fotograma. */
  readonly spec: Uint8Array
  intro: number
  orbK: number
  haloK: number
  shock(kind?: ShockKind): void
  update(t: number, dt: number, o: { anchor: THREE.Vector3; camera: THREE.Camera; g: number; G: number; energy: number }): void
  dispose(): void
}

export function createNucleus(gfx: Gfx): Nucleus {
  const { U } = gfx
  const group = new THREE.Group(), tint = new THREE.Vector3(0.31, 0.85, 1)
  const owned: (THREE.Mesh | THREE.Points)[] = []
  // Peana emisora.
  const pb = new RingBuilder(gfx)
  pb.line(2.12, 0, 1, 0.07).scale(72, 2.12, 0.05, { major: 6, majorLen: 0.13, a: 0.7 }).dash(1.78, 0, 1, 0.06, 36, { a: 0.6 }).flow(1.5, 0, 1, 0.07, 6, { a: 0.9 }).line(1.24, 0, 1, 0.04, { a: 0.5, col: C.blue })
  for (let i = 0; i < 3; i++) pb.arc(0.55, 1.08, i / 3 + 0.02, i / 3 + 0.29, { a: 0.3, col: C.blue })
  const pedestal = pb.mesh()
  pedestal.rotation.x = -Math.PI / 2
  pedestal.position.y = -2.5
  pedestal.material.uniforms.uMask.value = 0
  group.add(pedestal)
  owned.push(pedestal)
  // Haz de proyección.
  const beamU = { uOpacity: { value: 0 } }
  const beamMat = gfx.track(additive(new THREE.ShaderMaterial({
    uniforms: { uTime: U.uTime, uTint: { value: tint }, uVoice: U.uVoice, ...beamU }, side: THREE.DoubleSide,
    vertexShader: /* glsl */ `varying vec2 vUv; varying vec3 vN, vV; void main(){ vUv = uv; vec4 mv = modelViewMatrix*vec4(position,1.0); vN = normalMatrix*normal; vV = -mv.xyz; gl_Position = projectionMatrix*mv; }`,
    fragmentShader: /* glsl */ `precision highp float; uniform float uTime, uOpacity, uVoice; uniform vec3 uTint; varying vec2 vUv; varying vec3 vN, vV;
      void main(){ float rim = pow(1.0-abs(dot(normalize(vN), normalize(vV))), 2.4), fall = pow(1.0-vUv.y, 1.5), bands = 0.62+0.38*sin(vUv.y*64.0-uTime*2.6);
        gl_FragColor = vec4(uTint*(0.035+0.55*rim)*fall*bands*uOpacity*(1.0+0.7*uVoice), 0.0); }`
  })))
  const beam = new THREE.Mesh(gfx.track(new THREE.CylinderGeometry(2.3, 1.5, 4.7, 56, 1, true)), beamMat)
  beam.position.y = -2.5 + 2.35
  beam.frustumCulled = false
  group.add(beam)
  // Halo de voz: espectro circular alrededor del avatar, siempre de cara a la cámara.
  const halo = new THREE.Group()
  group.add(halo)
  const hb = new RingBuilder(gfx)
  hb.line(2.3, 0, 1, 0.045, { a: 0.55 }).dash(2.42, 0, 1, 0.03, 96, { a: 0.35, col: C.blue })
  for (let i = 0; i < 3; i++) hb.flow(2.5, i / 3, i / 3 + 0.2, 0.05, 1.2, { a: 0.9 }).tick(i / 3, 2.4, 2.62, 0.04, { col: C.white })
  const haloRing = hb.mesh()
  haloRing.material.uniforms.uMask.value = 0
  halo.add(haloRing)
  owned.push(haloRing)
  const NB = 144, sg = gfx.track(new THREE.BufferGeometry())
  const ang = new Float32Array(NB * 4), side = new Float32Array(NB * 4), lat = new Float32Array(NB * 4), bin = new Float32Array(NB * 4), six: number[] = []
  for (let i = 0; i < NB; i++) {
    const a = Math.PI / 2 - ((i + 0.5) / NB) * TAU, b = Math.abs(((i + 0.5) / NB) * 2 - 1)
    for (let k = 0; k < 4; k++) { ang[i * 4 + k] = a; side[i * 4 + k] = k >> 1; lat[i * 4 + k] = k & 1 ? 1 : -1; bin[i * 4 + k] = 1 - b }
    six.push(i * 4, i * 4 + 1, i * 4 + 2, i * 4 + 1, i * 4 + 3, i * 4 + 2)
  }
  sg.setAttribute('position', new THREE.BufferAttribute(new Float32Array(NB * 12), 3))
  sg.setAttribute('aAng', new THREE.BufferAttribute(ang, 1))
  sg.setAttribute('aSide', new THREE.BufferAttribute(side, 1))
  sg.setAttribute('aLat', new THREE.BufferAttribute(lat, 1))
  sg.setAttribute('aBin', new THREE.BufferAttribute(bin, 1))
  sg.setIndex(six)
  const spec = new Uint8Array(64)
  const specTex = gfx.track(new THREE.DataTexture(spec, 64, 1, THREE.RedFormat, THREE.UnsignedByteType))
  specTex.magFilter = THREE.LinearFilter
  specTex.minFilter = THREE.LinearFilter
  specTex.needsUpdate = true
  const specU = { uR: { value: 2.3 }, uOpacity: { value: 0 } }
  const specMat = gfx.track(additive(new THREE.ShaderMaterial({
    uniforms: { uSpec: { value: specTex }, uLen: { value: 0.75 }, uW: { value: 0.017 }, uTint: { value: tint }, ...specU }, side: THREE.DoubleSide,
    vertexShader: /* glsl */ `attribute float aAng, aSide, aLat, aBin; uniform sampler2D uSpec; uniform float uR, uLen, uW; varying float vV, vS;
      void main(){ float v = texture2D(uSpec, vec2(aBin, 0.5)).r; vec2 d = vec2(cos(aAng), sin(aAng)); vec2 p = d*(uR + aSide*(0.035+v*uLen)) + vec2(-d.y, d.x)*aLat*uW; vV = v; vS = aSide;
        gl_Position = projectionMatrix*modelViewMatrix*vec4(p, 0.0, 1.0); }`,
    fragmentShader: /* glsl */ `precision mediump float; uniform float uOpacity; uniform vec3 uTint; varying float vV, vS;
      void main(){ gl_FragColor = vec4(mix(uTint, vec3(1.0), vV*vV*0.85)*(0.3+0.9*vV)*(1.0-0.45*vS)*uOpacity, 0.0); }`
  })))
  const specMesh = new THREE.Mesh(sg, specMat)
  specMesh.frustumCulled = false
  halo.add(specMesh)
  let specDirty = true
  // Ondas de choque.
  const SHOCK: Record<ShockKind, number> = { plain: 0, error: 2, success: 3, warn: 4 }
  const shocks: (RingMesh & { userData: { t?: number } })[] = [C.ice, C.ice, C.red, C.warm, C.amber].map((col) => {
    const b = new RingBuilder(gfx)
    b.line(1, 0, 1, 0.022, { col, a: 0.9 }).arc(0.93, 1, 0, 1, { col, a: 0.1, st: 5, u1: 60 }).dash(1.03, 0, 1, 0.012, 90, { col, a: 0.5 })
    const m = b.mesh()
    m.visible = false
    m.material.uniforms.uMask.value = 0
    ;(m.userData as { t?: number }).t = 9
    halo.add(m)
    owned.push(m)
    return m
  })
  // Orbe de reserva (y semilla del arranque).
  const orb = makePoints(gfx, 900), og = new THREE.Group()
  og.add(orb.pts)
  halo.add(og)
  orb.mat.uniforms.uMask.value = 0
  for (let i = 0; i < 900; i++) {
    const y = 1 - (i / 899) * 2, r = Math.sqrt(1 - y * y), a = i * 2.39996, R = i % 5 === 0 ? 0.72 : 1.25
    orb.set(i, Math.cos(a) * r * R, y * R, Math.sin(a) * r * R)
    orb.style(i, i % 5 === 0 ? C.white : i % 2 ? C.cyan : C.blue, i % 5 === 0 ? 0.9 : 0.75, 0.05 + (i % 7) * 0.006, 0, 0)
  }
  orb.flush(true)
  owned.push(orb.pts)

  const N: Nucleus = {
    group, tint, spec, intro: 0, orbK: 0, haloK: 0,
    shock(kind = 'plain') {
      const i = kind === 'plain' ? ((shocks[0]!.userData.t ?? 9) > 1 ? 0 : 1) : SHOCK[kind]
      const m = shocks[i]!
      m.userData.t = 0
      m.visible = true
    },
    update(t, dt, o) {
      halo.position.copy(o.anchor)
      halo.quaternion.copy(o.camera.quaternion)
      haloRing.rotation.z -= dt * 0.22 * o.energy
      haloRing.material.uniforms.uOpacity.value = N.haloK * o.G
      specU.uOpacity.value = N.haloK * o.G
      specU.uR.value = lerp(2.32, 2.2, o.g)
      // Solo se sube la textura si cambió el espectro (en reposo, nunca).
      let any = false
      for (let i = 0; i < 64; i++) if (spec[i]) { any = true; break }
      if (any || specDirty) { specTex.needsUpdate = true; specDirty = any }
      halo.scale.setScalar(lerp(1, 0.66, o.g))
      pedestal.rotation.z += dt * 0.12 * o.energy
      pedestal.material.uniforms.uOpacity.value = N.intro * o.G * (1 - o.g)
      pedestal.material.uniforms.uReveal.value = clamp(N.intro * 1.2)
      beamU.uOpacity.value = N.intro * o.G * (1 - o.g)
      beam.scale.y = 0.02 + 0.98 * outCubic(N.intro)
      beam.position.y = -2.5 + 2.35 * beam.scale.y
      for (const m of shocks) {
        if (!m.visible) continue
        const k = (m.userData.t = (m.userData.t ?? 0) + dt / 1.15)
        if (k >= 1) { m.visible = false; continue }
        m.scale.setScalar(1.6 + outCubic(k) * 6.4)
        m.material.uniforms.uOpacity.value = (1 - k) * (1 - k) * 0.9 * o.G
      }
      og.visible = N.orbK > 0.01
      if (og.visible) {
        og.rotation.y = t * 0.35
        og.rotation.x = Math.sin(t * 0.21) * 0.3
        og.scale.setScalar(N.orbK * (1 + 0.1 * U.uVoice.value + 0.03 * Math.sin(t * 1.7)))
        orb.mat.uniforms.uOpacity.value = Math.min(1, N.orbK) * o.G
      }
    },
    dispose() {
      for (const m of owned) disposeMesh(m)
    }
  }
  return N
}
