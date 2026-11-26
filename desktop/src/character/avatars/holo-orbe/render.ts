// Render de «Holo-Orbe»: un solo lienzo WebGL2 y cinco llamadas de dibujo
// (fondo, profundidad de la cáscara, luz de la cáscara con ojos y boca, filamentos, motas).
// Toda la animación ocurre en los shaders; la CPU solo actualiza uniformes. Sin postprocesado:
// el brillo es el perfil gaussiano de cada cinta, sumado de forma aditiva.
import * as THREE from 'three';
import type { Pose, Zone } from './brain';
import { HIST } from './brain';
import { createWeaver, NP, MAXS, PIVOT, MOUTH, EYE, YM } from './bust';

const f = (n: number): string => n.toFixed(4);
// Rig facial compartido por filamentos y cáscara: cejas, mandíbula, labios y comisuras, con pesos calculados al tejer.
const RIG = /* glsl */ `
uniform float uBreath, uSmirk; uniform vec3 uHead; uniform vec4 uGaze, uBrow, uMouth, uLight;
const vec3 PIV = vec3(${PIVOT.join(',')}); const vec3 HINGE = vec3(0., -0.16, -0.05);
vec3 rotHead(vec3 v, float w) {
  float a = uHead.x * w, b = uHead.y * w, c = uHead.z * w;
  float ca = cos(a), sa = sin(a); v = vec3(v.x * ca + v.z * sa, v.y, -v.x * sa + v.z * ca);
  float cb = cos(b), sb = sin(b); v = vec3(v.x, v.y * cb - v.z * sb, v.y * sb + v.z * cb);
  float cc = cos(c), sc = sin(c); return vec3(v.x * cc - v.y * sc, v.x * sc + v.y * cc, v.z);
}
vec3 face(vec3 p, float sx, vec4 C, vec4 D, float jw) {
  float lid = sx < 0. ? uGaze.z : uGaze.w, cl = 1. - clamp(lid, 0., 1.);
  p.y -= D.z * (cl * ${f(EYE.up + EYE.low)} + uBrow.w * 0.01); p.y += D.w * uBrow.w * 0.028;
  float brow = sx < 0. ? uBrow.x : uBrow.y;
  p.y += D.x * brow * 0.13 - D.y * uBrow.z * 0.07; p.x -= sx * D.y * uBrow.z * 0.045;
  float ja = uMouth.x * 0.25 * jw; vec3 q = p - HINGE; float cj = cos(ja), sj = sin(ja);
  p = HINGE + vec3(q.x, q.y * cj - q.z * sj, q.y * sj + q.z * cj);
  float lw = max(max(C.x, C.y), C.z);
  p.y += C.x * uMouth.x * 0.02; p.x *= 1. - lw * (uMouth.y * 0.32 - uMouth.z * 0.14); p.z += lw * uMouth.y * 0.06;
  float sm = uMouth.w + sx * uSmirk;
  p.y += C.z * sm * 0.1 + C.w * max(sm, 0.) * 0.035 + C.y * (1. - C.z) * max(sm, 0.) * 0.012; p.x += sx * C.z * sm * 0.05;
  return p;
}`;

const VERT = /* glsl */ `
attribute vec3 aDir; attribute vec3 aNrm; attribute vec4 aA; attribute vec4 aB; attribute vec4 aC; attribute vec4 aD; attribute vec2 aF;
uniform float uInk, uTime, uTw, uSpin, uHPhase, uBright, uAttract, uStray, uCamZ, uDpr, uExec, uWarm, uErr, uOrbG, uOrbR, uOrbGain, uStrands;
uniform vec2 uRes, uInert; uniform vec3 uKey; uniform vec4 uForm, uFx, uTouch, uRip;
uniform float uHist[${HIST}];
varying vec3 vCol; varying float vSide;
${RIG}
const vec3 MOUTH = vec3(${MOUTH.join(',')}); const vec3 ORBC = vec3(0., -0.06, 0.);
vec3 n0; float gCond; float gFade; float gAmb;

// Donde vive un filamento que no forma parte del busto: el orbe (uOrbG = 0) o el anillo orbital del cuello (uOrbG = 1).
// El enjambre libre, además, se ordena en tres anillos al pensar y en dos hélices ascendentes al ejecutar.
vec3 orbit(float seed, float tt, float e, float isFree) {
  float h1 = fract(seed * 13.31), h2 = fract(seed * 7.137), h3 = fract(seed * 91.73), h4 = fract(seed * 37.91);
  // Orbe: un globo que gira. La mayoría recorre círculos de latitud sobre un eje inclinado (capa exterior nítida
  // y un núcleo interior más rápido); el resto cruza en círculos máximos para dar trama.
  float lat = step(fract(seed * 53.77), 0.74), sLat = 2. * h1 - 1.;
  float inc = pow(h1, 0.7) * 1.3, az = seed * 211.;
  const vec3 AXL = vec3(0.2493, 0.9589, 0.1343);
  vec3 axO = mix(vec3(sin(inc) * cos(az), cos(inc), sin(inc) * sin(az)), AXL, lat);
  float inner = step(h2, 0.3);
  float RS = mix(1.04 + 0.16 * (h2 - 0.3) / 0.7, 0.3 + 0.72 * pow(h2 / 0.3, 0.7), inner) * uOrbR * (1. + 0.035 * sin(uTw * 0.9 + h3 * 6.28));
  vec3 cO = ORBC + AXL * RS * sLat * lat;
  float RO = RS * mix(1., sqrt(max(1. - sLat * sLat, 0.02)), lat);
  float wO = mix((0.5 + 0.8 * h3) / (0.45 + RS), 0.4 + 0.2 * cos(sLat * 4.) + 0.12 * h3 + 0.5 * inner, lat);
  float amb = step(0.64, h4) * isFree; gAmb = amb; // parte del enjambre queda en órbitas amplias y tenues
  vec3 axH = normalize(mix(vec3(0.05, 1., 0.27) + (vec3(h1, h2, h3) - 0.5) * 0.09, axO, amb));
  float RH = mix(1.17 + 0.36 * h2 * h2, 1.72 + 0.62 * h2, amb);
  vec3 cH = mix(vec3(0., -1.4, -0.12), vec3(0., -0.55, 0.), amb);
  float wH = mix(0.36 + 0.22 * h3, 0.1 + 0.1 * h3, amb);
  float g = uOrbG;
  vec3 axis = normalize(mix(axO, axH, g)), cen = mix(cO, cH, g);
  float R = mix(RO, RH, g), arc = mix(0.5 + 0.6 * h4, mix(0.3 + 0.3 * h4, 0.22, amb), g);
  float an = seed * 100. + uSpin * mix(wO * 2.6, wH * 2.2, g) + (tt - 0.5) * arc + e * 0.03;
  vec3 bu = normalize(cross(axis, vec3(0.31, 0.11, 0.94))), bv = cross(axis, bu);
  vec3 pos = cen + (bu * cos(an) + bv * sin(an)) * R;
  float fade = 1.;
  if (isFree > 0.5) {
    float k = floor(h1 * 3.), own = 1. - amb;
    // Pensar: corona inclinada hacia atrás, collar bajo el mentón y un halo casi de frente. Ninguno cruza los rasgos.
    vec3 nT = k < 0.5 ? vec3(0., 0.79, -0.62) : k < 1.5 ? vec3(0.196, 0.627, 0.754) : vec3(0.342, 0.161, 0.926);
    float RT = (k < 0.5 ? 1.3 : k < 1.5 ? 1.44 : 1.4) + (h2 - 0.5) * 0.12, wT = k < 0.5 ? 1. : k < 1.5 ? -0.8 : 0.55;
    float aT = seed * 100. + uSpin * wT * 1.1 + (tt - 0.5) * 0.44 + e * 0.03;
    vec3 tu = normalize(cross(nT, vec3(1., 0., 0.))), tv = cross(nT, tu);
    vec3 T = vec3(0., 0.03, 0.) + (tu * cos(aT) + tv * sin(aT)) * RT;
    float kt = smoothstep(h3 * 0.5, h3 * 0.5 + 0.5, uForm.y) * own;
    pos = mix(pos, T, kt);
    // Ejecutar: dos corrientes que suben en hélice alrededor del busto.
    float ky = mod(h2 * 4.4 + uSpin * 0.8 * (0.7 + 0.6 * h3), 4.4) - 2.7, yy = ky + (tt - 0.5) * 0.36 + e * 0.02;
    float RX = mix(1.6, 1.16, smoothstep(-2.2, -0.4, yy)) + (h4 - 0.5) * 0.14;
    float aX = floor(h1 * 2.) * 3.14159 + (yy + 1.45) * 1.25 + (h3 - 0.5) * 0.42;
    vec3 X = vec3(sin(aX) * RX, yy, cos(aX) * RX - 0.1);
    float kx = smoothstep(h3 * 0.4, h3 * 0.4 + 0.6, uExec) * own;
    pos = mix(pos, X, kx); fade = mix(1., smoothstep(-2.7, -2.2, ky) * smoothstep(1.7, 1.15, ky), kx);
    fade *= mix(1., 0.5, amb * g);
  }
  gFade = fade;
  return pos;
}
vec3 xform(vec3 p, float e) {
  float sx = sign(position.x), tt = aA.y, seed = aA.z, loose = aB.z, tip = tt * tt;
  float isFree = step(0.5, aF.x) * step(aF.x, 1.5);
  p = face(p, sx, aC, aD, aB.y);
  // Soltura: los cabos ondean, respiran, van con retraso respecto a la cabeza y se orientan al escuchar.
  float lz = loose * tip * uForm.z;
  vec3 wv = vec3(sin(uTw * 1.3 + seed * 40. + p.y * 3.), sin(uTw * 1.1 + seed * 23. + p.x * 3.), sin(uTw * 0.9 + seed * 61. + p.z * 2.));
  p += wv * lz * 0.04 + n0 * lz * 0.03 * (0.5 + 0.5 * sin(uTw * 0.7 + seed * 17.));
  p -= (vec3(p.z, 0., -p.x) * uInert.x + vec3(0., -p.z, p.y) * uInert.y) * loose * tip;
  p += vec3(0., 0.1, 1.) * loose * tip * uAttract * 0.09;
  float isStray = step(fract(seed * 17.31), 0.022) * step(0.4, loose);
  p += (n0 * 0.5 + vec3(0., 0.22, 0.) + wv * 0.16) * tip * uStray * isStray * 0.62;
  p.y -= uLight.w * (0.03 + loose * tip * 0.22 * (0.4 + seed));
  p = PIV + rotHead(p - PIV, aB.x);
  p += vec3(0., 0.02, 0.022) * uBreath * (1. - aB.x * 0.6);
  // Condensación: del orbe al busto, primero el rostro y luego la periferia, describiendo arcos.
  vec3 Q = orbit(seed, tt, e, isFree);
  float c = smoothstep(0., 0.3, uForm.x * 1.3 - aA.w - fract(seed * 29.7) * 0.06);
  c *= 1. - uForm.w * smoothstep(0.965, 0.998, sin(uTime * 0.19 + seed * 50.)) * step(0.3, aA.w);
  c *= 1. - isFree;
  vec3 arc = cross(vec3(0., 1., 0.), p - Q) * sin(3.14159 * c) * 0.22;
  gCond = c;
  return mix(Q, p, c) + arc;
}
vec3 ramp(float h) { // temperatura del holograma: añil, azul, cian hielo, blanco
  vec3 c = mix(vec3(0.012, 0.06, 0.36), vec3(0.03, 0.34, 1.0), smoothstep(-0.05, 0.3, h));
  c = mix(c, vec3(0.28, 0.76, 1.0), smoothstep(0.25, 0.7, h));
  return mix(c, vec3(0.86, 0.97, 1.0), smoothstep(0.75, 1.3, h));
}
void main() {
  n0 = normalize(aNrm);
  float kind = aF.x, tt = aA.y, seed = aA.z;
  vec3 p2 = xform(position + aDir * 0.02, 1.);
  vec3 p1 = xform(position, 0.);
  float c = gCond;
  vec3 N = rotHead(n0, aB.x);
  vec3 dT = p1 - uTouch.xyz; float tk = exp(-dot(dT, dT) * 11.) * uTouch.w; // la mano que pasa
  float dR = length(p1 - uRip.xyz), rk = exp(-pow((dR - uRip.w * 2.4) / 0.14, 2.)) * exp(-uRip.w * 1.7); // onda del clic
  vec3 push = N * (tk * 0.07 * (0.3 + aB.z) + rk * 0.06) * c; p1 += push; p2 += push;
  vec4 mv = modelViewMatrix * vec4(p1, 1.);
  vec4 c1 = projectionMatrix * mv, c2 = projectionMatrix * modelViewMatrix * vec4(p2, 1.);
  vec2 d = (c2.xy / c2.w - c1.xy / c1.w) * uRes; float dl = length(d); d = dl > 1e-5 ? d / dl : vec2(1., 0.);
  // Luz: los filamentos se iluminan como un sólido (difusa + contorno).
  vec3 Nv = normalize(normalMatrix * N); float ndv = Nv.z;
  float facing = smoothstep(-0.3, 0.3, ndv), diff = max(dot(Nv, uKey), 0.), rim = pow(1. - abs(ndv), 3.);
  float fill = max(dot(Nv, vec3(0.62, -0.1, 0.78)), 0.);
  float dI = mix(diff, 1. - 0.8 * diff, uInk); // en tinta, la sombra es la que lleva más línea
  float b = (0.07 + 0.95 * dI * dI + 0.2 * fill + 0.5 * rim) * mix(0.2, 1., facing);
  float heat = uLight.x - 0.2 + diff * 0.42 + tk * 0.6 + rk * 0.8;
  // La voz viaja por la trama: sale de la boca al hablar y converge hacia la cabeza al escuchar.
  float a = mix(distance(position, MOUTH), max(0., 2.7 - distance(position, vec3(0., 0.1, 0.))), uFx.y) * 5.5;
  float fh = a + 1. - uHPhase; int i0 = int(clamp(fh, 0., ${HIST - 2}.)); float hv = mix(uHist[i0], uHist[i0 + 1], clamp(fh - float(i0), 0., 1.)) * exp(-a * 0.1);
  heat += hv * 0.5; b *= 1. + hv * 0.7;
  float gl = smoothstep(0.86, 1., sin((tt * 1.6 - uTw * (0.6 + uFx.x * 1.8) + seed * 9.) * 6.2832)); // pulsos que recorren el hilo
  b *= 1. + gl * (0.25 + uFx.x * 2.3); heat += gl * uFx.x * 0.35;
  float fl = exp(-pow((p1.y - uFx.z) / 0.36, 2.)) * uFx.w; heat += fl * 0.8; b *= 1. + fl * 1.7;
  if (kind > 1.5) {
    if (kind < 2.5) { b = b * 1.1 + 0.25; heat += 0.34; } // cejas canas: blancas y densas
    else if (kind < 3.5) { b = b * 0.9 + 0.3; heat += 0.26; } // labios
    else if (kind < 4.5) { heat += 0.05; } // líneas de la edad
    else { heat += 0.1; } // pelo plateado
  }
  // En órbita cada filamento titila; el núcleo del orbe es más blanco y el anillo late con la voz.
  float tw = 0.5 + 0.5 * sin(uTime * (1. + seed * 2.) + seed * 80.);
  float core = smoothstep(1.0, 0.4, length(p1 - ORBC));
  float bO = mix(0.5 + 1.5 * pow(tw, 5.) + 0.5 * core, 0.7 + 0.5 * gl + 1.4 * uHist[0], uOrbG) * gFade;
  bO *= 1. + (uForm.y + uExec) * (1. - gAmb) * step(0.5, kind) * step(kind, 1.5) * (0.5 + 1.6 * gl);
  float hO = mix(0.34 + 0.5 * core, 0.5 + 0.3 * gl, uOrbG) + (uForm.y + uExec) * 0.12;
  // Lo que orbita no pasa por delante de la cara: se atenúa al cruzarla.
  float veil = smoothstep(0., 0.4, p1.z) * smoothstep(1.15, 0.85, length((p1.xy - vec2(0., -0.2)) / vec2(0.62, 0.8))) * uOrbG;
  bO *= 1. - 0.88 * veil;
  b = mix(bO, b, c); heat = mix(hO, heat, c) + sin(3.14159 * c) * 0.5; // en vuelo, el hilo se pone al blanco
  float sick = step(fract(seed * 5.3), 0.42);
  b *= 1. - uLight.z * sick * step(0.5, fract(sin(seed * 91.7 + floor(uTime * 13.) * 7.13) * 43758.5)) * 0.93; // filamentos que fallan
  float gain = mix(uOrbGain, aB.w, c);
  vec3 col = ramp(heat);
  float lum = dot(col, vec3(0.3, 0.5, 0.2));
  col = mix(col, vec3(1.0, 0.92, 0.78) * (0.35 + lum), clamp(uWarm, 0., 1.) * 0.72); // éxito: blanco cálido
  col = mix(col, mix(vec3(1.0, 0.5, 0.1), vec3(1.0, 0.2, 0.07), fract(seed * 3.7)) * (0.6 + lum), uErr * sick * (1. - step(4.5, kind)) * (1. - step(1.5, kind) * step(kind, 2.5))); // error: ámbar y rojo, nunca en el pelo
  col = mix(col, vec3(0.3, 0.4, 0.56) * (0.45 + 0.4 * lum), uLight.y * 0.85); // sin conexión: apagado
  float depth = 1. + (mv.z + uCamZ) * 0.16;
  float taper = smoothstep(0., 0.2, tt) * smoothstep(1., 0.68, tt);
  if (kind > 2.5 && kind < 3.5) taper = smoothstep(0.275, 0.2, abs(position.x)); // los labios son contornos continuos
  else if (kind > 3.5 && kind < 4.5) taper = smoothstep(1., 0.55, tt);
  vCol = col * b * gain * taper * uBright * uStrands * clamp(depth, 0.55, 1.3);
  float wpx = (mix(0.72, 0.9, c) + 0.4 * clamp(heat, 0., 1.3) * c + aF.y * c) * uDpr * clamp(depth, 0.7, 1.25) * (0.55 + 0.45 * taper);
  c1.xy += vec2(-d.y, d.x) * aA.x * wpx * 2. / uRes * c1.w;
  // Un poco hacia la cámara en profundidad, para no pelearse con la cáscara sobre la que descansa.
  vec4 cb = projectionMatrix * (mv + vec4(0., 0., 0.05, 0.)); c1.z = cb.z / cb.w * c1.w;
  gl_Position = c1; vSide = aA.x;
}`;
const EMIT = /* glsl */ `uniform float uInk;
vec4 emit(vec3 c) { // tema oscuro: luz aditiva con alfa; tema claro: tinta de cobalto que satura sin quemarse
  float m = max(c.r, max(c.g, c.b)); if (uInk < 0.5) return vec4(c, min(m, 1.));
  vec3 hue = c / max(m, 1e-3); float a = clamp(m * 1.5, 0., 1.);
  return vec4(mix(hue * hue * 0.6, vec3(0.02, 0.1, 0.45), 0.5) * a, a);
}`;
const FRAG = /* glsl */ `
varying vec3 vCol; varying float vSide; ${EMIT}
void main() { float d = vSide * vSide; gl_FragColor = emit(vCol * (exp(-d * 4.5) * 0.9 + 0.1 * (1. - d))); }`;

// ── Cáscara: el mismo busto como superficie. Un pase escribe profundidad (punteada mientras se condensa)
// y otro suma una luz tenue de holograma, con los ojos y el interior de la boca dibujados por píxel.
const SHELL_VERT = /* glsl */ `
attribute vec3 aNrm; attribute vec4 aB; attribute vec4 aC; attribute vec4 aD;
varying vec3 vN; varying vec3 vP0; varying float vK; varying float vH;
${RIG}
void main() {
  vec3 p = face(position, sign(position.x), aC, aD, aB.y);
  p.y -= uLight.w * 0.03;
  p = PIV + rotHead(p - PIV, aB.x);
  p += vec3(0., 0.02, 0.022) * uBreath * (1. - aB.x * 0.6);
  vN = normalMatrix * rotHead(aNrm, aB.x); vP0 = position; vK = aB.z; vH = aB.w;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.);
}`;
const IGN = /* glsl */ `float ign(vec2 p) { return fract(52.9829189 * fract(dot(p, vec2(0.06711056, 0.00583715)))); }`;
const DEPTH_FRAG = /* glsl */ `
uniform float uShellK; varying float vK; ${IGN}
void main() { if (ign(gl_FragCoord.xy) >= uShellK * vK * 0.7) discard; gl_FragColor = vec4(0.); }`;
const SHELL_FRAG = /* glsl */ `
uniform float uShellK, uShell, uBright, uVerge, uTime, uWarm; uniform vec3 uKey; uniform vec4 uGaze, uBrow, uMouth, uLight, uFx;
${EMIT}
varying vec3 vN; varying vec3 vP0; varying float vK; varying float vH;
void main() {
  vec3 N = normalize(vN); float ndv = clamp(N.z, 0., 1.);
  float diff = max(dot(N, uKey), 0.), fill = max(dot(N, vec3(0.62, -0.1, 0.78)), 0.);
  float rim = pow(1. - ndv, 2.1) * smoothstep(0.02, 0.2, ndv);
  float lum = mix(0.02 + 0.17 * diff * diff + 0.05 * fill, 0.02 + 0.2 * pow(1. - diff, 2.), uInk) + 0.95 * rim;
  lum *= 0.72 + 0.5 * smoothstep(0.55, 1., sin(vP0.y * 118. + uTime * 1.4)); // la superficie es luz: finas líneas de latitud que suben
  lum *= 1. - 0.72 * vH; // bajo el pelo, la cáscara casi no brilla
  lum *= 0.93 + 0.07 * sin(gl_FragCoord.y * 1.57 - uTime * 2.2); // trama de barrido, muy leve
  lum *= 1. + exp(-pow((vP0.y - uFx.z) / 0.36, 2.)) * uFx.w * 1.6;
  vec3 col = mix(vec3(0.02, 0.13, 0.6), vec3(0.22, 0.7, 1.0), clamp(diff * 0.9 + rim * 1.2, 0., 1.)) * lum * uShell;
  float sx = sign(vP0.x);
  // ── Ojo: esclerótica tenue, iris de fibras radiales con anillo limbal, pupila, brillo y párpados nítidos.
  vec2 l = vec2((vP0.x - sx * ${f(EYE.x)}) * sx, vP0.y - ${f(EYE.y)}); float u = l.x / ${f(EYE.halfW)}; // u: -1 lagrimal, +1 exterior
  if (abs(u) < 1.3 && abs(l.y) < 0.17 && vP0.z > 0.45) {
    float lid = sx < 0. ? uGaze.z : uGaze.w, uu = clamp(u, -1., 1.), s = 1. - uu * uu, tilt = 0.014 * uu;
    float sU = pow(s, 0.55) * (1. - 0.16 * uu), sL = pow(s, 0.75) * (1. + 0.22 * uu);
    float yL = -(${f(EYE.low)} - uBrow.w * 0.034) * sL + tilt, yU0 = ${f(EYE.up)} * sU + tilt;
    float yU = mix(yL, yU0, clamp(lid, 0., 1.)) + max(lid - 1., 0.) * 0.04 * sU;
    float aa = 0.006, ends = smoothstep(1.0, 0.93, abs(u));
    float ap = smoothstep(-aa, aa, yU - l.y) * smoothstep(-aa, aa, l.y - yL) * ends;
    vec2 nxy = vec2(l.x * sx, l.y) / ${f(EYE.r)}; vec3 n = vec3(nxy, sqrt(max(1. - dot(nxy, nxy), 0.02)));
    float gy = uGaze.x * 0.5 - sx * uVerge * 0.4, gp = uGaze.y * 0.42;
    vec3 g = vec3(sin(gy) * cos(gp), -sin(gp), cos(gy) * cos(gp));
    vec3 rt = normalize(cross(vec3(0., 1., 0.), g)), up = cross(g, rt);
    float ia = dot(n, rt), ib = dot(n, up), rho = length(vec2(ia, ib)), az = atan(ib, ia);
    float iris = smoothstep(0.455, 0.425, rho), pupil = smoothstep(0.17, 0.2, rho);
    float fib = 0.5 + 0.5 * sin(az * 34. + sin(az * 9.) * 1.5 + rho * 18.);
    float limb = exp(-pow((rho - 0.4) / 0.04, 2.)), coll = exp(-pow((rho - 0.235) / 0.03, 2.));
    float irisL = pupil * (0.42 + 0.5 * fib * smoothstep(0.18, 0.44, rho) + 0.75 * limb + 0.14 * coll);
    float shade = 1. - 0.6 * smoothstep(yU - 0.05, yU, l.y); // sombra del párpado superior
    float eyeL = mix(0.17 + 0.3 * diff, irisL * 1.45, iris) * shade;
    if (uInk > 0.5) eyeL = mix(0.07, mix(1.0, 0.4 + 0.25 * fib + 0.3 * limb, pupil), iris) + 0.25 * (1. - shade);
    eyeL += smoothstep(0.085, 0.035, length(n.xy - vec2(-0.2, 0.2) - g.xy * 0.55)) * mix(1.5, -1.2, uInk); eyeL = max(eyeL, 0.); // brillo de la mirada
    vec3 eyeC = mix(vec3(0.16, 0.5, 1.0), vec3(0.72, 0.93, 1.0), clamp(eyeL - 0.25, 0., 1.)) * eyeL * 1.3;
    col = mix(col, eyeC, ap);
    float open = clamp(lid, 0., 1.);
    float lineU = exp(-pow((l.y - yU - 0.004) / 0.011, 2.)) * smoothstep(1.12, 0.9, abs(u)) * (0.75 + 0.25 * uu);
    float lineL = exp(-pow((l.y - yL + 0.003) / 0.007, 2.)) * ends * (0.4 + 0.3 * uu);
    float crease = exp(-pow((l.y - (yU0 + 0.03 + 0.022 * sU)) / 0.007, 2.)) * smoothstep(1.05, 0.5, abs(u)) * open;
    col += vec3(0.6, 0.9, 1.0) * (lineU * 1.45 + lineL * 0.55 * (0.4 + 0.6 * open) + crease * 0.28);
  }
  // ── Interior de la boca: la franja entre las dos filas de la línea de los labios se abre con la mandíbula.
  if (abs(vP0.x) < 0.27 && vP0.z > 0.6) {
    float m = (${f(YM + 0.004)} - vP0.y) / 0.008;
    if (m > 0. && m < 1.) {
      float h = uMouth.x * 0.27 * (1. - 0.5 * pow(vP0.x / 0.25, 2.)) + 0.008, dd = m * h, db = (1. - m) * h;
      col = mix(vec3(0.004, 0.012, 0.04), vec3(0.1, 0.3, 0.7) * smoothstep(0., 0.03, min(dd, db) + 0.01), uInk); // sin dientes: una sombra limpia
    }
  }
  col = mix(col, vec3(1.0, 0.94, 0.84) * dot(col, vec3(0.3, 0.5, 0.2)) * 1.2, clamp(uWarm, 0., 1.) * 0.5);
  gl_FragColor = emit(col * uBright * uShellK * uShellK * vK);
}`;

const DUST_VERT = /* glsl */ `
attribute vec3 aR;
uniform float uTime, uTw, uBurst, uB, uCold, uScale;
varying vec3 vCol;
void main() {
  float seed = aR.x, ang = uTw * 0.05 * (0.4 + seed) + seed * 6.28, ca = cos(ang), sa = sin(ang);
  vec3 p = vec3(position.x * ca + position.z * sa, position.y + sin(uTw * 0.25 + aR.z) * 0.12, -position.x * sa + position.z * ca);
  p += normalize(position - vec3(0., -0.4, 0.)) * uBurst * (1. - uBurst) * 4. * (0.4 + seed); // ráfaga al acertar
  vec4 mv = modelViewMatrix * vec4(p, 1.);
  float tw = 0.5 + 0.5 * sin(uTime * (0.8 + seed * 2.5) + aR.z * 7.);
  gl_PointSize = aR.y * 0.8 * uScale * (0.7 + 0.6 * tw) * (1. + uBurst * 1.5) / -mv.z;
  vec3 col = mix(vec3(0.1, 0.42, 1.0), vec3(0.6, 0.9, 1.0), seed);
  vCol = mix(col, vec3(0.35, 0.42, 0.55), uCold) * (0.16 + 0.55 * tw * tw) * uB * (1. + uBurst * 2.);
  gl_Position = projectionMatrix * mv;
}`;
const DUST_FRAG = /* glsl */ `
varying vec3 vCol; ${EMIT}
void main() { vec2 q = gl_PointCoord - 0.5; gl_FragColor = emit(vCol * exp(-dot(q, q) * 18.)); }`;

const BG_VERT = /* glsl */ `void main() { gl_Position = vec4(position.xy, 0., 1.); }`;
const BG_FRAG = /* glsl */ `
uniform vec2 uRes, uHalo, uOrigin; uniform float uGlow, uCold;
void main() {
  vec2 uv = (gl_FragCoord.xy - uOrigin) / uRes; vec2 q = (uv - uHalo) * vec2(uRes.x / uRes.y, 1.); float r2 = dot(q, q);
  vec3 ink = mix(vec3(0.012, 0.024, 0.062), vec3(0.002, 0.004, 0.014), smoothstep(0.1, 1., length((uv - vec2(0.5, 0.56)) * vec2(1.1, 1.25)) * 1.45));
  ink += mix(vec3(0.012, 0.07, 0.2) * uGlow, vec3(0.02, 0.03, 0.05), uCold) * (exp(-r2 * 9.) * 0.3 + exp(-r2 * 2.2) * 0.16);
  ink += (fract(52.9829189 * fract(dot(gl_FragCoord.xy, vec2(0.06711056, 0.00583715)))) - 0.5) / 255.; // sin bandas en el degradado
  gl_FragColor = vec4(ink, 1.);
}`;

export interface AvatarRenderer {
  render(p: Pose, dt: number): void;
  resize(w: number, h: number, dpr: number): void;
  face(): { x: number; y: number };
  hit(x: number, y: number): Zone | null;
  /** Cursor sobre el escenario (px) o null si sale: excita los filamentos cercanos. Devuelve si toca el busto. */
  touch(x: number | null, y?: number): boolean;
  info: { strands: () => number; weaveMs: () => number; woven: () => boolean; calls: () => number };
  /** Teje durante `ms` como mucho y sube lo nuevo. Devuelve true al terminar. */
  weave(ms: number): boolean;
  compile(): Promise<void>;
  /** Reserva búferes y geometría; se llama en una tarea distinta de la creación de la escena. */
  init(): void;
  /** Solo para revisar la escultura: 0 normal, 1 solo cáscara, 2 solo filamentos. */
  view(mode: number): void;
  /** Tema de la app: en el claro, el holograma pasa a tinta de cobalto con mezcla normal. */
  theme(light: boolean): void;
  /** Esquina inferior izquierda del recuadro en píxeles del framebuffer (para el fondo propio). */
  setOrigin(x: number, y: number): void;
  dispose(): void;
}

/**
 * Escena del holograma sobre un renderer AJENO (el del envoltorio o el Stage de Jarvis): nunca cambia su
 * tamaño, su densidad ni lo libera. `setOrigin` da la esquina del recuadro en píxeles del framebuffer.
 */
export function createScene(gl: THREE.WebGLRenderer, transparent = false): AvatarRenderer {
  if (!gl.capabilities.isWebGL2) throw new Error('webgl2-unavailable');
  const scene = new THREE.Scene(), FOV = 26, cam = new THREE.PerspectiveCamera(FOV, 1, 4, 30), LOOK_Y = -0.45;
  // Búferes reservados de antemano (en init(), en una tarea aparte): el tejedor los rellena por tandas y solo se sube a la GPU el tramo nuevo.
  let weaver: ReturnType<typeof createWeaver> | null = null, uploaded = 0, shellUp = false, viewMode = 0;
  const geo = new THREE.BufferGeometry(), attrs: THREE.BufferAttribute[] = [], sgeo = new THREE.BufferGeometry();
  const init = (): void => {
    if (weaver) return; weaver = createWeaver(); const W = weaver.W;
    const attr = (name: string, arr: Float32Array | Uint8Array, n: number, norm = false): void => { const a = new THREE.BufferAttribute(arr, n, norm); a.setUsage(THREE.DynamicDrawUsage); geo.setAttribute(name, a); attrs.push(a); };
    attr('position', W.pos, 3); attr('aDir', W.dir, 3); attr('aNrm', W.nrm, 3); attr('aA', W.a, 4); attr('aB', W.b, 4); attr('aC', W.c, 4, true); attr('aD', W.d, 4, true); attr('aF', W.f, 2);
    const index = new Uint32Array(MAXS * (NP - 1) * 6);
    for (let st = 0, o = 0; st < MAXS; st++) for (let i = 0; i < NP - 1; i++) { const v = st * NP * 2 + i * 2; index[o++] = v; index[o++] = v + 1; index[o++] = v + 2; index[o++] = v + 1; index[o++] = v + 3; index[o++] = v + 2; }
    geo.setIndex(new THREE.BufferAttribute(index, 1)); geo.setDrawRange(0, 0); mesh.visible = true;
  };
  const v4 = (): { value: THREE.Vector4 } => ({ value: new THREE.Vector4() });
  const U = {
    uInk: { value: 0 }, uTime: { value: 0 }, uTw: { value: 0 }, uSpin: { value: 0 }, uBreath: { value: 0 }, uHPhase: { value: 0 }, uBright: { value: 1 },
    uAttract: { value: 0 }, uStray: { value: 0 }, uVerge: { value: 0 }, uCamZ: { value: 11 }, uDpr: { value: 1 }, uSmirk: { value: 0 }, uExec: { value: 0 }, uWarm: { value: 0 }, uErr: { value: 0 },
    uOrbG: { value: 0 }, uOrbR: { value: 1 }, uOrbGain: { value: 0.3 }, uShellK: { value: 0 }, uShell: { value: 1 }, uStrands: { value: 1 },
    uRes: { value: new THREE.Vector2(1, 1) }, uInert: { value: new THREE.Vector2() },
    uHead: { value: new THREE.Vector3() }, uKey: { value: new THREE.Vector3(-0.46, 0.5, 0.73).normalize() },
    uGaze: v4(), uBrow: v4(), uMouth: v4(), uForm: v4(), uLight: v4(), uFx: v4(), uTouch: v4(), uRip: { value: new THREE.Vector4(0, 0, 0, 9) }, uHist: { value: new Float32Array(HIST) },
  };
  const add = { blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneFactor, depthWrite: false, transparent: true } as const;
  const mat = new THREE.ShaderMaterial({ vertexShader: VERT, fragmentShader: FRAG, uniforms: U, ...add, depthTest: true, side: THREE.DoubleSide });
  const mesh = new THREE.Mesh(geo, mat); mesh.frustumCulled = false; mesh.renderOrder = 3; mesh.visible = false;
  const depthMat = new THREE.ShaderMaterial({ vertexShader: SHELL_VERT, fragmentShader: DEPTH_FRAG, uniforms: U, colorWrite: false, depthWrite: true, depthTest: true, side: THREE.FrontSide });
  const shellMat = new THREE.ShaderMaterial({ vertexShader: SHELL_VERT, fragmentShader: SHELL_FRAG, uniforms: U, ...add, depthTest: true, depthFunc: THREE.LessEqualDepth, side: THREE.FrontSide });
  const sDepth = new THREE.Mesh(sgeo, depthMat), sLight = new THREE.Mesh(sgeo, shellMat);
  sDepth.frustumCulled = sLight.frustumCulled = false; sDepth.renderOrder = 1; sLight.renderOrder = 2; sDepth.visible = sLight.visible = false;
  const lean = new THREE.Group(); lean.position.y = -2.7; lean.rotation.order = 'YXZ'; scene.add(lean);
  for (const m of [mesh, sDepth, sLight]) { m.position.y = 2.7; lean.add(m); }

  // Motas: a distintas profundidades, para que el giro tenga paralaje.
  const ND = 520, dp = new Float32Array(ND * 3), dr = new Float32Array(ND * 3); let s = 0x9e3779b9;
  const rnd = (): number => { s = (Math.imul(s ^ (s >>> 15), s | 1) + 0x6d2b79f5) >>> 0; return ((s ^ (s >>> 14)) >>> 0) / 4294967296; };
  for (let i = 0; i < ND; i++) { const a = rnd() * 6.2832, r = 1.2 + rnd() * 2.4; dp[i * 3] = Math.cos(a) * r; dp[i * 3 + 1] = -3.3 + rnd() * 5.6; dp[i * 3 + 2] = Math.sin(a) * r * 0.9; dr[i * 3] = rnd(); dr[i * 3 + 1] = 1.5 + rnd() * rnd() * 4.5; dr[i * 3 + 2] = rnd() * 6.28; }
  const dgeo = new THREE.BufferGeometry(); dgeo.setAttribute('position', new THREE.BufferAttribute(dp, 3)); dgeo.setAttribute('aR', new THREE.BufferAttribute(dr, 3));
  const DU = { uInk: U.uInk, uTime: U.uTime, uTw: U.uTw, uBurst: { value: 0 }, uB: { value: 1 }, uCold: { value: 0 }, uScale: { value: 10 } };
  const dust = new THREE.Points(dgeo, new THREE.ShaderMaterial({ vertexShader: DUST_VERT, fragmentShader: DUST_FRAG, uniforms: DU, ...add, depthTest: true })); dust.frustumCulled = false; dust.renderOrder = 4; scene.add(dust);
  const BU = { uRes: U.uRes, uOrigin: { value: new THREE.Vector2() }, uHalo: { value: new THREE.Vector2(0.5, 0.6) }, uGlow: { value: 1 }, uCold: { value: 0 } };
  const bg = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial({ vertexShader: BG_VERT, fragmentShader: BG_FRAG, uniforms: BU, depthTest: false, depthWrite: false })); bg.frustumCulled = false; bg.renderOrder = 0; bg.visible = !transparent; scene.add(bg);

  let ink = false, exposure = 0.4, cw = 1, ch = 1, last: Pose | null = null, touchK = 0, touching = false, ripAge = 9, ripSeen = 0;
  const tmp = new THREE.Vector3(), inv = new THREE.Matrix4(), ro = new THREE.Vector3(), rd = new THREE.Vector3(), hitP = new THREE.Vector3(), ndc = new THREE.Vector2(), ray = new THREE.Raycaster();
  const sstep = (a: number, b: number, x: number): number => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
  /** Punto de reposo → espacio local del busto con el giro de cabeza actual (mismo orden que el shader). */
  const headLocal = (x: number, y: number, z: number, out: THREE.Vector3): THREE.Vector3 => {
    const p = last; let vx = x - PIVOT[0], vy = y - PIVOT[1], vz = z - PIVOT[2];
    if (p) {
      const ca = Math.cos(p.yaw), sa = Math.sin(p.yaw); [vx, vz] = [vx * ca + vz * sa, -vx * sa + vz * ca];
      const cb = Math.cos(p.pitch), sb = Math.sin(p.pitch); [vy, vz] = [vy * cb - vz * sb, vy * sb + vz * cb];
      const cc = Math.cos(p.roll), sc = Math.sin(p.roll); [vx, vy] = [vx * cc - vy * sc, vx * sc + vy * cc];
    }
    return out.set(vx + PIVOT[0], vy + PIVOT[1], vz + PIVOT[2]);
  };
  const toScreen = (v: THREE.Vector3): THREE.Vector3 => { v.applyMatrix4(mesh.matrixWorld).project(cam); v.x = (v.x * 0.5 + 0.5) * cw; v.y = (-v.y * 0.5 + 0.5) * ch; return v; };
  const rayEll = (cx: number, cy: number, cz: number, rx: number, ry: number, rz: number): number => { // rayo local contra un elipsoide
    const ox = (ro.x - cx) / rx, oy = (ro.y - cy) / ry, oz = (ro.z - cz) / rz, dx = rd.x / rx, dy = rd.y / ry, dz = rd.z / rz;
    const a = dx * dx + dy * dy + dz * dz, b = ox * dx + oy * dy + oz * dz, c = ox * ox + oy * oy + oz * oz - 1, h = b * b - a * c;
    return h < 0 ? -1 : (-b - Math.sqrt(h)) / a;
  };
  /** Lanza el rayo del cursor contra el volumen aproximado del busto. Devuelve 'head' | 'body' | null y deja el punto en hitP. */
  const cast = (x: number, y: number): 'head' | 'body' | null => {
    ndc.set((x / cw) * 2 - 1, -(y / ch) * 2 + 1); ray.setFromCamera(ndc, cam); inv.copy(mesh.matrixWorld).invert();
    ro.copy(ray.ray.origin).applyMatrix4(inv); rd.copy(ray.ray.direction).transformDirection(inv);
    const th = rayEll(0, 0.02, 0, 0.84, 1.2, 1.02), tb = Math.max(rayEll(0, -2.65, -0.15, 1.95, 0.95, 0.8), rayEll(0, -1.4, -0.2, 0.5, 0.6, 0.5));
    const t = th > 0 && (tb < 0 || th < tb) ? th : tb; if (t < 0) return null;
    hitP.copy(rd).multiplyScalar(t).add(ro); return t === th ? 'head' : 'body';
  };
  const px = (): number => ch / (2 * cam.position.z * Math.tan((FOV * Math.PI) / 360)); // píxeles por unidad a la profundidad del busto

  return {
    info: { strands: () => weaver?.W.strands ?? 0, weaveMs: () => weaver?.W.ms ?? 0, woven: () => weaver?.W.done ?? false, calls: () => gl.info.render.calls },
    init,
    view(mode) { viewMode = mode; },
    theme(light) {
      U.uInk.value = light ? 1 : 0; ink = light;
      for (const m of [mat, shellMat, dust.material as THREE.ShaderMaterial]) { m.blendSrc = light ? THREE.OneMinusDstAlphaFactor : THREE.OneFactor; m.needsUpdate = true; }
    },
    weave(ms) {
      if (!weaver) return false; const W = weaver.W, S = weaver.S;
      if (W.done && uploaded === W.strands && shellUp) return true;
      weaver.step(ms);
      if (W.strands > uploaded) { // sube solo los filamentos nuevos
        const v0 = uploaded * NP * 2, vn = (W.strands - uploaded) * NP * 2;
        for (const a of attrs) { a.clearUpdateRanges(); a.addUpdateRange(v0 * a.itemSize, vn * a.itemSize); a.needsUpdate = true; }
        uploaded = W.strands; geo.setDrawRange(0, uploaded * (NP - 1) * 6);
      }
      if (S.ready && !shellUp) {
        shellUp = true;
        sgeo.setAttribute('position', new THREE.BufferAttribute(S.pos, 3)); sgeo.setAttribute('aNrm', new THREE.BufferAttribute(S.nrm, 3)); sgeo.setAttribute('aB', new THREE.BufferAttribute(S.b, 4));
        sgeo.setAttribute('aC', new THREE.BufferAttribute(S.c, 4, true)); sgeo.setAttribute('aD', new THREE.BufferAttribute(S.d, 4, true)); sgeo.setIndex(new THREE.BufferAttribute(S.index, 1));
        sDepth.visible = sLight.visible = true;
      }
      return W.done && shellUp;
    },
    /** Compila los shaders sin bloquear (KHR_parallel_shader_compile). */
    compile: () => { const was = [mesh.visible, sDepth.visible, sLight.visible]; mesh.visible = sDepth.visible = sLight.visible = true; return gl.compileAsync(scene, cam).then(() => { [mesh.visible, sDepth.visible, sLight.visible] = was as [boolean, boolean, boolean]; }); },
    dispose() { geo.dispose(); sgeo.dispose(); mat.dispose(); depthMat.dispose(); shellMat.dispose(); dgeo.dispose(); (dust.material as THREE.Material).dispose(); bg.geometry.dispose(); (bg.material as THREE.Material).dispose(); }, // el renderer es de su dueño
    resize(w, h, dpr) {
      cw = w; ch = h; // solo cámara y uniformes: el tamaño del renderer es de su dueño
      const t = Math.tan((FOV * Math.PI) / 360), z = Math.max(3.6 / (2 * t), 3.0 / (w / h) / (2 * t)); // encuadre: cabe la cabeza con el pelo y los hombros
      cam.aspect = w / h; cam.position.set(0, LOOK_Y, z); cam.lookAt(0, LOOK_Y, 0); cam.updateProjectionMatrix();
      U.uRes.value.set(w * dpr, h * dpr); U.uCamZ.value = z; U.uDpr.value = 0.78 + 0.22 * dpr; exposure = 0.4 + 0.2 * (dpr - 1); DU.uScale.value = (h * dpr) / (2 * t) / 62;
    },
    setOrigin(x, y) { BU.uOrigin.value.set(x, y); },
    render(p, dt) {
      last = p;
      U.uTime.value = p.t; U.uTw.value = p.tw; U.uSpin.value = p.spin; U.uBreath.value = p.breath; U.uHPhase.value = p.histPhase;
      U.uBright.value = p.bright * exposure * (ink ? 1.5 : 1); U.uAttract.value = p.attract; U.uStray.value = p.stray; U.uVerge.value = p.verge; U.uSmirk.value = p.smirk; U.uInert.value.set(p.inertX, p.inertY);
      U.uHead.value.set(p.yaw, p.pitch, p.roll); U.uGaze.value.set(p.gx, p.gy, p.lidL, p.lidR); U.uBrow.value.set(p.browL, p.browR, p.furrow, p.squint);
      U.uMouth.value.set(p.jaw, p.round, p.spread, p.smile); U.uForm.value.set(p.cond, p.think, p.loose, p.shed); U.uLight.value.set(p.heat, p.cold, p.glitch, p.sag);
      U.uFx.value.set(p.flow, p.inward, p.flashY, p.flashK); U.uExec.value = p.exec; U.uWarm.value = p.warm; U.uErr.value = p.err; U.uHist.value.set(p.hist);
      U.uOrbG.value = sstep(0.2, 0.6, p.cond); U.uOrbR.value = 1 - 0.14 * p.cold; U.uOrbGain.value = 0.3 + 0.04 * U.uOrbG.value;
      U.uShellK.value = shellUp && viewMode !== 2 ? sstep(0.45, 0.72, p.cond) : 0;
      U.uShell.value = viewMode === 1 ? 3.4 : 2.9; U.uStrands.value = viewMode === 1 ? 0 : 1;
      lean.rotation.set(p.bpitch, p.byaw, 0); lean.updateMatrixWorld(true);
      // Onda del clic: nace donde se tocó (o en la boca, al interrumpirle).
      if (p.ripple !== ripSeen) { ripSeen = p.ripple; ripAge = 0; if (p.rippleZone === 'mouth' || !touching) headLocal(MOUTH[0], MOUTH[1], MOUTH[2], hitP); U.uRip.value.set(hitP.x, hitP.y, hitP.z, 0); }
      ripAge += dt; U.uRip.value.w = Math.min(ripAge, 9);
      touchK += ((touching ? 1 : 0) - touchK) * (1 - Math.exp(-dt * 9)); U.uTouch.value.w = touchK;
      DU.uBurst.value = p.dustBurst; DU.uB.value = p.dustB; DU.uCold.value = p.cold;
      toScreen(headLocal(0, 0.1, 0, tmp)); BU.uHalo.value.set(tmp.x / cw, 1 - tmp.y / ch); BU.uGlow.value = (0.6 + p.heat * 0.9 + p.level * 0.6 + (1 - U.uOrbG.value) * 1.6) * p.bright * (1 - p.cold * 0.8); BU.uCold.value = p.cold;
      gl.render(scene, cam);
    },
    face: () => (last ? toScreen(headLocal(0, 0.05, 0.6, tmp)) : { x: cw / 2, y: ch * 0.36 }),
    touch(x, y) {
      if (x === null || y === undefined) { touching = false; return false; }
      const z = cast(x, y); touching = z !== null; if (touching) U.uTouch.value.set(hitP.x, hitP.y, hitP.z, touchK);
      return touching;
    },
    hit(x, y) {
      const u = px(), near = (lx: number, ly: number, lz: number, r: number, sxk = 1): boolean => { toScreen(headLocal(lx, ly, lz, tmp)); return ((x - tmp.x) / sxk) ** 2 + (y - tmp.y) ** 2 < (r * u) ** 2; };
      const z = cast(x, y);
      if (near(-EYE.x, EYE.y, 0.76, 0.2)) return 'eyeL';
      if (near(EYE.x, EYE.y, 0.76, 0.2)) return 'eyeR';
      if (near(0, -0.24, 1.02, 0.15)) return 'nose';
      if (near(0, YM, 0.9, 0.16, 2)) return 'mouth';
      if (z === 'head') return hitP.y > 0.45 ? 'hair' : 'head';
      return z;
    },
  };
}
