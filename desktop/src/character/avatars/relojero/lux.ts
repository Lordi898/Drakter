// «Lux»: el sistema de materiales del Relojero v2. Sustituye a MeshStandard + PMREM por un entorno de
// estudio ANALÍTICO (caja de luz con bordes nítidos, tiras de contraluz, aro cenital, banda del color de estado)
// con Fresnel de Schlick. Reflejos limpios de alta joyería y menos coste por píxel que el PBR genérico.
import * as THREE from 'three';
import { FACE_GLSL } from './face';
import { FX, FY, FYC } from './geo';

/** Uniformes compartidos por todos los materiales (mismo objeto → una sola actualización por fotograma). */
export const G = {
  uT: { value: 0 }, uGlow: { value: 1 }, uCold: { value: 0 }, uDim: { value: 1 }, uExpo: { value: 1 },
  uKey: { value: new THREE.Color(1, 0.9, 0.76) }, uAccent: { value: new THREE.Color(1, 0.72, 0.38) },
  uRot: { value: new THREE.Vector3() }, uBlush: { value: 0 },
  // Cara: mandíbula, comisuras (izquierda/derecha en pantalla), anchura, redondez.
  uJaw: { value: 0 }, uSmL: { value: 0 }, uSmR: { value: 0 }, uLipW: { value: 0 }, uRound: { value: 0 },
};

export const COMMON = /* glsl */ `
varying vec3 vW;
uniform float uT, uGlow, uCold, uDim, uExpo; uniform vec3 uKey, uAccent;
const vec3 KEY_DIR = vec3(-0.62, 0.55, 0.56);
vec3 envA(vec3 r, float rough) {
  float y = r.y, s = rough * 0.55;
  vec3 c = mix(vec3(0.010, 0.010, 0.015), vec3(0.045, 0.046, 0.062), smoothstep(-0.4, 0.9, y));
  c += vec3(0.11, 0.075, 0.042) * smoothstep(-0.15, -0.85, y);                                   // rebote cálido del suelo
  c += vec3(0.16, 0.15, 0.14) * exp(-pow((y + 0.04) / (0.03 + s), 2.0));                          // horizonte
  vec3 k = normalize(KEY_DIR); float kd = dot(r, k);
  c += uKey * (smoothstep(0.915 - s, 0.94 + s * 0.2, kd) * 3.4 + pow(max(kd, 0.0), 7.0) * 0.3);  // caja de luz principal
  vec3 f = normalize(vec3(0.82, 0.22, 0.52));
  c += uKey * vec3(0.78, 0.84, 1.0) * smoothstep(0.965 - s, 0.985, dot(r, f)) * 1.2;              // relleno pequeño
  float sl = exp(-pow((r.x + 0.74) / (0.045 + s), 2.0)) * smoothstep(-0.3, 0.2, y) * smoothstep(0.95, 0.4, y);
  float sr = exp(-pow((r.x - 0.8) / (0.04 + s), 2.0)) * smoothstep(-0.4, 0.1, y) * smoothstep(0.9, 0.5, y);
  c += sl * vec3(0.55, 0.7, 1.0) * 2.2 + sr * mix(vec3(1.0, 0.82, 0.62), uAccent, 0.55) * 2.4;    // tiras de contraluz
  c += vec3(1.0, 0.94, 0.86) * smoothstep(0.88 - s, 0.975, y) * 1.15;                              // aro cenital
  c += uAccent * exp(-pow((y - 0.16) / (0.07 + s), 2.0)) * 0.45 * uGlow;                          // anillo de estado
  return c * uDim;
}
vec3 envD(vec3 n) {
  vec3 k = normalize(KEY_DIR);
  return (mix(vec3(0.06, 0.055, 0.06), vec3(0.2, 0.19, 0.19), n.y * 0.5 + 0.5) + vec3(0.1, 0.06, 0.03) * max(-n.y, 0.0)
    + uKey * (max(dot(n, k), 0.0) * 1.05 + 0.08) + uAccent * 0.05 * uGlow) * uDim;
}
vec3 aces(vec3 c) { c *= uExpo; return clamp((c * (2.51 * c + 0.03)) / (c * (2.43 * c + 0.59) + 0.14), 0.0, 1.0); }
vec3 bumpN(vec3 n, float h, float k) {
  vec3 sp = vW; vec3 sx = dFdx(sp), sy = dFdy(sp);
  vec3 r1 = cross(sy, n), r2 = cross(n, sx); float det = dot(sx, r1);
  vec3 g = sign(det) * (dFdx(h) * r1 + dFdy(h) * r2) * k;
  return normalize(abs(det) * n - g);
}
`;

const VS = /* glsl */ `
uniform float uT;
varying vec3 vN; varying vec3 vW; varying vec3 vC; varying vec3 vO;
#ifdef MECH
attribute vec2 aPiv; attribute vec3 aRate; uniform vec3 uRot;
#endif
#ifdef FACE
${FACE_GLSL}
#endif
void main() {
  vec3 p = position, n = normal;
  vC = vec3(1.0);
#ifdef USE_COLOR
  vC = color;
#endif
#ifdef MECH
  float a = dot(aRate, uRot), ca = cos(a), sa = sin(a);
  mat2 R = mat2(ca, sa, -sa, ca);
  p.xy = R * (p.xy - aPiv) + aPiv; n.xy = R * n.xy;
#endif
#ifdef FACE
  faceDeform(p, n);
#endif
  vO = position;
  vec4 lp = vec4(p, 1.0);
#ifdef USE_INSTANCING
  lp = instanceMatrix * lp; n = mat3(instanceMatrix) * n;
#endif
#ifdef USE_INSTANCING_COLOR
  vC *= instanceColor;
#endif
  vec4 wp = modelMatrix * lp; vW = wp.xyz; vN = normalize(mat3(modelMatrix) * n);
  gl_Position = projectionMatrix * viewMatrix * wp;
}`;

const PAT: Record<string, string> = {
  guilloche: `float pat(vec3 p){ return 0.5 + 0.5 * sin((p.y + 0.012 * sin(p.x * 24.0 + p.z * 11.0) + 0.004 * sin(p.x * 61.0)) * 210.0); }`,
  cotes: `float pat(vec3 p){ float u = fract((p.x * 0.8 + p.y * 0.6) * 13.0); return 1.0 - pow(abs(u * 2.0 - 1.0), 2.0); }`,
  soleil: `float pat(vec3 p){ float a = atan(p.y + 0.04, p.x); return 0.5 + 0.5 * sin(a * 260.0 + sin(a * 7.0) * 3.0); }`,
  knurl: `float pat(vec3 p){ return 0.5 + 0.5 * sin(atan(p.z, p.y) * 60.0); }`,
};

const FS = /* glsl */ `
${COMMON}
uniform vec3 uBase, uEmis; uniform float uMetal, uRough, uBump, uTint, uRoughVar, uClear;
varying vec3 vN; varying vec3 vC; varying vec3 vO;
#ifdef PATTERN
PATTERN_SRC
#endif
#ifdef FACE
uniform float uBlush;
#endif
void main() {
  vec3 N = normalize(vN); if (!gl_FrontFacing) N = -N;
  vec3 V = normalize(cameraPosition - vW);
  vec3 base = uBase; float rough = uRough, ao = 1.0;
#ifdef AO_IN_COLOR
  ao = vC.r;
#else
  base *= vC;
#endif
#ifdef PATTERN
  float h = pat(vO), fw = clamp(fwidth(h) * 0.9, 0.0, 1.0); h = mix(h, 0.5, fw);
  base *= 1.0 - uTint + 2.0 * uTint * h; rough = clamp(rough + uRoughVar * (h - 0.5), 0.04, 1.0);
  N = bumpN(N, h, uBump * (1.0 - fw));
#endif
#ifdef DIAL
  {
    vec2 q = vec2(vO.x / ${FX.toFixed(3)}, (vO.y - ${FYC.toFixed(3)}) / ${FY.toFixed(3)});
    float e = length(q), a = atan(q.x, q.y) / 6.28318 + 0.5;
    float aw = fwidth(a * 60.0), ew = fwidth(e);
    float m60 = abs(fract(a * 60.0 + 0.5) - 0.5), m12 = abs(fract(a * 12.0 + 0.5) - 0.5) * 5.0;
    float rail = (1.0 - smoothstep(0.0, ew * 1.5, abs(e - 0.905))) + (1.0 - smoothstep(0.0, ew * 1.5, abs(e - 0.955)));
    float tick = (1.0 - smoothstep(0.06, 0.06 + aw, m60)) * step(0.905, e) * step(e, 0.955);
    float hour = (1.0 - smoothstep(0.1, 0.1 + aw, m12)) * step(0.86, e) * step(e, 0.96);
    float ink = clamp(rail * 0.8 + tick + hour, 0.0, 1.0);
    base = mix(base, vec3(0.012, 0.016, 0.05), ink * 0.9);
  }
#endif
#ifdef LIDEDGE
  { float e = smoothstep(0.004, 0.022, vO.z); base = mix(vec3(0.02, 0.018, 0.03), base, e); rough = mix(0.5, rough, e); }
#endif
#ifdef FACE
  { vec2 c1 = vec2(abs(vO.x) - 0.33, vO.y + 0.25); base = mix(base, vec3(0.95, 0.5, 0.42), uBlush * 0.32 * exp(-dot(c1, c1) / 0.012)); }
#endif
  vec3 R = reflect(-V, N); float ndv = clamp(dot(N, V), 0.0, 1.0);
  vec3 F0 = mix(vec3(0.04), base, uMetal);
  vec3 F = F0 + (1.0 - F0) * pow(1.0 - ndv, 5.0) * (1.0 - rough * 0.6);
  vec3 L = normalize(KEY_DIR);
  vec3 spec = envA(R, rough) * F * mix(1.0, uClear, 1.0 - uMetal) + F0 * uKey * pow(max(dot(R, L), 0.0), mix(90.0, 8.0, rough)) * 0.9;
  vec3 diff = base * (1.0 - uMetal) * envD(N) * (1.0 - F * uClear);
  vec3 col = (diff + spec * mix(0.25, 1.0, ao)) * mix(0.35, 1.0, ao * ao) + uEmis;
  col += uAccent * pow(1.0 - ndv, 3.0) * 0.12 * uGlow;
  gl_FragColor = vec4(aces(col), 1.0);
  #include <colorspace_fragment>
}`;

export interface LuxOpts {
  base: [number, number, number]; metal?: number; rough?: number; emis?: [number, number, number];
  pattern?: keyof typeof PAT; bump?: number; tint?: number; roughVar?: number; clear?: number;
  mech?: boolean; face?: boolean; lidEdge?: boolean; dial?: boolean; aoInColor?: boolean; vertexColors?: boolean; side?: THREE.Side;
}

/** Material «lux»: metales (latón, oro rosa, acero, pavonado) y dieléctricos con barniz (esmalte, laca). */
export function lux(o: LuxOpts): THREE.ShaderMaterial {
  const defines: Record<string, string> = {};
  let fs = FS;
  if (o.pattern) { defines.PATTERN = ''; fs = fs.replace('PATTERN_SRC', PAT[o.pattern]!); }
  if (o.mech) defines.MECH = '';
  if (o.face) defines.FACE = '';
  if (o.dial) defines.DIAL = '';
  if (o.aoInColor) defines.AO_IN_COLOR = '';
  if (o.lidEdge) defines.LIDEDGE = '';
  const m = new THREE.ShaderMaterial({
    defines, vertexShader: VS, fragmentShader: fs, vertexColors: o.vertexColors ?? (o.mech || o.aoInColor || false), side: o.side ?? THREE.FrontSide,
    uniforms: {
      ...G,
      uBase: { value: new THREE.Vector3(...o.base) }, uEmis: { value: new THREE.Vector3(...(o.emis ?? [0, 0, 0])) },
      uMetal: { value: o.metal ?? 1 }, uRough: { value: o.rough ?? 0.2 }, uBump: { value: o.bump ?? 0 }, uTint: { value: o.tint ?? 0 },
      uRoughVar: { value: o.roughVar ?? 0 }, uClear: { value: o.clear ?? 1 },
    },
  });
  // Las referencias a G se conservan: Three no clona los objetos de uniforme al compilar.
  return m;
}

/** Colores base lineales (F0 de los metales, albedo de los dieléctricos). */
export const BASE = {
  brass: [0.92, 0.7, 0.36] as [number, number, number],
  rose: [0.96, 0.66, 0.5] as [number, number, number],
  caseGold: [0.78, 0.55, 0.26] as [number, number, number],
  steel: [0.78, 0.79, 0.81] as [number, number, number],
  blued: [0.09, 0.17, 0.62] as [number, number, number],
  enamel: [0.84, 0.76, 0.62] as [number, number, number],
  lacquer: [0.008, 0.009, 0.014] as [number, number, number],
  midnight: [0.02, 0.035, 0.12] as [number, number, number],
  plate: [0.36, 0.38, 0.42] as [number, number, number],
};

/** Cristal de zafiro: solo reflejo nítido del estudio con Fresnel, aditivo. */
export function glassMat(tint: [number, number, number] = [1, 0.95, 0.88], strength = 1): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor,
    uniforms: { ...G, uTint: { value: new THREE.Vector3(...tint) }, uS: { value: strength }, uFlash: { value: 0 } },
    vertexShader: `varying vec3 vN; varying vec3 vW; varying vec3 vO;
      void main(){ vec4 wp = modelMatrix * vec4(position, 1.0); vW = wp.xyz; vO = position; vN = normalize(mat3(modelMatrix) * normal); gl_Position = projectionMatrix * viewMatrix * wp; }`,
    fragmentShader: /* glsl */ `varying vec3 vN; varying vec3 vO;
      ${COMMON}
      uniform vec3 uTint; uniform float uS, uFlash;
      void main(){ vec3 N = normalize(vN), V = normalize(cameraPosition - vW); vec3 R = reflect(-V, N);
        float ndv = clamp(dot(N, V), 0.0, 1.0), F = 0.045 + 0.955 * pow(1.0 - ndv, 5.0);
        vec3 c = envA(R, 0.02) * F * 0.75 * uTint * uS;
        float band = vO.x * 0.8 + vO.y - 1.6 + mod(uT * 0.11, 3.4);
        c += uTint * exp(-band * band * 120.0) * uFlash * 0.4;
        gl_FragColor = vec4(aces(c), 0.0);
        #include <colorspace_fragment>
      }`,
  });
}
