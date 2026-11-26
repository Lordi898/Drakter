/**
 * Capa de prueba neutra: polvo holográfico. Un `Points` con el movimiento en el vertex shader (cero
 * trabajo de CPU por partícula). El número sale de `QualityProfile.particles`; quieto en Ahorro y con
 * reducir movimiento.
 */
import * as THREE from 'three'
import type { QualityProfile, StageFrame, StageLayer } from '../types'
import { createHoloCamera } from './holoCamera'

const VERT = /* glsl */ `
uniform float uTime; uniform float uScale;
in vec4 aSeed;
out float vAlpha;
void main() {
  vec3 p = position;
  float t = uTime * (0.05 + aSeed.y * 0.1);
  p.y = mod(p.y + t * 6.0, 6.0);
  p.x += sin(uTime * 0.3 + aSeed.x * 6.2831) * 0.25;
  p.z += cos(uTime * 0.25 + aSeed.z * 6.2831) * 0.25;
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  gl_Position = projectionMatrix * mv;
  gl_PointSize = clamp((1.0 + aSeed.w * 2.5) * uScale / -mv.z, 1.0, 24.0);
  // Aparece y se apaga en los extremos del recorrido vertical: sin saltos al dar la vuelta.
  vAlpha = smoothstep(0.0, 0.6, p.y) * (1.0 - smoothstep(5.0, 6.0, p.y)) * (0.35 + aSeed.w * 0.65);
}`

const FRAG = /* glsl */ `
in float vAlpha; out vec4 outColor;
void main() {
  vec2 c = gl_PointCoord - 0.5;
  float d = dot(c, c) * 4.0;
  float a = exp(-d * 3.0) * vAlpha;
  outColor = vec4(mix(vec3(0.3, 0.85, 1.0), vec3(1.0), exp(-d * 12.0)) * a, a);
}`

function buildGeometry(count: number): THREE.BufferGeometry {
  const pos = new Float32Array(count * 3)
  const seed = new Float32Array(count * 4)
  for (let i = 0; i < count; i++) {
    pos[i * 3] = (Math.random() - 0.5) * 30
    pos[i * 3 + 1] = Math.random() * 6
    pos[i * 3 + 2] = -Math.random() * 34 + 3
    for (let k = 0; k < 4; k++) seed[i * 4 + k] = Math.random()
  }
  const g = new THREE.BufferGeometry()
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3))
  g.setAttribute('aSeed', new THREE.BufferAttribute(seed, 4))
  g.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 3, -14), 30)
  return g
}

export function createParticlesLayer(order = 20): StageLayer {
  const scene = new THREE.Scene()
  const holo = createHoloCamera()
  const material = new THREE.ShaderMaterial({
    glslVersion: THREE.GLSL3, vertexShader: VERT, fragmentShader: FRAG,
    uniforms: { uTime: { value: 0 }, uScale: { value: 1 } },
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending
  })
  let geometry = buildGeometry(1)
  let allocated = 1
  const points = new THREE.Points(geometry, material)
  scene.add(points)
  let time = 0
  let frozen = false

  const apply = (q: QualityProfile): void => {
    const n = Math.max(0, q.particles)
    if (n > allocated) {
      geometry.dispose()
      geometry = buildGeometry(n)
      allocated = n
      points.geometry = geometry
    }
    geometry.setDrawRange(0, n)
    points.visible = n > 0
    frozen = q.tier === 'ahorro'
  }

  return {
    id: 'test-particles',
    order,
    async init(frame: StageFrame) {
      apply(frame.quality)
      holo.update(frame)
      await frame.renderer.compileAsync(scene, holo.camera)
    },
    setQuality: apply,
    update(frame) {
      if (!frozen && !frame.reducedMotion) time += frame.dt
      material.uniforms.uTime!.value = time
      // Tamaño en px físicos: crece con la escala de render y con la altura del lienzo.
      material.uniforms.uScale!.value = frame.renderScale * frame.height * 0.012
      holo.update(frame)
    },
    render(frame) {
      if (points.visible) frame.renderer.render(scene, holo.camera)
    },
    dispose() {
      geometry.dispose()
      material.dispose()
    }
  }
}
