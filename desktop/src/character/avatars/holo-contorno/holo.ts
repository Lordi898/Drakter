// Lenguaje visual del holograma: contornos topográficos sobre la escultura, cintas de luz en espacio de
// pantalla para los rasgos y el pelo, brillos falsos y fondo. Todo aditivo, sin postproceso.
import * as THREE from 'three';
import { DEFORM_GLSL } from './deform';
import { EYE, MOUTH_Y, MOUTH_W } from './sculpt';
import { HAIRLINE_GLSL } from './hair';

/**
 * Uniformes compartidos por todos los materiales de UNA instancia (un objeto → una actualización por
 * fotograma). Van por instancia, no en el módulo: Drakter y el Stage de Jarvis pueden tener dos avatares vivos.
 */
export function holoUniforms() {
  return {
  uT: { value: 0 }, uLineK: { value: 1 }, uVol: { value: new THREE.Vector2(0.025, 0.025) }, uInk: { value: 0 }, uGlow: { value: 1 }, uCold: { value: 0 }, uScan: { value: 0 }, uScanK: { value: 0.6 }, uWarm: { value: 0 },
  uCyan: { value: new THREE.Color(0.32, 0.78, 1.0) }, uDeep: { value: new THREE.Color(0.06, 0.26, 0.9) }, uWhite: { value: new THREE.Color(0.86, 0.95, 1.0) },
  uAccent: { value: new THREE.Color(0.32, 0.78, 1.0) }, uRes: { value: new THREE.Vector2(500, 600) }, uPx: { value: 1 },
  uJaw: { value: 0 }, uSmL: { value: 0 }, uSmR: { value: 0 }, uLipW: { value: 0 }, uRound: { value: 0 }, uLiftL: { value: 0 }, uLiftR: { value: 0 },
  };
}
export type HoloU = ReturnType<typeof holoUniforms>;

export const COMMON = /* glsl */ `
uniform float uInk;
/** Salida: luz aditiva (tema oscuro) o tinta de cobalto premultiplicada (tema claro, grabado sobre papel). */
vec4 outCol(vec3 c) {
  float l = dot(c, vec3(0.3, 0.55, 0.15));
  if (uInk > 0.5) {
    float a = clamp(l * 1.7, 0.0, 0.96);
    vec3 ink = mix(vec3(0.07, 0.2, 0.5), vec3(0.0, 0.26, 0.86), clamp((l - 0.42) * 1.6, 0.0, 1.0));
    return vec4(ink * a, a);
  }
  return vec4(c, clamp(l * 0.6, 0.0, 1.0));
}
uniform float uT, uGlow, uCold, uScan, uScanK, uWarm, uPx; uniform vec3 uCyan, uDeep, uWhite, uAccent; uniform vec2 uRes;
vec3 tint() { return mix(uCyan, uAccent, 0.75); }
`;

// ── Contornos de la escultura (cabeza y busto). FACE activa la deformación facial.
const CONTOUR_VS = /* glsl */ `
${COMMON}
attribute float aAO;
varying vec3 vRest; varying vec3 vN; varying vec3 vW; varying float vAO;
#ifdef FACE
${DEFORM_GLSL}
#endif
void main() {
  vec3 p = position, n = normal;
#ifdef FACE
  deform(p, n);
#endif
  vRest = position; vAO = aAO;
  vec4 wp = modelMatrix * vec4(p, 1.0); vW = wp.xyz; vN = normalize(mat3(modelMatrix) * n);
  gl_Position = projectionMatrix * viewMatrix * wp;
}`;

const CONTOUR_FS = /* glsl */ `
${COMMON}
uniform float uJaw, uSpacing, uFade0, uFade1, uFace, uLineK; uniform vec2 uVol;
varying vec3 vRest; varying vec3 vN; varying vec3 vW; varying float vAO;
const vec3 KEY = vec3(-0.55, 0.55, 0.63);
#ifdef FACE
${HAIRLINE_GLSL}
#endif
/** Línea de grosor w (px) cada 'sp' unidades de la coordenada c. Devuelve (cuerpo, núcleo). */
vec2 iso(float c, float sp, float w) {
  float u = c / sp, fw = max(fwidth(u), 1e-5), d = abs(fract(u + 0.5) - 0.5) / fw; // distancia en px
  return vec2(1.0 - smoothstep(w * 0.5 - 0.5, w * 0.5 + 0.7, d), 1.0 - smoothstep(0.0, w * 0.32 + 0.35, d));
}
void main() {
  vec3 N = normalize(vN), V = normalize(cameraPosition - vW);
  float ndv = clamp(dot(N, V), 0.0, 1.0), lam = clamp(dot(N, normalize(KEY)) * 0.5 + 0.5, 0.0, 1.0);
  float rim = pow(1.0 - ndv, 2.4);
  // Grabado: el trazo engorda en la sombra y adelgaza en la luz.
  float lit = pow(lam, 1.3);
  float w = mix(0.55, 2.1, lit) * uPx;
  float major = step(4.5, mod(floor(vRest.y / uSpacing + 0.5), 5.0));
  vec2 h = iso(vRest.y, uSpacing, w * (1.0 + major * 0.55));
  vec2 v = iso(vRest.z, uSpacing * 1.15, w * 0.9);                     // cortes de perfil (profundidad): anillos topográficos
  // La cara se mantiene limpia: los cortes de perfil se apagan al frente y en ojos y boca.
  float faceFront = uFace * smoothstep(0.55, 0.85, N.z) * (1.0 - smoothstep(0.42, 0.6, abs(vRest.x)));
  vec2 e = vec2(abs(vRest.x) - ${EYE[0].toFixed(3)}, vRest.y - ${EYE[1].toFixed(3)}) / vec2(0.135, 0.058);
  float eyeHole = uFace * (1.0 - smoothstep(0.75, 1.15, length(e))) * step(0.4, vRest.z);
  vec2 m = vec2(vRest.x / ${MOUTH_W.toFixed(3)}, (vRest.y - ${MOUTH_Y.toFixed(3)}) / 0.075);
  float mouth = uFace * (1.0 - smoothstep(0.7, 1.05, length(m))) * step(0.5, vRest.z);
  float hl = h.x * (1.0 - eyeHole) * (1.0 - mouth * 0.75) * mix(0.22, 1.0, lit) * (1.0 - faceFront * 0.42);
  float noseR = uFace * (1.0 - smoothstep(0.09, 0.15, abs(vRest.x))) * smoothstep(-0.5, -0.44, vRest.y) * (1.0 - smoothstep(0.08, 0.16, vRest.y)) * step(0.8, vRest.z);
  float vl = v.x * mix(0.25, 1.0, lit) * (0.35 + 0.65 * uFace) * (1.0 - eyeHole) * (1.0 - mouth * 0.8) * smoothstep(0.15, 0.45, ndv) * (1.0 - smoothstep(0.8, 0.95, ndv)) * 0.6 * (1.0 - noseR * 0.85);
#ifdef FACE
  float sc = scalp(vRest); hl *= 1.0 - 0.72 * sc; vl *= 1.0 - 0.5 * sc;
#endif
  // Profundidad: lo que mira de canto se apaga salvo el borde; abajo el busto se disuelve en luz.
  float depth = mix(0.35, 1.0, pow(ndv, 0.6));
  float fade = smoothstep(uFade0, uFade1, vRest.y);
  float scan = exp(-pow((vW.y - uScan) / 0.05, 2.0)) * uScanK;
  float ao = mix(0.45, 1.0, vAO);
  hl *= 0.55 * uLineK; vl *= uLineK; // uLineK < 1: las curvas de nivel quedan como eco (Holo-Hilo, donde la trama la llevan los filamentos)
  vec3 c = tint() * (hl * (0.55 + 0.45 * major) + vl * 0.85) * depth * ao;
  c += uWhite * (h.y * hl * 0.6 + v.y * vl * 0.75) * (0.45 + 0.4 * lam) * depth * ao;
  c += tint() * (rim * 0.85 + uVol.x + lit * uVol.y) * ao * (1.0 - uInk * 0.55); // volumen y silueta (en tinta, menos aguada)
  c += uWhite * pow(rim, 3.0) * 0.35 * ao;
  c += uWhite * scan * (0.25 + hl * 1.2);
  c = mix(c, c * vec3(1.15, 1.0, 0.8) + vec3(0.03, 0.015, 0.0) * hl, uWarm);
  c *= fade * uGlow * (1.0 - uCold * 0.72) * mix(0.6 + 0.4 * uFace, 1.0 + 0.5 * (1.0 - uFace), uInk);
  gl_FragColor = outCol(c);
}`;

export function contourMat(G: HoloU, face: boolean, spacing: number, fade0: number, fade1: number): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    defines: face ? { FACE: '' } : {}, vertexShader: CONTOUR_VS, fragmentShader: CONTOUR_FS,
    uniforms: { ...G, uSpacing: { value: spacing }, uFade0: { value: fade0 }, uFade1: { value: fade1 }, uFace: { value: face ? 1 : 0 } },
    transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, depthFunc: THREE.LessEqualDepth,
  });
}
/** Prepasada: escribe solo profundidad (la nariz tapa la mejilla; la nuca no se ve a través). */
export function depthMat(G: HoloU, face: boolean): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    defines: face ? { FACE: '' } : {}, vertexShader: CONTOUR_VS, fragmentShader: 'void main(){ gl_FragColor = vec4(0.0); }',
    uniforms: { ...G }, colorWrite: false, depthWrite: true,
  });
}

// ── Cintas de luz en espacio de pantalla.
const LINE_VS = /* glsl */ `
${COMMON}
#ifdef DEFORM
${DEFORM_GLSL}
#endif
attribute vec3 aPrev; attribute vec3 aNext; attribute float aSide; attribute float aW; attribute float aA;
uniform float uGain, uHalo, uSway;
varying float vS; varying float vA; varying float vCore;
void main() {
  mat4 M = projectionMatrix * modelViewMatrix;
  vec3 pp = position, pv = aPrev, pn = aNext;
#ifdef DEFORM
  vec3 nd = vec3(0.0, 0.0, 1.0); deform(pp, nd); deform(pv, nd); deform(pn, nd);
#endif
  vec4 c = M * vec4(pp, 1.0), p = M * vec4(pv, 1.0), n = M * vec4(pn, 1.0);
  vec2 h = uRes * 0.5, sc = c.xy / c.w * h, sp = p.xy / p.w * h, sn = n.xy / n.w * h;
  vec2 t = sn - sp; t = length(t) < 1e-4 ? vec2(1.0, 0.0) : normalize(t);
  float w = max(aW * uPx, 0.6), halo = uHalo * uPx + w * 0.7, tot = w * 0.5 + halo;
  c.xy += vec2(-t.y, t.x) * aSide * tot / h * c.w;
  vS = aSide * tot / (w * 0.5); vA = aA * min(1.0, aW * uPx / 0.9); vCore = clamp((w - 1.2) / 2.5, 0.25, 1.0);
  c.z -= 0.0015 * c.w;
  gl_Position = c;
}`;
const LINE_FS = /* glsl */ `
${COMMON}
uniform float uGain; uniform vec3 uTint; uniform float uTintK;
varying float vS; varying float vA; varying float vCore;
void main() {
  float x = abs(vS);
  float body = 1.0 - smoothstep(0.7, 1.25, x), core = 1.0 - smoothstep(0.0, 0.75, x), halo = exp(-x * x * 0.22) * 0.32;
  vec3 col = mix(tint(), uTint, uTintK);
  vec3 c = (col * (body * 0.8 + halo) + uWhite * core * core * vCore * 1.05) * vA * uGain;
  c = mix(c, c * vec3(1.15, 1.0, 0.8), uWarm);
  gl_FragColor = outCol(c * uGlow * (1.0 - uCold * 0.7));
}`;

/** Lote de polilíneas con disposición fija (mismo nº de trazos y puntos): solo se reescriben posiciones. */
export class LineBatch {
  geo = new THREE.BufferGeometry(); mesh: THREE.Mesh; mat: THREE.ShaderMaterial;
  private P!: Float32Array; private PP!: Float32Array; private PN!: Float32Array; private Wd!: Float32Array; private A!: Float32Array; private layout = '';
  constructor(G: HoloU, gain = 1, halo = 2.2, deform = false) {
    this.mat = new THREE.ShaderMaterial({
      defines: deform ? { DEFORM: '' } : {},
      vertexShader: LINE_VS, fragmentShader: LINE_FS, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, depthTest: true, side: THREE.DoubleSide,
      uniforms: { ...G, uGain: { value: gain }, uHalo: { value: halo }, uSway: { value: 0 }, uTint: { value: new THREE.Color(1, 1, 1) }, uTintK: { value: 0 } },
    });
    this.mesh = new THREE.Mesh(this.geo, this.mat); this.mesh.frustumCulled = false; this.mesh.renderOrder = 4;
  }
  /** Carga polilíneas: pts (xyz planos), w (px), a (0-1). Reconstruye índices solo si cambia la disposición. */
  set(strokes: { pts: ArrayLike<number>; w: ArrayLike<number>; a: ArrayLike<number>; n: number }[]): void {
    const layout = strokes.map((s) => s.n).join(',');
    if (layout !== this.layout) {
      this.layout = layout;
      const nPts = strokes.reduce((k, s) => k + s.n, 0), nv = nPts * 2;
      this.P = new Float32Array(nv * 3); this.PP = new Float32Array(nv * 3); this.PN = new Float32Array(nv * 3); this.Wd = new Float32Array(nv); this.A = new Float32Array(nv);
      const side = new Float32Array(nv), idx: number[] = [];
      let v = 0;
      for (const s of strokes) { for (let i = 0; i < s.n; i++) { side[v * 2] = -1; side[v * 2 + 1] = 1; if (i < s.n - 1) { const a = v * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); } v++; } }
      const g = this.geo; g.dispose();
      g.setAttribute('position', new THREE.BufferAttribute(this.P, 3).setUsage(THREE.DynamicDrawUsage));
      g.setAttribute('aPrev', new THREE.BufferAttribute(this.PP, 3).setUsage(THREE.DynamicDrawUsage));
      g.setAttribute('aNext', new THREE.BufferAttribute(this.PN, 3).setUsage(THREE.DynamicDrawUsage));
      g.setAttribute('aW', new THREE.BufferAttribute(this.Wd, 1).setUsage(THREE.DynamicDrawUsage));
      g.setAttribute('aA', new THREE.BufferAttribute(this.A, 1).setUsage(THREE.DynamicDrawUsage));
      g.setAttribute('aSide', new THREE.BufferAttribute(side, 1));
      g.setIndex(idx);
    }
    let v = 0;
    const P = this.P, PP = this.PP, PN = this.PN;
    for (const s of strokes) {
      const q = s.pts;
      for (let i = 0; i < s.n; i++) {
        const ip = Math.max(0, i - 1) * 3, ii = i * 3, inn = Math.min(s.n - 1, i + 1) * 3;
        for (let k = 0; k < 2; k++) {
          const o = (v * 2 + k) * 3;
          P[o] = q[ii]!; P[o + 1] = q[ii + 1]!; P[o + 2] = q[ii + 2]!;
          PP[o] = q[ip]!; PP[o + 1] = q[ip + 1]!; PP[o + 2] = q[ip + 2]!;
          PN[o] = q[inn]!; PN[o + 1] = q[inn + 1]!; PN[o + 2] = q[inn + 2]!;
          this.Wd[v * 2 + k] = s.w[i]!; this.A[v * 2 + k] = s.a[i]!;
        }
        v++;
      }
    }
    for (const n of ['position', 'aPrev', 'aNext', 'aW', 'aA']) (this.geo.attributes[n] as THREE.BufferAttribute).needsUpdate = true;
  }
}

/** Brillos (pupilas, destellos, polvo): puntos aditivos con tamaño en unidades del mundo. */
export function glowPoints(G: HoloU, n: number): { pts: THREE.Points; pos: Float32Array; col: Float32Array; size: Float32Array; mat: THREE.ShaderMaterial } {
  const geo = new THREE.BufferGeometry(), pos = new Float32Array(n * 3), col = new Float32Array(n * 3), size = new Float32Array(n);
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3).setUsage(THREE.DynamicDrawUsage));
  geo.setAttribute('aCol', new THREE.BufferAttribute(col, 3).setUsage(THREE.DynamicDrawUsage));
  geo.setAttribute('aSize', new THREE.BufferAttribute(size, 1).setUsage(THREE.DynamicDrawUsage));
  const mat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, depthTest: true, blending: THREE.AdditiveBlending, uniforms: { uScale: { value: 600 }, uInk: G.uInk },
    vertexShader: /* glsl */ `attribute vec3 aCol; attribute float aSize; uniform float uScale; varying vec3 vC;
      void main(){ vec4 mv = modelViewMatrix * vec4(position, 1.0); vC = aCol; gl_PointSize = aSize * uScale / -mv.z; gl_Position = projectionMatrix * mv; gl_Position.z -= 0.004 * gl_Position.w; }`,
    fragmentShader: /* glsl */ `uniform float uInk; varying vec3 vC; void main(){ vec2 d = gl_PointCoord - 0.5; float r2 = dot(d, d) * 4.0;
      float a = exp(-r2 * 10.0) + exp(-r2 * 2.5) * 0.3; a *= 1.0 - smoothstep(0.75, 1.0, r2); vec3 c = vC * a; float l = dot(c, vec3(0.3, 0.55, 0.15));
      gl_FragColor = uInk > 0.5 ? vec4(vec3(0.0, 0.2, 0.7) * clamp(l * 1.6, 0.0, 0.9), clamp(l * 1.6, 0.0, 0.9)) : vec4(c, clamp(l * 0.6, 0.0, 1.0)); }`,
  });
  const pts = new THREE.Points(geo, mat); pts.frustumCulled = false; pts.renderOrder = 6;
  return { pts, pos, col, size, mat };
}

/** Fondo: noche azul con un resplandor de proyección bajo el busto. Un triángulo a pantalla completa. */
export function backdrop(G: HoloU): THREE.Mesh<THREE.BufferGeometry, THREE.ShaderMaterial> {
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute([-1, -1, 0, 3, -1, 0, -1, 3, 0], 3));
  const mat = new THREE.ShaderMaterial({
    depthWrite: false, depthTest: false, uniforms: { ...G, uHead: { value: new THREE.Vector2(0.5, 0.62) } },
    vertexShader: `varying vec2 vU; void main(){ vU = position.xy * 0.5 + 0.5; gl_Position = vec4(position.xy, 0.0, 1.0); }`,
    fragmentShader: /* glsl */ `${COMMON} uniform vec2 uHead; varying vec2 vU;
      void main(){ float asp = uRes.x / uRes.y; vec2 d = (vU - uHead) * vec2(asp, 1.0); float r = length(d);
        vec3 c = mix(vec3(0.012, 0.03, 0.065), vec3(0.002, 0.006, 0.016), smoothstep(0.0, 0.9, r));
        c += tint() * 0.05 * exp(-r * r * 6.0) * uGlow;
        float base = exp(-pow((vU.y - 0.02) / 0.06, 2.0)) * exp(-pow((vU.x - 0.5) / 0.35, 2.0));
        c += tint() * base * 0.09 * uGlow;
        c += (fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453) - 0.5) / 255.0;
        gl_FragColor = vec4(c * (1.0 - uCold * 0.5), 1.0);
      }`,
  });
  const m = new THREE.Mesh(geo, mat); m.frustumCulled = false; m.renderOrder = -10;
  return m;
}

/** Mezcla según el tema: aditiva (luz) o premultiplicada (tinta). Sin recompilar: solo factores de mezcla. */
export function setBlend(m: THREE.Material, ink: boolean): void {
  m.blending = THREE.CustomBlending; m.blendEquation = THREE.AddEquation; m.blendEquationAlpha = THREE.AddEquation;
  m.blendSrc = THREE.OneFactor; m.blendDst = ink ? THREE.OneMinusSrcAlphaFactor : THREE.OneFactor;
  m.blendSrcAlpha = THREE.OneFactor; m.blendDstAlpha = THREE.OneMinusSrcAlphaFactor;
}

/** Polvo de luz animado por completo en el vertex shader: ni un byte por fotograma. */
export function dustPoints(G: HoloU, n: number): { pts: THREE.Points; mat: THREE.ShaderMaterial } {
  const geo = new THREE.BufferGeometry(), seed = new Float32Array(n * 4), pos = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) seed.set([Math.sin(i * 12.9898) * 1.6, (i * 0.618) % 1, -0.6 + Math.cos(i * 4.1) * 0.6, i * 1.7], i * 4);
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3)); geo.setAttribute('aSeed', new THREE.BufferAttribute(seed, 4));
  const mat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, depthTest: true, blending: THREE.AdditiveBlending,
    uniforms: { ...G, uScale: { value: 600 }, uK: { value: 1 } },
    vertexShader: /* glsl */ `${COMMON} attribute vec4 aSeed; uniform float uScale, uK; varying vec3 vC;
      void main(){ float v = 0.04 + fract(aSeed.w * 0.217) * 0.08, y = mod(aSeed.y * 4.2 + uT * v, 4.2) - 2.6;
        vec3 p = vec3(aSeed.x + sin(uT * 0.3 + aSeed.w) * 0.1, y, aSeed.z);
        vC = tint() * (0.25 + 0.2 * sin(uT * 1.3 + aSeed.w)) * clamp((1.6 - abs(y + 0.5)) * 0.8, 0.0, 1.0) * (1.0 - uCold * 0.8) * uK;
        vec4 mv = modelViewMatrix * vec4(p, 1.0); gl_PointSize = 0.022 * uScale / -mv.z; gl_Position = projectionMatrix * mv; }`,
    fragmentShader: /* glsl */ `${COMMON} varying vec3 vC; void main(){ vec2 d = gl_PointCoord - 0.5; float r2 = dot(d, d) * 4.0;
      float a = exp(-r2 * 10.0) + exp(-r2 * 2.5) * 0.3; a *= 1.0 - smoothstep(0.75, 1.0, r2); gl_FragColor = outCol(vC * a); }`,
  });
  const pts = new THREE.Points(geo, mat); pts.frustumCulled = false; pts.renderOrder = 6;
  return { pts, mat };
}
