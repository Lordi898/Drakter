/**
 * Capa de prueba neutra: suelo de rejilla holográfica (una draw call, líneas con `fwidth`, fundido por
 * distancia y un anillo de barrido). Sirve para medir el Stage; la estética final es de W8/W9.
 */
import * as THREE from 'three'
import type { StageFrame, StageLayer } from '../types'
import { createHoloCamera } from './holoCamera'

const VERT = /* glsl */ `
out vec3 vWorld;
void main() { vec4 w = modelMatrix * vec4(position, 1.0); vWorld = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`

const FRAG = /* glsl */ `
uniform float uTime; uniform float uSweep; uniform vec3 uColor;
in vec3 vWorld; out vec4 outColor;
float lines(vec2 p, float cell, float width) {
  vec2 g = abs(fract(p / cell - 0.5) - 0.5) / fwidth(p / cell);
  return 1.0 - min(min(g.x, g.y) / width, 1.0);
}
void main() {
  vec2 p = vWorld.xz;
  float minor = lines(p, 1.0, 1.0) * 0.35;
  float major = lines(p, 5.0, 1.4);
  float d = length(p - vec2(0.0, -10.0));
  float fade = exp(-d * 0.055);
  float ring = uSweep * exp(-abs(d - mod(uTime * 6.0, 60.0)) * 1.5);
  float a = (max(minor, major) * (0.6 + ring) + ring * 0.25) * fade;
  // Núcleo blanco donde la línea es más intensa: glow en el propio shader.
  vec3 c = mix(uColor, vec3(1.0), clamp(a - 0.6, 0.0, 1.0));
  outColor = vec4(c * a, a);
}`

export function createGridLayer(order = 10): StageLayer {
  const scene = new THREE.Scene()
  const holo = createHoloCamera()
  const material = new THREE.ShaderMaterial({
    glslVersion: THREE.GLSL3, vertexShader: VERT, fragmentShader: FRAG,
    uniforms: { uTime: { value: 0 }, uSweep: { value: 1 }, uColor: { value: new THREE.Color(0.25, 0.8, 1.0) } },
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide
  })
  const geometry = new THREE.PlaneGeometry(160, 160)
  geometry.rotateX(-Math.PI / 2)
  const mesh = new THREE.Mesh(geometry, material)
  mesh.position.set(0, 0, -10)
  scene.add(mesh)
  let time = 0

  return {
    id: 'test-grid',
    order,
    async init(frame: StageFrame) {
      holo.update(frame)
      await frame.renderer.compileAsync(scene, holo.camera)
    },
    update(frame) {
      // Reducir movimiento: sin barrido, rejilla estática.
      if (!frame.reducedMotion) time += frame.dt
      material.uniforms.uTime!.value = time
      material.uniforms.uSweep!.value = frame.reducedMotion ? 0 : 1
      holo.update(frame)
    },
    render(frame) {
      frame.renderer.render(scene, holo.camera)
    },
    dispose() {
      geometry.dispose()
      material.dispose()
    }
  }
}
