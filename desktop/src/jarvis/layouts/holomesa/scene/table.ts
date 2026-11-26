/**
 * La Holomesa: un disco de vidrio de luz en perspectiva. Su dibujo (rejilla, anillos, marcas, barrido,
 * emisores, conductos y ondas de voz) sale de UN shader en UN plano; los emisores van como uniformes.
 */
import * as THREE from 'three'
import type { Materials, SharedUniforms } from './materials'

export const TABLE_R = 10
export const MAX_PADS = 8
/** Cabecera de la mesa, donde preside el avatar. */
export const HEAD = new THREE.Vector3(0, 0, -7.2)

export interface Table {
  readonly group: THREE.Group
  readonly uniforms: {
    uDraw: { value: number }
    uPadHover: { value: number[] }
    uPadFocus: { value: number[] }
    uFocus: { value: number }
    uQuality: { value: number }
  }
  setPads(p: readonly THREE.Vector3[], radii: readonly number[]): void
  /** Partículas de polvo que suben (0 = ninguna). */
  setDust(n: number): void
  update(dt: number, voice: number): void
}

const MAX_DUST = 3000

export function createTable(U: SharedUniforms, M: Materials): Table {
  const group = new THREE.Group()
  const pads = Array.from({ length: MAX_PADS }, () => new THREE.Vector3(999, 0, 999))
  const uniforms = {
    ...U,
    uDraw: { value: 1 },
    uPads: { value: pads },
    uPadR: { value: new Array<number>(MAX_PADS).fill(1) },
    uPadHover: { value: new Array<number>(MAX_PADS).fill(0) },
    uPadFocus: { value: new Array<number>(MAX_PADS).fill(0) },
    uFocus: { value: 0 },
    uVoice: { value: 0 },
    uWave: { value: 0 },
    uHead: { value: new THREE.Vector2(HEAD.x, HEAD.z) },
    uColor: { value: new THREE.Color(0x4cc6ff) },
    uQuality: { value: 1 }
  }
  const mat = new THREE.ShaderMaterial({
    uniforms,
    vertexShader: /* glsl */ `varying vec3 vW; void main(){ vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`,
    fragmentShader: /* glsl */ `
      #define PI 3.14159265
      uniform float uTime, uDraw, uFocus, uVoice, uWave, uQuality, uWarn, uOffline;
      uniform vec3 uPads[${MAX_PADS}]; uniform float uPadR[${MAX_PADS}]; uniform float uPadHover[${MAX_PADS}]; uniform float uPadFocus[${MAX_PADS}];
      uniform vec2 uHead; uniform vec3 uColor; varying vec3 vW;
      float ring(float r, float at, float w){ float d = abs(r - at); float f = fwidth(r) * 1.2; return 1.0 - smoothstep(w, w + f, d); }
      float hexGrid(vec2 p){ p *= 1.6; vec2 r = vec2(1.0, 1.7320508); vec2 h = r * 0.5; vec2 a = mod(p, r) - h; vec2 b = mod(p - h, r) - h; vec2 g = dot(a, a) < dot(b, b) ? a : b;
        vec2 q = abs(g); float e = 0.5 - max(dot(q, normalize(r)), q.x); return 1.0 - smoothstep(0.0, fwidth(p.x) * 1.5 + 0.015, e); }
      vec3 tint(vec3 c){ vec3 w = vec3(1.0, 0.3, 0.37) * dot(c, vec3(0.45, 0.45, 0.35)); c = mix(c, w, uWarn * 0.45); return c * (1.0 - uOffline * 0.82); }
      void main(){
        vec2 p = vW.xz; float r = length(p); float a = atan(p.y, p.x); float an = a / (2.0 * PI) + 0.5;
        float R = ${TABLE_R.toFixed(1)};
        if (r > R + 0.6) discard;
        float drawR = (1.0 - uDraw) * (R + 1.2);
        float vis = smoothstep(drawR - 0.2, drawR + 1.2, r) * smoothstep(0.0, 0.08, uDraw);
        float front = ring(r, drawR + 0.2, 0.05) * step(uDraw, 0.999) * step(0.02, uDraw) * 2.2;
        vec3 col = vec3(0.0);
        float edgeFade = smoothstep(R, R * 0.35, r);
        if (uQuality > 0.5) col += uColor * hexGrid(p) * 0.05 * edgeFade * (1.0 - uFocus * 0.4);
        col += uColor * 0.035 * edgeFade;
        float ticksA = step(0.82, fract(an * 360.0)) * ring(r, R - 0.32, 0.16);
        float ticksB = step(0.7, fract(an * 72.0)) * ring(r, R - 0.5, 0.32);
        float rimK = 1.0 - uFocus * 0.65;
        col += rimK * uColor * (ring(r, R, 0.03) * 1.6 + ring(r, R - 0.08, 0.012) * 0.9 + ticksA * 0.45 + ticksB * 0.4);
        col += uColor * ring(r, 7.6, 0.012) * 0.55 + uColor * ring(r, 4.3, 0.01) * 0.35 + uColor * ring(r, 2.35, 0.015) * 0.7;
        float arcs = step(0.5, fract(an * 6.0 + uTime * 0.02)) * step(fract(an * 6.0 + uTime * 0.02), 0.62);
        col += uColor * ring(r, R + 0.32, 0.05) * arcs * 1.2 * rimK;
        float sw = uQuality > 0.0 ? fract(an - uTime * 0.045) : 1.0; float sweep = pow(1.0 - sw, 14.0) * smoothstep(R, 2.0, r) * smoothstep(0.5, 2.5, r);
        col += mix(uColor, vec3(0.8, 0.95, 1.0), 0.4) * sweep * 0.55 * uQuality;
        for (int i = 0; i < ${MAX_PADS}; i++) {
          vec2 c = uPads[i].xz; float pr = uPadR[i]; float d = length(p - c); float hv = uPadHover[i]; float fc = uPadFocus[i];
          float pa = d < pr * 1.5 ? atan(p.y - c.y, p.x - c.x) / (2.0 * PI) + 0.5 : 0.0;
          float k = 1.0 + hv * 1.2 + fc * 1.5;
          if (d < pr * 1.5) {
            col += uColor * ring(d, pr, 0.03) * 1.1 * k;
            col += uColor * ring(d, pr * 1.18, 0.012) * step(0.4, fract(pa * 24.0 + uTime * (0.05 + hv * 0.3))) * 0.9 * k;
            col += uColor * ring(d, pr * 1.36, 0.02) * step(0.85, fract(pa * 4.0 - uTime * 0.07)) * 0.8 * k;
            col += mix(uColor, vec3(1.0), 0.3) * exp(-d * d / (pr * pr) * 2.2) * 0.22 * k;
          }
          vec2 dir = normalize(c + vec2(1e-5)); float along = dot(p, dir); float across = abs(dot(p, vec2(-dir.y, dir.x)));
          float len = length(c) - pr * 1.4;
          if (along > 2.5 && along < len && len > 2.5) {
            float lane = 1.0 - smoothstep(0.012, 0.012 + fwidth(across) * 1.5, across);
            float pk = step(0.9, fract(along * 0.35 - uTime * 0.5 + float(i) * 0.37));
            col += uColor * lane * (0.22 + pk * 1.6) * (1.0 + hv);
          }
        }
        float dh = length(p - uHead);
        float wv = sin(dh * 3.0 - uWave * 6.0) * 0.5 + 0.5; wv = pow(wv, 10.0) * smoothstep(9.0, 0.5, dh) * uVoice;
        col += vec3(0.65, 0.92, 1.0) * wv * 0.5;
        col += uColor * ring(dh, 1.35, 0.03) * (0.8 + uVoice * 1.5) + uColor * ring(dh, 1.7 + uVoice * 0.3, 0.01) * 0.6;
        col *= vis; col += vec3(0.75, 0.95, 1.0) * front;
        gl_FragColor = vec4(tint(col), 1.0);
      }`,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending
  })
  const disc = new THREE.Mesh(new THREE.CircleGeometry(TABLE_R + 0.7, 96), mat)
  disc.rotation.x = -Math.PI / 2
  disc.renderOrder = -2
  group.add(disc)

  // Canto: anillo de luz y faldón con graduación.
  const rimMat = new THREE.ShaderMaterial({
    uniforms: { ...U },
    vertexShader: /* glsl */ `void main(){ gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: /* glsl */ `uniform float uOffline, uWarn, uFocusG; void main(){ vec3 c = mix(vec3(0.55, 0.9, 1.0), vec3(1.0, 0.7, 0.3), uWarn * 0.6); gl_FragColor = vec4(c * 1.2 * (1.0 - uOffline * 0.8) * (1.0 - uFocusG * 0.7), 1.0); }`,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending
  })
  const rim = new THREE.Mesh(new THREE.TorusGeometry(TABLE_R, 0.035, 6, 180), rimMat)
  rim.rotation.x = Math.PI / 2
  group.add(rim)
  const skirtMat = new THREE.ShaderMaterial({
    uniforms: { ...U },
    vertexShader: /* glsl */ `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: /* glsl */ `uniform float uTime, uOffline, uFocusG; varying vec2 vUv;
      void main(){ float s = step(0.5, fract(vUv.x * 240.0)) * 0.5 + 0.5; float g = pow(vUv.y, 3.0) * 0.35 * s;
        float run = smoothstep(0.97, 1.0, fract(vUv.x * 3.0 - uTime * 0.05)) * vUv.y;
        gl_FragColor = vec4(vec3(0.3, 0.7, 1.0) * (g + run * 0.8) * (1.0 - uOffline * 0.8) * (1.0 - uFocusG * 0.7), 1.0); }`,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    side: THREE.DoubleSide
  })
  const skirt = new THREE.Mesh(new THREE.CylinderGeometry(TABLE_R, TABLE_R * 0.97, 0.55, 128, 1, true), skirtMat)
  skirt.position.y = -0.28
  group.add(skirt)

  // Núcleo de luz bajo el vidrio.
  const under = new THREE.Mesh(new THREE.PlaneGeometry(26, 26), M.glowMat(0x1a6dff, 0.55))
  under.rotation.x = -Math.PI / 2
  under.position.y = -0.6
  under.renderOrder = -4
  group.add(under)

  // Polvo de luz que sube de la mesa (tantas partículas como permita el nivel).
  const pos = new Float32Array(MAX_DUST * 3), size = new Float32Array(MAX_DUST), seed = new Float32Array(MAX_DUST)
  for (let i = 0; i < MAX_DUST; i++) {
    const rr = Math.sqrt(Math.random()) * TABLE_R * 1.05, a = Math.random() * Math.PI * 2
    pos[i * 3] = Math.cos(a) * rr
    pos[i * 3 + 1] = -0.2
    pos[i * 3 + 2] = Math.sin(a) * rr
    size[i] = 0.4 + Math.random() * 1.2
    seed[i] = Math.random()
  }
  const dg = new THREE.BufferGeometry()
  dg.setAttribute('position', new THREE.BufferAttribute(pos, 3))
  dg.setAttribute('aSize', new THREE.BufferAttribute(size, 1))
  dg.setAttribute('aSeed', new THREE.BufferAttribute(seed, 1))
  const dust = new THREE.Points(dg, M.pointMat(0x8fdcff, 1.6, 0.05))
  dust.frustumCulled = false
  group.add(dust)

  return {
    group,
    uniforms,
    setPads(p, radii) {
      for (let i = 0; i < MAX_PADS; i++) {
        const v = p[i]
        if (v) pads[i]!.copy(v)
        else pads[i]!.set(999, 0, 999)
        uniforms.uPadR.value[i] = radii[i] ?? 0.001
      }
    },
    setDust(n) {
      dg.setDrawRange(0, Math.max(0, Math.min(MAX_DUST, n)))
      dust.visible = n > 0
    },
    update(dt, voice) {
      uniforms.uVoice.value += (voice - uniforms.uVoice.value) * Math.min(1, dt * 10)
      uniforms.uWave.value += dt * (0.4 + voice * 1.6)
    }
  }
}
