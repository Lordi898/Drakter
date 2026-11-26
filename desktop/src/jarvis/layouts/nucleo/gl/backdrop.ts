/**
 * Fondo y viñeta de Núcleo en el Stage (en el prototipo eran capas DOM a pantalla completa, que
 * obligan al compositor a mezclar dos superficies más). Un triángulo a pantalla completa cada una.
 */
import * as THREE from 'three'
import type { StageLayer } from '../../../stage/types'

const VS = /* glsl */ `varying vec2 vUv; void main(){ vUv = position.xy*0.5+0.5; gl_Position = vec4(position.xy, 0.0, 1.0); }`

function fullscreen(fs: string, uniforms: Record<string, THREE.IUniform>, blending: Partial<THREE.ShaderMaterialParameters>): { scene: THREE.Scene; mat: THREE.ShaderMaterial; geo: THREE.BufferGeometry } {
  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.Float32BufferAttribute([-1, -1, 0, 3, -1, 0, -1, 3, 0], 3))
  const mat = new THREE.ShaderMaterial({ vertexShader: VS, fragmentShader: fs, uniforms, depthTest: false, depthWrite: false, ...blending })
  const mesh = new THREE.Mesh(geo, mat)
  mesh.frustumCulled = false
  const scene = new THREE.Scene()
  scene.add(mesh)
  return { scene, mat, geo }
}
const cam = new THREE.Camera()

/** Abismo azul con el halo central (orden 0, opaco). */
export function createBackdropLayer(): StageLayer & { setOpacity(k: number): void } {
  const u = { uK: { value: 0 }, uAspect: { value: 1 } }
  const { scene, mat, geo } = fullscreen(/* glsl */ `precision mediump float; varying vec2 vUv; uniform float uK, uAspect;
    void main(){ vec2 p = (vUv-vec2(0.5,0.53))*vec2(uAspect,1.0);
      float core = exp(-dot(p/vec2(0.34,0.4), p/vec2(0.34,0.4))*2.2);
      float r = length((vUv-0.5)*vec2(uAspect*0.72,1.0)*1.25);
      vec3 base = mix(vec3(0.039,0.157,0.322), vec3(0.004,0.02,0.051), smoothstep(0.0, 1.0, r));
      vec3 c = mix(vec3(0.004,0.02,0.051), base + vec3(0.157,0.51,1.0)*core*0.3, uK);
      gl_FragColor = vec4(c, 1.0); }`, u, { blending: THREE.NoBlending })
  return {
    id: 'nucleo-backdrop', order: 0,
    setOpacity(k) { u.uK.value = k },
    init() {},
    update(f) { u.uAspect.value = f.width / Math.max(1, f.height) },
    render(f) { f.renderer.render(scene, cam) },
    dispose() { geo.dispose(); mat.dispose() }
  }
}

/** Viñeta y líneas de barrido finas por encima de todo (orden 95). En Ahorro, solo viñeta. */
export function createVignetteLayer(): StageLayer {
  const u = { uScan: { value: 1 }, uH: { value: 800 } }
  const { scene, mat, geo } = fullscreen(/* glsl */ `precision mediump float; varying vec2 vUv; uniform float uScan, uH;
    void main(){ float r = length(vUv-0.5)*1.42; float v = smoothstep(0.52, 1.0, r)*0.78;
      float s = uScan*step(mod(gl_FragCoord.y, 3.0), 1.0)*0.03;
      gl_FragColor = vec4(vec3(0.0,0.012,0.04), v) + vec4(vec3(0.51,0.8,1.0)*s, 0.0); }`, u, { transparent: true, blending: THREE.NormalBlending })
  return {
    id: 'nucleo-vignette', order: 95,
    init() {},
    setQuality(q) { u.uScan.value = q.tier === 'ahorro' ? 0 : 1 },
    update(f) { u.uH.value = f.height },
    render(f) { f.renderer.render(scene, cam) },
    dispose() { geo.dispose(); mat.dispose() }
  }
}
