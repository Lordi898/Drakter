// Holo-Hilo: la trama de filamentos. Miles de hebras de luz trazadas sobre la escultura de Holo-Contorno siguiendo
// líneas de flujo anatómicas (órbitas en ojos y boca, caída en mejilla y cuello, abanico en la frente, V en el pecho).
// En la cara usan la MISMA deformación que la piel (DEFORM_GLSL), así que se mueven con cejas, comisuras y mandíbula.
// Los modismos del hilo viven aquí: ovillo (pensar), lanzadera (ejecutar), atar cabos (éxito), perder el hilo (error)
// y deshilachado (sin conexión, y el nacimiento al revés).
import * as THREE from 'three';
import { headSDF, bodySDF, EYE, MOUTH_Y, MOUTH_W, ss } from '../holo-contorno/sculpt';
import { hairline } from '../holo-contorno/hair';
import { DEFORM_GLSL } from '../holo-contorno/deform';
import { COMMON, type HoloU } from '../holo-contorno/holo';

type SDF = (x: number, y: number, z: number) => number;
const NP = 8;
const L = (x: number, y: number, z: number): number => Math.sqrt(x * x + y * y + z * z);
function rng(seed: number): () => number { let a = seed >>> 0; return () => { a = (a + 0x6d2b79f5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

const VS = /* glsl */ `
${COMMON}
#ifdef DEFORM
${DEFORM_GLSL}
#endif
attribute vec3 aDir; attribute vec3 aNrm; attribute vec4 aA; attribute vec4 aS; attribute float aG;
uniform float uCond, uThink, uSpin, uSag, uLoose, uLevel, uShutK, uGain; uniform vec2 uFlash; uniform vec2 uShut; uniform vec3 uBall;
varying float vS; varying float vB; varying float vHot;
float gC; float gTh;
vec3 place(vec3 p, float e) {
  float t = aA.y, seed = aA.z, tip = t * t;
#ifdef DEFORM
  vec3 nd = vec3(0.0, 0.0, 1.0); deform(p, nd);
#endif
  // Los cabos respiran; al perder el hilo, la trama cae.
  vec3 wv = vec3(sin(uT * 1.3 + seed * 40.0 + p.y * 3.0), sin(uT * 1.1 + seed * 23.0 + p.x * 3.0), sin(uT * 0.9 + seed * 61.0));
  p += (wv * 0.014 + aNrm * 0.012 * (0.5 + 0.5 * sin(uT * 0.7 + seed * 17.0))) * tip * uLoose;
  p.y -= uSag * (0.012 + tip * 0.09 * (0.4 + seed));
  // Ovillo: hebras de la coronilla se devanan en un ovillo que flota donde él mira; un hilo lo une a la cabeza.
  float th = aS.w * smoothstep(seed * 0.5, seed * 0.5 + 0.5, uThink); th = th * th * (3.0 - 2.0 * th);
  float hh = fract(seed * 13.3), an = uSpin * (1.2 + 1.6 * fract(seed * 7.0)) + (t - 0.5) * 2.4 + e * 0.07;
  vec3 ax = normalize(vec3(sin(seed * 91.0), cos(seed * 57.0), sin(seed * 33.0 + 1.0))), bu = normalize(cross(ax, vec3(0.3, 1.0, 0.2))), bv = cross(ax, bu);
  vec3 ball = uBall + vec3(0.0, 0.03 * sin(uT * 1.1), 0.0) + (bu * cos(an) + bv * sin(an)) * (0.13 + 0.1 * hh);
  float link = step(fract(seed * 3.17), 0.08);
  ball = mix(ball, mix(p, uBall, t + e * 0.03) + vec3(0.0, sin(3.14159 * t) * 0.09, 0.0), link);
  p = mix(p, ball, th); gTh = th * (1.0 - link * 0.5);
  // Deshilachado: cada hebra se va a su estrella, primero la periferia; vuelve describiendo un arco.
  float c = smoothstep(0.0, 0.3, uCond * 1.3 - aA.w);
  float ang = sin(uT * 0.07 + seed * 6.28) * 0.3, ca = cos(ang), sa = sin(ang);
  vec3 S = vec3(aS.x * ca + aS.z * sa, aS.y + sin(uT * 0.3 + seed * 30.0) * 0.05, -aS.x * sa + aS.z * ca) + aDir * ((t - 0.5) * 0.05 + e * 0.02);
  gC = c;
  return mix(S, p, c) + cross(vec3(0.0, 1.0, 0.0), p - S) * sin(3.14159 * c) * 0.14;
}
void main() {
  float t = aA.y, seed = aA.z;
  vec3 p2 = place(position + aDir * 0.02, 1.0), p1 = place(position, 0.0);
  mat4 M = projectionMatrix * modelViewMatrix;
  vec4 c = M * vec4(p1, 1.0), c2 = M * vec4(p2, 1.0);
  vec2 h = uRes * 0.5, d = (c2.xy / c2.w - c.xy / c.w) * h; float dl = length(d); d = dl > 1e-5 ? d / dl : vec2(1.0, 0.0);
  vec3 wp = (modelMatrix * vec4(p1, 1.0)).xyz, N = normalize(mat3(modelMatrix) * aNrm), V = normalize(cameraPosition - wp);
  float lam = clamp(dot(N, normalize(vec3(-0.55, 0.55, 0.63))) * 0.5 + 0.5, 0.0, 1.0), ndv = clamp(dot(N, V), 0.0, 1.0);
  float b = 0.16 + 0.95 * pow(lam, 2.2) + 0.5 * pow(1.0 - ndv, 3.0); // las hebras se encienden donde da la luz: el volumen lo lleva la escultura
  float hot = 0.25 + 0.6 * pow(lam, 2.0);
  // Pulsos de datos por el hilo; la voz sale de la boca y recorre la trama.
  float gl = smoothstep(0.86, 1.0, sin((t * 1.6 - uT * 0.7 + seed * 9.0) * 6.2832)); b *= 1.0 + gl * 0.4; hot += gl * 0.2;
#ifdef DEFORM
  float dm = distance(position, vec3(0.0, ${MOUTH_Y.toFixed(3)}, 0.9)); float vo = uLevel * exp(-dm * 0.9) * (0.55 + 0.45 * sin(dm * 9.0 - uT * 11.0)); b *= 1.0 + vo * 1.3; hot += vo * 0.6;
#else
  // Lanzadera: una cuenta de luz cruza el pecho de lado a lado y teje fila a fila.
  float row = exp(-pow((position.y - uShut.y) / 0.06, 2.0)), bead = exp(-pow((position.x - uShut.x) / 0.15, 2.0)), sh = uShutK * row * (0.5 + 2.6 * bead); b *= 1.0 + sh * 2.4; hot += sh * 0.6;
#endif
  float fl = exp(-pow((wp.y - uFlash.x) / 0.3, 2.0)) * uFlash.y; b *= 1.0 + fl * 2.0; hot += fl * 0.9; // atar cabos
  float sc = exp(-pow((wp.y - uScan) / 0.05, 2.0)) * uScanK; b *= 1.0 + sc * 1.4; hot += sc * 0.4;        // escaneo
  b *= 1.0 - uSag * step(fract(seed * 5.3), 0.35) * step(0.5, fract(sin(seed * 91.7 + floor(uT * 13.0) * 7.13) * 43758.5)) * 0.9; // hebras fundidas
  b = mix(b, 0.95, gTh); hot = mix(hot, 0.9, gTh);
  float tw = 0.5 + 0.5 * sin(uT * (1.0 + seed * 2.0) + seed * 80.0);
  b = mix((1.3 + 7.0 * pow(tw, 5.0)) / max(uGlow, 0.3), b * aG, gC); // deshilachada, cada hebra es una estrella que titila
  float taper = smoothstep(0.0, 0.2, t) * smoothstep(1.0, 0.7, t);
  float w = max((0.8 + 0.7 * hot + (1.0 - gC) * 0.4) * uPx, 0.6), tot = w * 0.5 + 1.1 * uPx;
  c.xy += vec2(-d.y, d.x) * aA.x * tot / h * c.w;
  c.z -= 0.0012 * c.w;
  vS = aA.x * tot / (w * 0.5); vB = b * taper * uGain; vHot = clamp(hot, 0.0, 1.2);
  gl_Position = c;
}`;
const FS = /* glsl */ `
${COMMON}
varying float vS; varying float vB; varying float vHot;
void main() {
  float x = abs(vS), body = 1.0 - smoothstep(0.7, 1.3, x), core = 1.0 - smoothstep(0.0, 0.7, x), halo = exp(-x * x * 0.3) * 0.22;
  vec3 col = mix(uDeep, tint(), smoothstep(0.1, 0.6, vHot));
  vec3 c = (col * (body * 0.85 + halo) + uWhite * core * core * smoothstep(0.35, 1.0, vHot) * 0.95) * vB; // núcleo blanco solo donde el hilo está encendido
  c = mix(c, c * vec3(1.15, 1.0, 0.8), uWarm);
  gl_FragColor = outCol(c * uGlow * (1.0 - uCold * 0.45));
}`;

/** Uniformes propios de la trama (compartidos por cabeza y busto de UNA instancia). */
export function threadUniforms() {
  return {
  uCond: { value: 0 }, uThink: { value: 0 }, uSpin: { value: 0 }, uSag: { value: 0 }, uLoose: { value: 1 }, uLevel: { value: 0 }, uShutK: { value: 0 },
  uFlash: { value: new THREE.Vector2(0, 0) }, uShut: { value: new THREE.Vector2(0, -2.3) }, uBall: { value: new THREE.Vector3(0.9, 1.05, 0.5) },
  };
}
export type ThreadU = ReturnType<typeof threadUniforms>;

export interface ThreadSet { mesh: THREE.Mesh; mat: THREE.ShaderMaterial; count: number; step(ms: number): boolean }

/** Trama sobre un SDF. `face` activa la deformación facial y el campo de flujo de la cara; si no, el del busto. */
export function threadSet(G: HoloU, TU: ThreadU, face: boolean, quota: number, extraThink = 0): ThreadSet {
  const f: SDF = face ? headSDF : bodySDF, R = rng(face ? 0x411a : 0xb0d1), total = quota + extraThink, V = total * NP * 2;
  const pos = new Float32Array(V * 3), dir = new Float32Array(V * 3), nrm = new Float32Array(V * 3), aA = new Float32Array(V * 4), aS = new Float32Array(V * 4), aG = new Float32Array(V);
  const index = new Uint32Array(total * (NP - 1) * 6);
  for (let s = 0, o = 0; s < total; s++) for (let i = 0; i < NP - 1; i++) { const v = s * NP * 2 + i * 2; index[o++] = v; index[o++] = v + 1; index[o++] = v + 2; index[o++] = v + 1; index[o++] = v + 3; index[o++] = v + 2; }
  const geo = new THREE.BufferGeometry();
  const attr = (n: string, a: Float32Array, k: number): THREE.BufferAttribute => { const b = new THREE.BufferAttribute(a, k); geo.setAttribute(n, b); return b; };
  const attrs = [attr('position', pos, 3), attr('aDir', dir, 3), attr('aNrm', nrm, 3), attr('aA', aA, 4), attr('aS', aS, 4), attr('aG', aG, 1)];
  geo.setIndex(new THREE.BufferAttribute(index, 1)); geo.setDrawRange(0, 0);
  const mat = new THREE.ShaderMaterial({
    defines: face ? { DEFORM: '' } : {}, vertexShader: VS, fragmentShader: FS, transparent: true, depthWrite: false, depthTest: true, side: THREE.DoubleSide,
    uniforms: { ...G, ...TU, uGain: { value: face ? 0.62 : 0.46 } },
  });
  const mesh = new THREE.Mesh(geo, mat); mesh.frustumCulled = false; mesh.renderOrder = 4;

  const g = [0, 0, 1], E = 0.002;
  const grad = (x: number, y: number, z: number): number => { // gradiente (tetraedro) en g; devuelve la distancia media
    const a = f(x + E, y - E, z - E), b = f(x - E, y - E, z + E), c = f(x - E, y + E, z - E), e = f(x + E, y + E, z + E);
    let nx = a - b - c + e, ny = -a - b + c + e, nz = -a + b - c + e; const l = L(nx, ny, nz) || 1; g[0] = nx / l; g[1] = ny / l; g[2] = nz / l; return (a + b + c + e) * 0.25;
  };
  const inEye = (ax: number, y: number, z: number): boolean => ((ax - EYE[0]) / 0.165) ** 2 + ((y - EYE[1]) / 0.085) ** 2 < 1 && z > 0.4;
  const inMouth = (ax: number, y: number, z: number): boolean => ax < MOUTH_W + 0.03 && Math.abs(y - MOUTH_Y) < 0.1 && z > 0.5;
  const scalp = (x: number, y: number, z: number): boolean => y > hairline(x, z) - 0.02 && !(Math.abs(x) > 0.58 && y < 0.16);
  const d3 = [1, 0, 0];
  const flow = (x: number, y: number, z: number): void => {
    const nx = g[0]!, ny = g[1]!, nz = g[2]!; let fx = nz, fy = 0, fz = -nx; // anillos horizontales
    if (face) {
      for (const s of [-1, 1]) { const vx = x - s * EYE[0], vy = y - EYE[1], w = 1.6 * Math.exp(-(vx * vx + vy * vy + (z - 0.78) ** 2) / 0.07), l = Math.hypot(vx, vy) || 1; fx += (s * -vy * w) / l; fy += (s * vx * w) / l; } // orbicular del ojo
      { const vy = y - MOUTH_Y, w = 2.6 * Math.exp(-(x * x + vy * vy + (z - 0.88) ** 2) / 0.08), l = Math.hypot(x, vy) || 1; fx += (-vy * w) / l; fy += (x * w) / l; } // orbicular de la boca
      { const w = 2.5 * Math.exp(-(x * x) / 0.012) * ss(0.2, 0.05, y) * ss(-0.45, -0.3, y) * ss(0.7, 0.85, z); fy -= w; } // dorso de la nariz
      { const w = ss(0.22, 0.34, y) * ss(0.2, 0.5, z), l = Math.hypot(x, y - 0.05) || 1; fx = fx * (1 - w) + (x / l) * 3 * w; fy = fy * (1 - w) + ((y - 0.05) / l) * 3 * w; fz *= 1 - w; } // frontal en abanico
      { const w = ss(0.22, 0.38, Math.abs(x)) * ss(-0.1, -0.24, y) * ss(-1.0, -0.84, y) * ss(0.0, 0.25, z); fx = fx * (1 - w) - Math.sign(x) * 1.2 * w; fy = fy * (1 - w) - 3 * w; fz = fz * (1 - w) + 0.6 * w; } // en la mejilla manda una sola dirección: cae hacia el mentón
      { const w = 2.2 * ss(-1.05, -1.25, y); fy -= w; fx *= 1 - Math.min(1, w) * 0.4; } // tendones del cuello
    } else {
      const w = 2.2 * ss(-0.3, 0.2, z); fx += -Math.sign(x) * 0.55 * w * ss(0.05, 0.3, Math.abs(x)); fy -= w; // V de las solapas
    }
    const dn = fx * nx + fy * ny + fz * nz; fx -= nx * dn; fy -= ny * dn; fz -= nz * dn; const l = L(fx, fy, fz);
    if (l > 1e-4) { d3[0] = fx / l; d3[1] = fy / l; d3[2] = fz / l; }
  };
  const box = face ? [-0.85, 0.85, -1.6, 1.3, -1.15, 1.15] : [-1.7, 1.7, -3.15, -1.75, -0.8, 0.6];
  const P = new Float32Array(NP * 3), Nn = new Float32Array(NP * 3);
  let made = 0, uploaded = 0, tries = 0;
  const step = (ms: number): boolean => { // teje hasta agotar el presupuesto de tiempo: nunca bloquea el hilo
    const t0 = performance.now();
    for (let n = 0; made < total && tries < 400000 && (n % 4 !== 0 || performance.now() - t0 < ms); ) {
      tries++;
      let x = box[0]! + R() * (box[1]! - box[0]!), y = box[2]! + R() * (box[3]! - box[2]!), z = box[4]! + R() * (box[5]! - box[4]!), ok = false;
      for (let i = 0; i < 7; i++) { const d = grad(x, y, z); x -= g[0]! * d; y -= g[1]! * d; z -= g[2]! * d; if (Math.abs(d) < 0.0015) { ok = true; break; } }
      if (!ok || y < box[2]! || y > box[3]!) continue;
      const ax = Math.abs(x), think = made >= quota; let gain = 1, periph = 0.5, loose = 1;
      if (face) {
        const sc = scalp(x, y, z);
        if (think !== sc) continue; // las hebras del ovillo nacen en la coronilla; el resto, en la piel
        if (think && (y < 0.85 || z < -0.5)) continue;
        if (!think && (inEye(ax, y, z) || inMouth(ax, y, z) || (ax > 0.6 && y < 0.2 && y > -0.45 && z < 0.1))) continue; // ni ojos, ni boca, ni orejas
        const frontal = ss(0.0, 0.5, z);
        gain = think ? 0.55 : (0.5 + 0.5 * frontal) * (1 - 0.45 * ss(-0.6, -0.9, y)) * (1 - 0.35 * ss(-1.05, -1.3, y)); // barba y cuello, más tenues: ahí manda el vello // la barba ya tiene su vello
        periph = think ? 0.3 : 0.08 + 0.3 * (1 - frontal) + 0.25 * ss(-1.0, -1.5, y) + R() * 0.1;
      } else { const down = ss(-2.0, -3.1, y); gain = 0.75 * ss(-0.4, 0.2, z) + 0.25; periph = 0.5 + 0.4 * down + R() * 0.1; loose = 1 + 2 * down; }
      const stepL = face ? 0.03 + R() * 0.012 : 0.05, seed = R(); let valid = 0;
      for (let i = 0; i < NP; i++) {
        grad(x, y, z);
        if (face && !think && i > 0 && (inEye(Math.abs(x), y, z) || inMouth(Math.abs(x), y, z) || scalp(x, y, z))) break;
        P.set([x + g[0]! * 0.008, y + g[1]! * 0.008, z + g[2]! * 0.008], i * 3); Nn.set(g, i * 3); valid++;
        flow(x, y, z); x += d3[0]! * stepL; y += d3[1]! * stepL; z += d3[2]! * stepL;
        const d = grad(x, y, z); x -= g[0]! * d; y -= g[1]! * d; z -= g[2]! * d;
      }
      if (valid < 4) continue;
      const mid = Math.min(valid - 1, NP >> 1) * 3, r2 = R(), out = 0.12 + 1.4 * r2 * r2 * r2;
      const sx = P[mid]! + Nn[mid]! * out + (R() - 0.5) * 0.3, sy = P[mid + 1]! + Nn[mid + 1]! * out + (R() - 0.5) * 0.3, sz = P[mid + 2]! + Nn[mid + 2]! * out + (R() - 0.5) * 0.3;
      let v = made * NP * 2;
      for (let i = 0; i < NP; i++) {
        const q = Math.min(i, valid - 1), j = q * 3, t = Math.min(1, i / (valid - 1)), j0 = Math.max(0, q - 1) * 3, j1 = Math.min(valid - 1, q + 1) * 3;
        let tx = P[j1]! - P[j0]!, ty = P[j1 + 1]! - P[j0 + 1]!, tz = P[j1 + 2]! - P[j0 + 2]!; const tl = L(tx, ty, tz) || 1; tx /= tl; ty /= tl; tz /= tl;
        for (let side = -1; side <= 1; side += 2, v++) {
          pos.set([P[j]!, P[j + 1]!, P[j + 2]!], v * 3); dir.set([tx, ty, tz], v * 3); nrm.set([Nn[j]!, Nn[j + 1]!, Nn[j + 2]!], v * 3);
          aA.set([side, t, seed, periph], v * 4); aS.set([sx, sy, sz, think ? 1 : 0], v * 4); aG[v] = gain * (0.7 + 0.6 * R()) * (loose > 1 ? 1 : 1);
        }
      }
      made++; n++;
    }
    if (made > uploaded) { // sube solo las hebras nuevas
      const v0 = uploaded * NP * 2, vn = (made - uploaded) * NP * 2;
      for (const a of attrs) { a.clearUpdateRanges(); a.addUpdateRange(v0 * a.itemSize, vn * a.itemSize); a.needsUpdate = true; }
      uploaded = made; geo.setDrawRange(0, made * (NP - 1) * 6);
    }
    return made >= total || tries >= 400000;
  };
  return { mesh, mat, get count() { return made; }, step };
}
