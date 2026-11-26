/**
 * Bloom barato y propio para Cine (jarvis-arquitectura.md §2.4): copia el fotograma ya compuesto,
 * extrae lo brillante a media resolución, lo difumina en dos pasadas y lo suma encima. No usa render
 * targets para las capas, así cada una (el avatar con su `setViewport`) dibuja directo al lienzo.
 */
import * as THREE from 'three'

const VERT = /* glsl */ `
out vec2 vUv;
void main() { vUv = position.xy * 0.5 + 0.5; gl_Position = vec4(position.xy, 0.0, 1.0); }`

const PREFILTER = /* glsl */ `
uniform sampler2D tSrc; uniform vec2 uTexel; uniform float uThreshold;
in vec2 vUv; out vec4 outColor;
void main() {
  // Cuatro muestras bilineales = media de 16 texeles al reducir a la mitad.
  vec3 c = texture(tSrc, vUv + uTexel * vec2(-1.0, -1.0)).rgb + texture(tSrc, vUv + uTexel * vec2(1.0, -1.0)).rgb
         + texture(tSrc, vUv + uTexel * vec2(-1.0, 1.0)).rgb + texture(tSrc, vUv + uTexel * vec2(1.0, 1.0)).rgb;
  c *= 0.25;
  float l = max(c.r, max(c.g, c.b));
  float k = clamp((l - uThreshold) / max(1e-4, 1.0 - uThreshold), 0.0, 1.0);
  outColor = vec4(c * k * k, 1.0);
}`

const BLUR = /* glsl */ `
uniform sampler2D tSrc; uniform vec2 uDir;
in vec2 vUv; out vec4 outColor;
void main() {
  // Gauss de 9 taps con 5 lecturas (muestreo lineal).
  vec3 c = texture(tSrc, vUv).rgb * 0.2270270;
  c += (texture(tSrc, vUv + uDir * 1.3846154).rgb + texture(tSrc, vUv - uDir * 1.3846154).rgb) * 0.3162162;
  c += (texture(tSrc, vUv + uDir * 3.2307692).rgb + texture(tSrc, vUv - uDir * 3.2307692).rgb) * 0.0702703;
  outColor = vec4(c, 1.0);
}`

const COMPOSITE = /* glsl */ `
uniform sampler2D tSrc; uniform float uIntensity;
in vec2 vUv; out vec4 outColor;
void main() { outColor = vec4(texture(tSrc, vUv).rgb * uIntensity, 1.0); }`

export interface Bloom {
  /** Tras dibujar todas las capas en el lienzo; deja el render target en `null`. */
  render(renderer: THREE.WebGLRenderer): void
  dispose(): void
}

export function createBloom(intensity = 0.9, threshold = 0.55): Bloom {
  const camera = new THREE.Camera()
  const geometry = new THREE.BufferGeometry()
  // Triángulo que cubre la pantalla.
  geometry.setAttribute('position', new THREE.Float32BufferAttribute([-1, -1, 0, 3, -1, 0, -1, 3, 0], 3))
  const make = (fragmentShader: string, uniforms: Record<string, THREE.IUniform>, blending: THREE.Blending = THREE.NoBlending) =>
    new THREE.ShaderMaterial({
      glslVersion: THREE.GLSL3, vertexShader: VERT, fragmentShader, uniforms, blending,
      depthTest: false, depthWrite: false, transparent: blending !== THREE.NoBlending
    })
  const prefilter = make(PREFILTER, { tSrc: { value: null }, uTexel: { value: new THREE.Vector2() }, uThreshold: { value: threshold } })
  const blur = make(BLUR, { tSrc: { value: null }, uDir: { value: new THREE.Vector2() } })
  const composite = make(COMPOSITE, { tSrc: { value: null }, uIntensity: { value: intensity } }, THREE.AdditiveBlending)
  const quad = new THREE.Mesh(geometry, prefilter)
  quad.frustumCulled = false

  const rtOptions = { depthBuffer: false, stencilBuffer: false, type: THREE.UnsignedByteType, magFilter: THREE.LinearFilter, minFilter: THREE.LinearFilter }
  const a = new THREE.WebGLRenderTarget(1, 1, rtOptions)
  const b = new THREE.WebGLRenderTarget(1, 1, rtOptions)
  let frame: THREE.FramebufferTexture | null = null
  const size = new THREE.Vector2()

  const pass = (renderer: THREE.WebGLRenderer, material: THREE.ShaderMaterial, target: THREE.WebGLRenderTarget | null): void => {
    quad.material = material
    renderer.setRenderTarget(target)
    renderer.render(quad, camera)
  }

  return {
    render(renderer) {
      renderer.getDrawingBufferSize(size)
      const w = Math.max(1, Math.floor(size.x)), h = Math.max(1, Math.floor(size.y))
      if (!frame || frame.image.width !== w || frame.image.height !== h) {
        frame?.dispose()
        frame = new THREE.FramebufferTexture(w, h)
        frame.minFilter = frame.magFilter = THREE.LinearFilter
        a.setSize(Math.max(1, w >> 1), Math.max(1, h >> 1))
        b.setSize(Math.max(1, w >> 1), Math.max(1, h >> 1))
      }
      const prevTone = renderer.toneMapping
      renderer.toneMapping = THREE.NoToneMapping
      try {
        renderer.setRenderTarget(null)
        renderer.copyFramebufferToTexture(frame)
        prefilter.uniforms.tSrc!.value = frame
        ;(prefilter.uniforms.uTexel!.value as THREE.Vector2).set(1 / w, 1 / h)
        pass(renderer, prefilter, a)
        blur.uniforms.tSrc!.value = a.texture
        ;(blur.uniforms.uDir!.value as THREE.Vector2).set(1 / a.width, 0)
        pass(renderer, blur, b)
        blur.uniforms.tSrc!.value = b.texture
        ;(blur.uniforms.uDir!.value as THREE.Vector2).set(0, 1 / a.height)
        pass(renderer, blur, a)
        composite.uniforms.tSrc!.value = a.texture
        pass(renderer, composite, null)
      } finally {
        renderer.toneMapping = prevTone
        renderer.setRenderTarget(null)
      }
    },
    dispose() {
      frame?.dispose()
      a.dispose()
      b.dispose()
      geometry.dispose()
      prefilter.dispose()
      blur.dispose()
      composite.dispose()
    }
  }
}
