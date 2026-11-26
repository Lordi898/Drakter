// Render de «Holo-Filamento»: un solo lienzo WebGL2 y cuatro llamadas de dibujo (fondo, busto sólido, trama de hebras, polvo).
// El busto sólido escribe profundidad: las hebras de detrás quedan ocultas y el retrato deja de ser fantasmal.
// Toda la animación ocurre en los vertex shaders; la CPU solo actualiza uniformes. Sin postprocesado:
// el brillo es el perfil gaussiano de cada cinta, con núcleo blanco, sumado de forma aditiva.
import * as THREE from 'three';
import type { Pose, Zone } from './brain';
import { HIST } from './brain';
import { createWeaver, NP, MAXS, PIVOT, KNOT, MOUTH, EYE } from './bust';

const f = (n: number): string => n.toFixed(4);
// Rig compartido por la malla y las hebras: mirada, párpados que resbalan sobre el globo, cejas, mandíbula y labios.
const RIG = /* glsl */ `
attribute vec4 aB; attribute vec4 aC; attribute vec4 aD;
uniform float uTime, uBreath, uVerge, uSmirk;
uniform vec3 uHead, uKey; uniform vec4 uGaze, uBrow, uMouth, uLight, uFx, uAcc;
const vec3 PIV = vec3(${PIVOT.map(f).join(',')}); const vec3 HINGE = vec3(0., -0.16, -0.05);
const vec3 EC = vec3(${f(EYE.x)}, ${f(EYE.y)}, ${f(EYE.z)}); const float CLOSE = ${f(EYE.up + EYE.low)}; const float RLID = ${f(EYE.r + EYE.lid)};
vec3 rotHead(vec3 v, float w) {
  float a = uHead.x * w, b = uHead.y * w, c = uHead.z * w;
  float ca = cos(a), sa = sin(a); v = vec3(v.x * ca + v.z * sa, v.y, -v.x * sa + v.z * ca);
  float cb = cos(b), sb = sin(b); v = vec3(v.x, v.y * cb - v.z * sb, v.y * sb + v.z * cb);
  float cc = cos(c), sc = sin(c); return vec3(v.x * cc - v.y * sc, v.x * sc + v.y * cc, v.z);
}
vec3 gazeRot(vec3 l, float sx) {
  float gy = uGaze.x * 0.5 - sx * uVerge * 0.4, gp = uGaze.y * 0.42;
  float ca = cos(gy), sa = sin(gy); l = vec3(l.x * ca + l.z * sa, l.y, -l.x * sa + l.z * ca);
  float cb = cos(gp), sb = sin(gp); return vec3(l.x, l.y * cb - l.z * sb, l.y * sb + l.z * cb);
}
vec3 face(vec3 p, float sx, float lift) {
  float lid = sx < 0. ? uGaze.z : uGaze.w, cl = 1. - lid; vec3 ec = vec3(sx * EC.x, EC.y, EC.z);
  p.y -= aD.z * (cl * CLOSE + uBrow.w * 0.012); p.y += aD.w * (uBrow.w * 0.03 + max(cl, 0.) * 0.012);
  if (aD.z + aD.w > 0.004) { vec3 q = p - ec; float L = length(q); p = ec + q * (max(L, RLID + lift) / L); } // el párpado resbala sobre el globo
  float brow = sx < 0. ? uBrow.x : uBrow.y;
  p.y += aD.x * brow * 0.11 - aD.y * uBrow.z * 0.06; p.x -= sx * aD.y * uBrow.z * 0.04;
  float ja = uMouth.x * 0.25 * aB.y; vec3 q = p - HINGE; float cj = cos(ja), sj = sin(ja);
  p = HINGE + vec3(q.x, q.y * cj - q.z * sj, q.y * sj + q.z * cj);
  float lw = max(max(aC.x, aC.y), aC.z), sm = uMouth.w + sx * uSmirk;
  p.y += aC.x * uMouth.x * 0.02; p.x *= 1. - lw * (uMouth.y * 0.32 - uMouth.z * 0.14); p.z += lw * uMouth.y * 0.06;
  p.y += aC.z * sm * 0.1 + aC.w * max(sm, 0.) * 0.035 + aC.y * (1. - aC.z) * max(sm, 0.) * 0.012; p.x += sx * aC.z * sm * 0.05;
  return p;
}
vec3 settle(vec3 p, float headW) { p = PIV + rotHead(p - PIV, headW); return p + vec3(0., 0.02, 0.022) * uBreath * (1. - headW * 0.6); }
float sweep(float y) { return exp(-pow((y - (mod(uTime * 0.5, 9.) - 3.6)) / 0.14, 2.)); } // barrido holográfico que sube cada ~18 s
`;

const VERT = /* glsl */ `
attribute vec3 aDir; attribute vec3 aNrm; attribute vec4 aA; attribute vec4 aE; attribute vec2 aF;
${RIG}
uniform float uTw, uSpin, uHPhase, uEmber, uGlow, uBright, uAttract, uStray, uCamZ, uDpr, uInk;
uniform vec2 uRes, uInert; uniform vec3 uShut; uniform vec4 uForm, uTouch, uRip;
uniform float uHist[${HIST}];
varying vec3 vCol; varying float vSide, vInk, vA;
const vec3 MOUTH = vec3(${MOUTH.map(f).join(',')});
vec3 n0; float gCond; float gTh;
vec3 xform(vec3 p, float e) {
  float sx = sign(position.x), tt = aA.y, seed = aA.z, loose = aB.z, tip = tt * tt;
  if (aF.x > 0.5 && aF.x < 1.5) { vec3 ec = vec3(sx * EC.x, EC.y, EC.z); p = ec + gazeRot(p - ec, sx); }
  p = face(p, sx, 0.006);
  // Soltura: los cabos ondean, respiran, van con retraso respecto a la cabeza y se orientan al escuchar.
  float lz = loose * tip * uForm.z;
  vec3 wv = vec3(sin(uTw * 1.3 + seed * 40. + p.y * 3.), sin(uTw * 1.1 + seed * 23. + p.x * 3.), sin(uTw * 0.9 + seed * 61. + p.z * 2.));
  p += wv * lz * 0.04 + n0 * lz * 0.035 * (0.5 + 0.5 * sin(uTw * 0.7 + seed * 17.));
  p -= (vec3(p.z, 0., -p.x) * uInert.x + vec3(0., -p.z, p.y) * uInert.y) * loose * tip;
  p += vec3(0., 0.1, 1.) * loose * tip * uAttract * 0.09;
  float isStray = step(fract(seed * 17.31), 0.022) * step(0.5, loose);
  p += (n0 * 0.5 + vec3(0., 0.22, 0.) + wv * 0.16) * tip * uStray * isStray * 0.62;
  p.y -= uLight.w * (0.03 + loose * tip * 0.22 * (0.4 + seed));
  p = settle(p, aB.x);
  // Ovillo: al pensar, hebras de la coronilla se devanan en un ovillo que flota donde él mira; un hilo lo une a la cabeza.
  float th = aE.w * smoothstep(seed * 0.5, seed * 0.5 + 0.5, uForm.y); th = th * th * (3. - 2. * th);
  float hh = fract(seed * 13.3), an = uSpin * (1.2 + 1.6 * fract(seed * 7.)) + (tt - 0.5) * 2.4 + e * 0.07;
  vec3 ax = normalize(vec3(sin(seed * 91.), cos(seed * 57.), sin(seed * 33. + 1.))), bu = normalize(cross(ax, vec3(0.3, 1., 0.2))), bv = cross(ax, bu);
  vec3 ball = vec3(1.04, 1.02 + 0.04 * sin(uTw * 1.1), 0.5) + (bu * cos(an) + bv * sin(an)) * (0.17 + 0.13 * hh);
  float link = step(fract(seed * 3.17), 0.07); // el hilo que sale de la coronilla
  ball = mix(ball, mix(p, vec3(1.04, 1.02, 0.5), tt + e * 0.03) + vec3(0., sin(3.14159 * tt) * (0.1 + 0.05 * sin(uTw * 2. + seed * 9.)), 0.), link);
  p = mix(p, ball, th); gTh = th * (1. - link * 0.5);
  // Condensación: de la constelación al busto, primero el rostro y luego la periferia, describiendo arcos.
  float c = smoothstep(0., 0.3, uForm.x * 1.3 - aA.w);
  c *= 1. - uForm.w * smoothstep(0.93, 0.995, sin(uTime * 0.21 + seed * 50.)) * step(0.16, aA.w);
  float ang = sin(uTime * 0.07 + seed * 6.28) * 0.3, ca = cos(ang), sa = sin(ang);
  vec3 S = vec3(aE.x * ca + aE.z * sa, aE.y + sin(uTime * 0.3 + seed * 30.) * 0.06, -aE.x * sa + aE.z * ca) + aDir * ((tt - 0.5) * 0.055 + e * 0.02);
  vec3 arc = cross(vec3(0., 1., 0.), p - S) * sin(3.14159 * c) * 0.16;
  gCond = c;
  return mix(S, p, c) + arc;
}
vec3 ramp(float h) { // la energía del filamento: azul profundo, azur, cian, núcleo blanco
  vec3 c = mix(vec3(0.02, 0.09, 0.4), vec3(0.05, 0.4, 1.0), smoothstep(-0.05, 0.3, h));
  c = mix(c, vec3(0.3, 0.8, 1.0), smoothstep(0.25, 0.7, h));
  return mix(c, vec3(0.9, 0.97, 1.0), smoothstep(0.75, 1.3, h));
}
void main() {
  n0 = normalize(aNrm);
  float kind = aF.x, tt = aA.y, seed = aA.z;
  vec3 p2 = xform(position + aDir * 0.02, 1.);
  vec3 p1 = xform(position, 0.);
  vec3 N = rotHead(n0, aB.x);
  vec3 dT = p1 - uTouch.xyz; float tk = exp(-dot(dT, dT) * 11.) * uTouch.w; // la mano que pasa
  float dR = length(p1 - uRip.xyz), rk = exp(-pow((dR - uRip.w * 2.4) / 0.14, 2.)) * exp(-uRip.w * 1.7); // onda del clic
  vec3 push = N * (tk * 0.06 * (0.3 + aB.z) + rk * 0.05) * gCond; p1 += push; p2 += push;
  vec4 mv = modelViewMatrix * vec4(p1, 1.);
  vec4 c1 = projectionMatrix * mv, c2 = projectionMatrix * modelViewMatrix * vec4(p2, 1.);
  vec2 d = (c2.xy / c2.w - c1.xy / c1.w) * uRes; float dl = length(d); d = dl > 1e-5 ? d / dl : vec2(1., 0.);
  // Luz: las hebras se iluminan como un sólido (difusa, relleno y contorno); el busto sólido ya tapa lo de detrás.
  vec3 Nv = normalize(normalMatrix * N); float ndv = Nv.z;
  float facing = smoothstep(-0.15, 0.2, ndv), diff = max(dot(Nv, uKey), 0.), rim = pow(1. - abs(ndv), 3.);
  float fill = max(dot(Nv, vec3(0.62, -0.1, 0.78)), 0.);
  float b = (0.12 + 1.05 * diff * diff + 0.2 * fill + 0.55 * rim) * mix(0.12, 1., facing);
  float heat = uLight.x - 0.2 + diff * 0.42 + tk * 0.6 + rk * 0.8;
  // La voz viaja por la trama: sale de la boca al hablar y converge hacia la cabeza al escuchar.
  float a = mix(distance(position, MOUTH), max(0., 2.7 - distance(position, vec3(0., 0.1, 0.))), uFx.y) * 5.5;
  float fi = a + 1. - uHPhase; int i0 = int(clamp(fi, 0., ${HIST - 2}.)); float hv = mix(uHist[i0], uHist[i0 + 1], clamp(fi - float(i0), 0., 1.)) * exp(-a * 0.1);
  heat += hv * 0.5; b *= 1. + hv * 0.6;
  float gl = smoothstep(0.86, 1., sin((tt * 1.6 - uTw * (0.6 + uFx.x * 1.8) + seed * 9.) * 6.2832)); // pulsos de datos por el hilo
  b *= 1. + gl * (0.3 + uFx.x * 2.3); heat += gl * (0.1 + uFx.x * 0.35);
  float fl = exp(-pow((p1.y - uFx.z) / 0.36, 2.)) * uFx.w; heat += fl * 0.8; b *= 1. + fl * 1.7;
  float sw = sweep(p1.y); b *= 1. + sw * 0.7; heat += sw * 0.25;
  b *= 0.955 + 0.045 * sin(uTime * 37. + seed * 90.); // parpadeo leve de holograma
  float glitchy = step(fract(seed * 5.3), 0.4);
  b *= 1. - uLight.z * glitchy * step(0.5, fract(sin(seed * 91.7 + floor(uTime * 13.) * 7.13) * 43758.5)) * 0.93; // hebras fundidas
  b = mix(b, 0.8, gTh); heat = mix(heat, 0.75, gTh);
  // Lanzadera: al ejecutar, una cuenta de luz recorre el pecho de lado a lado y teje fila a fila.
  float row = exp(-pow((position.y - uShut.y) / 0.07, 2.)) * (1. - aB.x), bead = exp(-pow((position.x - uShut.x) / 0.16, 2.));
  float sh = uShut.z * row * (0.5 + 2.6 * bead); b *= 1. + sh * 2.2; heat += sh * 0.5;
  float tw = 0.5 + 0.5 * sin(uTime * (1. + seed * 2.) + seed * 80.);
  b = mix((0.35 + 3.2 * pow(tw, 5.)) * (1. + uLight.y * 1.6), b, gCond); // dispersa, cada hebra es una estrella que titila
  float gain = mix(0.8, aB.w, gCond), open = smoothstep(0.03, 0.4, uMouth.x), accK = uAcc.w * max(max(glitchy, step(0.5, aB.z) * 0.8), clamp(fl + sh, 0., 1.));
  if (kind > 0.5) {
    if (kind < 1.5) { b = 0.75 * facing; heat = mix(1.0, 0.5, tt) * clamp(uLight.x * 1.7 + 0.15, 0.25, 1.15) + hv * 0.3 + aF.y; accK = 0.; }
    else if (kind < 2.5) { b = open * (0.3 + 0.4 * uGlow); heat = 0.25 + 0.3 * uGlow; accK = 0.; } // fondo luminoso de la boca
    else if (kind < 3.5) { b = uEmber * mix(0.3, 1., facing); heat = 0.7 + uEmber * 0.3; accK = uAcc.w; } // el núcleo del nudo
    else if (kind < 5.5) { b = open * 0.3; heat = 0.9; accK = 0.; } // dientes
    else { b = (0.62 + 0.7 * diff + 0.3 * fill + 0.45 * rim) * (1. + hv * 0.6 + fl * 1.7 + sw * 0.7) * mix(1., 0.8, gTh); b = mix((0.35 + 3.2 * pow(tw, 5.)) * (1. + uLight.y * 1.6), b, gCond); } // pelo
  }
  vec3 col = ramp(heat); float lum = dot(col, vec3(0.3, 0.5, 0.2));
  col = mix(col, uAcc.rgb * (0.55 + lum), accK); // acento: ámbar en el error, blanco cálido en el éxito
  col = mix(col, vec3(0.3, 0.38, 0.52) * (0.4 + 0.6 * lum), uLight.y); // sin conexión: apagado
  float depth = 1. + (mv.z + uCamZ) * 0.16;
  float taper = smoothstep(0., 0.2, tt) * smoothstep(1., 0.68, tt);
  vCol = col * b * gain * taper * uBright * clamp(depth, 0.55, 1.3);
  vInk = uInk * max(max(1. - gCond, gTh), step(5.5, kind) * tt * tt * 0.9); vA = clamp(b * gain * taper * 0.9, 0., 1.) * (1. - 0.5 * uLight.y); // sobre fondo claro, lo que flota fuera del busto es tinta
  float wpx = (0.95 + 0.5 * clamp(heat, 0., 1.3) + aF.y + (1. - gCond) * 0.45) * uDpr * clamp(depth, 0.7, 1.25) * (0.55 + 0.45 * taper);
  c1.xy += vec2(-d.y, d.x) * aA.x * wpx * 2. / uRes * c1.w;
  c1.z -= 0.0012 * c1.w; // un pelo por delante de la malla
  gl_Position = c1; vSide = aA.x;
}`;
const FRAG = /* glsl */ `
varying vec3 vCol; varying float vSide, vInk, vA;
void main() {
  float d = vSide * vSide, prof = exp(-d * 4.5) * 0.9 + 0.1 * (1. - d);
  vec3 light = vCol * prof + vec3(dot(vCol, vec3(0.45))) * exp(-d * 18.) * 0.7;
  float ia = clamp(vA * exp(-d * 3.) * 1.5, 0., 1.) * vInk; // tinta cobalto, con mezcla normal
  gl_FragColor = vec4(light * (1. - vInk) + vec3(0.03, 0.17, 0.52) * ia, ia); // la luz se suma (alfa 0); solo la tinta tapa
}`;

// Busto sólido: vidrio holográfico oscuro con contorno de luz, líneas de escaneo y ojos de verdad (esclerótica, iris de fibras, pupila).
const SOLID_VERT = /* glsl */ `
${RIG}
varying vec3 vN, vRest; varying float vFlag, vJaw, vFx;
void main() {
  float sx = sign(position.x); vec3 p = face(position, sx, 0.);
  p.y -= uLight.w * 0.03; p = settle(p, aB.x);
  vec3 N = rotHead(normalize(normal), aB.x); p -= N * 0.004;
  vN = normalMatrix * N; vRest = position; vFlag = aB.z; vJaw = aB.y; vFx = sweep(p.y) * 0.22 + exp(-pow((p.y - uFx.z) / 0.36, 2.)) * uFx.w * 0.5;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.);
}`;
const SOLID_FRAG = /* glsl */ `
uniform float uTime, uVerge, uSolid, uClay, uAlphaK, uInk; uniform vec3 uKey; uniform vec4 uGaze, uMouth, uLight, uFx, uAcc;
varying vec3 vN, vRest; varying float vFlag, vJaw, vFx;
const vec3 EC = vec3(${f(EYE.x)}, ${f(EYE.y)}, ${f(EYE.z)});
void main() {
  vec3 N = normalize(vN);
  float ndv = clamp(N.z, 0., 1.), diff = max(dot(N, uKey), 0.), fill = max(dot(N, vec3(0.62, -0.1, 0.78)), 0.), fres = pow(1. - ndv, 2.4);
  if (uClay > 0.5) { gl_FragColor = vec4(vec3(0.1 + 0.75 * diff + 0.18 * fill) * (vFlag > 0.5 && vFlag < 1.5 ? vec3(1., 0.8, 0.8) : vFlag > 1.5 && vFlag < 2.5 ? vec3(0.75, 0.8, 1.) : vec3(1.)), 1.); return; }
  float energy = 0.5 + 0.95 * uLight.x;
  vec3 col = vec3(0.005, 0.022, 0.062) + vec3(0.04, 0.2, 0.44) * pow(diff, 1.35) + vec3(0.008, 0.045, 0.1) * fill;
  col *= 0.72 + 0.28 * smoothstep(-0.7, 0.5, N.y); // lo que mira hacia abajo recibe menos luz
  float hair = step(1.5, vFlag) * step(vFlag, 2.5), cloth = step(2.5, vFlag);
  col *= 1. - 0.12 * hair - 0.25 * cloth;
  vec3 rimC = mix(vec3(0.2, 0.7, 1.0), uAcc.rgb, uAcc.w * 0.85);
  col += rimC * fres * (0.55 + 0.25 * hair) * (1. - 0.7 * uInk) + vec3(0.012, 0.04, 0.09) * uInk;
  if (vFlag > 0.5 && vFlag < 1.5) { // el ojo: se sombrea en el espacio del globo, siguiendo la mirada
    float sx = sign(vRest.x), gy = uGaze.x * 0.5 - sx * uVerge * 0.4, gp = uGaze.y * 0.42;
    vec3 g = vec3(sin(gy), -cos(gy) * sin(gp), cos(gy) * cos(gp)), n = normalize(vRest - vec3(sx * EC.x, EC.y, EC.z));
    float c = dot(n, g); vec3 u = normalize(cross(g, vec3(0., 1., 0.))), v = cross(g, u); float phi = atan(dot(n, v), dot(n, u));
    float iris = smoothstep(0.852, 0.866, c), pupil = smoothstep(0.962, 0.97, c), limbus = smoothstep(0.852, 0.866, c) * (1. - smoothstep(0.866, 0.89, c));
    float fib = 0.55 + 0.45 * sin(phi * 34. + sin(phi * 6.) * 2.2), rad = smoothstep(0.866, 0.965, c);
    vec3 sclera = vec3(0.15, 0.3, 0.44) * (0.4 + 0.7 * diff + 0.35 * fill);
    vec3 irisC = mix(vec3(0.03, 0.2, 0.55), vec3(0.35, 0.85, 1.0), fib * (0.35 + 0.65 * rad)) * (0.5 + 0.8 * energy);
    irisC = mix(irisC, uAcc.rgb, uAcc.w * 0.45);
    col = mix(sclera, irisC, iris); col *= 1. - 0.55 * limbus; col = mix(col, vec3(0.0, 0.008, 0.025), pupil);
    col += vec3(1.) * smoothstep(0.9905, 0.9935, dot(n, normalize(vec3(-0.25 + g.x * 0.5, 0.3 + g.y * 0.5, 0.92)))) * 0.95; // brillo
    col += vec3(0.6, 0.9, 1.) * smoothstep(0.9965, 0.998, dot(n, normalize(vec3(0.16 + g.x * 0.7, -0.14 + g.y * 0.7, 0.97)))) * 0.5;
    col *= 0.45 + 0.55 * smoothstep(0.86, 0.985, n.z + 0.1 * (1. - abs(n.x * 3.))); // sombra del párpado
  } else col *= energy;
  float open = smoothstep(0.03, 0.4, uMouth.x), inside = smoothstep(0.1, 0.3, vJaw) * smoothstep(0.92, 0.7, vJaw) * open * step(0.55, vRest.z) * step(abs(vRest.x), 0.27) * step(vRest.y, -0.55) * step(-0.75, vRest.y);
  col = mix(col, vec3(0.0, 0.012, 0.04), inside * 0.92); // el interior de la boca
  col *= 0.87 + 0.13 * sin(gl_FragCoord.y * 2.0944); // líneas de escaneo
  col += mix(vec3(0.2, 0.65, 0.95), uAcc.rgb, uAcc.w) * vFx;
  col = mix(col, vec3(dot(col, vec3(0.3, 0.5, 0.2))) * vec3(0.7, 0.8, 1.0) * 0.5, uLight.y);
  float al = uSolid * smoothstep(-3.15, -2.55, vRest.y) * mix(1., smoothstep(0.0, 0.2, ndv), uAlphaK); // silueta suave cuando flota sobre la interfaz
  gl_FragColor = vec4(col * al, al);
}`;

const DUST_VERT = /* glsl */ `
attribute vec3 aR;
uniform float uTime, uTw, uBurst, uB, uCold, uScale, uHeat; uniform vec4 uAcc;
varying vec3 vCol;
void main() {
  float seed = aR.x, ang = uTw * 0.05 * (0.4 + seed) + seed * 6.28, ca = cos(ang), sa = sin(ang);
  vec3 p = vec3(position.x * ca + position.z * sa, position.y + sin(uTw * 0.25 + aR.z) * 0.12 + mod(uTw * 0.05 * (0.3 + seed), 1.) * 0.4, -position.x * sa + position.z * ca);
  p += normalize(position - vec3(0., -1.5, 0.)) * uBurst * (1. - uBurst) * 4. * (0.4 + seed); // atar cabos: ráfaga desde el nudo
  vec4 mv = modelViewMatrix * vec4(p, 1.);
  float tw = 0.5 + 0.5 * sin(uTime * (0.8 + seed * 2.5) + aR.z * 7.);
  gl_PointSize = aR.y * 0.75 * uScale * (0.7 + 0.6 * tw) * (1. + uBurst * 1.5) / -mv.z;
  vec3 col = mix(vec3(0.08, 0.4, 1.0), vec3(0.6, 0.92, 1.0), clamp(uHeat + seed * 0.5, 0., 1.));
  col = mix(col, uAcc.rgb, uAcc.w * 0.6 * step(0.5, seed));
  vCol = mix(col, vec3(0.3, 0.38, 0.5), uCold) * (0.16 + 0.6 * tw * tw) * uB * (1. + uBurst * 2.);
  gl_Position = projectionMatrix * mv;
}`;
const DUST_FRAG = /* glsl */ `
uniform float uInk;
varying vec3 vCol;
void main() { vec2 q = gl_PointCoord - 0.5; float g = exp(-dot(q, q) * 18.), m = max(vCol.r, max(vCol.g, vCol.b)) * g, ia = clamp(m * 0.9, 0., 0.55) * uInk; gl_FragColor = vec4(vCol * g * (1. - uInk) + vec3(0.03, 0.17, 0.52) * ia, ia); }`;

const BG_VERT = /* glsl */ `void main() { gl_Position = vec4(position.xy, 0., 1.); }`;
const BG_FRAG = /* glsl */ `
uniform vec2 uRes, uHalo, uOrg; uniform float uWarm, uCold, uTime; uniform vec4 uAcc;
void main() {
  vec2 uv = (gl_FragCoord.xy - uOrg) / uRes; vec2 q = (uv - uHalo) * vec2(uRes.x / uRes.y, 1.); float r2 = dot(q, q);
  vec3 ink = mix(vec3(0.012, 0.03, 0.07), vec3(0.003, 0.006, 0.018), smoothstep(0.1, 1., length((uv - vec2(0.5, 0.56)) * vec2(1.1, 1.25)) * 1.45));
  vec3 glow = mix(vec3(0.02, 0.13, 0.3), uAcc.rgb * 0.25, uAcc.w * 0.5);
  ink += mix(glow * uWarm, vec3(0.02, 0.03, 0.05), uCold) * (exp(-r2 * 9.) * 0.32 + exp(-r2 * 2.2) * 0.2);
  // El emisor: un haz tenue que nace bajo el busto, con dos anillos de luz en perspectiva.
  vec2 e = (uv - vec2(uHalo.x, 0.035)) * vec2(uRes.x / uRes.y, 1.); float beam = exp(-pow(e.x / (0.16 + uv.y * 0.42), 2.)) * exp(-uv.y * 3.2) * 0.1;
  float rr = length(vec2(e.x, e.y * 5.5)), rings = exp(-pow((rr - 0.33) / 0.006, 2.)) * 0.5 + exp(-pow((rr - 0.25) / 0.004, 2.)) * 0.3 + exp(-pow((rr - 0.4) / 0.004, 2.)) * 0.16 * (0.6 + 0.4 * sin(atan(e.y * 5.5, e.x) * 24. + uTime));
  ink += glow * (beam * 2.2 + rings * 1.6) * uWarm * (1. - uCold * 0.8);
  ink += (fract(52.9829189 * fract(dot(gl_FragCoord.xy, vec2(0.06711056, 0.00583715)))) - 0.5) / 255.; // sin bandas en el degradado
  gl_FragColor = vec4(ink, 1.);
}`;

export interface AvatarRenderer {
  /** `ox`/`oy`: origen del recuadro en px del lienzo (device px, `oy` desde abajo), para el fondo. */
  render(p: Pose, dt: number, ox?: number, oy?: number): void;
  resize(w: number, h: number, dpr: number): void;
  face(): { x: number; y: number };
  hit(x: number, y: number): Zone | null;
  /** Cursor sobre el escenario (px) o null si sale: excita las hebras cercanas. Devuelve si toca el busto. */
  touch(x: number | null, y?: number): boolean;
  info: { strands: () => number; prof: () => Record<string, number>; verts: () => number; weaveMs: () => number; woven: () => boolean; calls: () => number };
  /** Teje durante `ms` como mucho y sube lo nuevo. Devuelve true al terminar. */
  weave(ms: number): boolean;
  compile(): Promise<void>;
  /** Reserva búferes y geometría; se llama en una tarea distinta de la creación del contexto. */
  init(): void;
  /** Superficie sobre la que flota en modo transparente: clara (tinta cobalto fuera del busto) u oscura (todo luz). */
  setSurface(light: boolean): void;
  dispose(): void;
}

/** El renderer es del anfitrión (lienzo propio o Stage): aquí no se crea, no se dimensiona ni se destruye. */
export function createRenderer(gl: THREE.WebGLRenderer, clay = false, transparent = false): AvatarRenderer {
  if (!gl.capabilities.isWebGL2) throw new Error('webgl2-unavailable');
  const scene = new THREE.Scene(), FOV = 26, cam = new THREE.PerspectiveCamera(FOV, 1, 4, 30), LOOK_Y = -0.42;
  // Búferes reservados de antemano (en init(), en una tarea aparte): el tejedor los rellena por tandas y solo se sube a la GPU el tramo nuevo.
  let weaver: ReturnType<typeof createWeaver> | null = null, uploaded = 0, solidReady = false;
  const geo = new THREE.BufferGeometry(), attrs: THREE.BufferAttribute[] = [];
  const init = (): void => {
    if (weaver) return; weaver = createWeaver(); const W = weaver.W;
    const attr = (name: string, arr: Float32Array | Uint8Array, n: number, norm = false): void => { const a = new THREE.BufferAttribute(arr, n, norm); a.setUsage(THREE.DynamicDrawUsage); geo.setAttribute(name, a); attrs.push(a); };
    attr('position', W.pos, 3); attr('aDir', W.dir, 3); attr('aNrm', W.nrm, 3); attr('aA', W.a, 4); attr('aB', W.b, 4); attr('aC', W.c, 4, true); attr('aD', W.d, 4, true); attr('aE', W.e, 4); attr('aF', W.f, 2);
    const index = new Uint32Array(MAXS * (NP - 1) * 6);
    for (let st = 0, o = 0; st < MAXS; st++) for (let i = 0; i < NP - 1; i++) { const v = st * NP * 2 + i * 2; index[o++] = v; index[o++] = v + 1; index[o++] = v + 2; index[o++] = v + 1; index[o++] = v + 3; index[o++] = v + 2; }
    geo.setIndex(new THREE.BufferAttribute(index, 1)); geo.setDrawRange(0, 0); mesh.visible = !clay;
  };
  const v4 = (): { value: THREE.Vector4 } => ({ value: new THREE.Vector4() });
  const U = {
    uTime: { value: 0 }, uTw: { value: 0 }, uSpin: { value: 0 }, uBreath: { value: 0 }, uHPhase: { value: 0 }, uEmber: { value: 0.5 }, uGlow: { value: 0 }, uBright: { value: 1 },
    uAttract: { value: 0 }, uStray: { value: 0 }, uVerge: { value: 0 }, uCamZ: { value: 11 }, uDpr: { value: 1 }, uSmirk: { value: 0 }, uSolid: { value: 0 }, uClay: { value: clay ? 1 : 0 }, uAlphaK: { value: transparent ? 1 : 0 }, uInk: { value: 0 },
    uRes: { value: new THREE.Vector2(1, 1) }, uInert: { value: new THREE.Vector2() },
    uHead: { value: new THREE.Vector3() }, uShut: { value: new THREE.Vector3() }, uKey: { value: new THREE.Vector3(-0.66, 0.46, 0.6).normalize() },
    uGaze: v4(), uBrow: v4(), uMouth: v4(), uForm: v4(), uLight: v4(), uFx: v4(), uTouch: v4(), uAcc: { value: new THREE.Vector4(1, 0.55, 0.15, 0) }, uRip: { value: new THREE.Vector4(0, 0, 0, 9) }, uHist: { value: new Float32Array(HIST) },
  };
  // Mezcla premultiplicada: con alfa 0 es aditiva (luz) y con alfa > 0 es normal (tinta); sirve igual en opaco y en transparente.
  const add = { blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor, depthTest: true, depthWrite: false, transparent: true, side: THREE.DoubleSide } as const;
  const mat = new THREE.ShaderMaterial({ vertexShader: VERT, fragmentShader: FRAG, uniforms: U, ...add });
  const mesh = new THREE.Mesh(geo, mat); mesh.frustumCulled = false; mesh.renderOrder = 2; mesh.visible = false;
  // El busto sólido arranca con una geometría vacía para que su shader se compile junto a los demás.
  const sgeo = new THREE.BufferGeometry(); sgeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(9), 3)); sgeo.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(9), 3));
  sgeo.setAttribute('aB', new THREE.BufferAttribute(new Float32Array(12), 4)); sgeo.setAttribute('aC', new THREE.BufferAttribute(new Uint8Array(12), 4, true)); sgeo.setAttribute('aD', new THREE.BufferAttribute(new Uint8Array(12), 4, true));
  const smat = new THREE.ShaderMaterial({ vertexShader: SOLID_VERT, fragmentShader: SOLID_FRAG, uniforms: U, transparent: true, blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor, depthTest: true, depthWrite: true, side: THREE.FrontSide });
  const solid = new THREE.Mesh(sgeo, smat); solid.frustumCulled = false; solid.renderOrder = 1;
  const lean = new THREE.Group(); lean.position.y = -2.7; mesh.position.y = 2.7; solid.position.y = 2.7; lean.rotation.order = 'YXZ'; lean.add(solid, mesh); scene.add(lean);

  // Polvo: motas a distintas profundidades, para que el giro tenga paralaje.
  const ND = 700, dp = new Float32Array(ND * 3), dr = new Float32Array(ND * 3); let s = 0x9e3779b9;
  const rnd = (): number => { s = (Math.imul(s ^ (s >>> 15), s | 1) + 0x6d2b79f5) >>> 0; return ((s ^ (s >>> 14)) >>> 0) / 4294967296; };
  for (let i = 0; i < ND; i++) { const a = rnd() * 6.2832, r = 1.1 + rnd() * 2.4; dp[i * 3] = Math.cos(a) * r; dp[i * 3 + 1] = -3.3 + rnd() * 5.6; dp[i * 3 + 2] = Math.sin(a) * r * 0.9; dr[i * 3] = rnd(); dr[i * 3 + 1] = 1.5 + rnd() * rnd() * 5; dr[i * 3 + 2] = rnd() * 6.28; }
  const dgeo = new THREE.BufferGeometry(); dgeo.setAttribute('position', new THREE.BufferAttribute(dp, 3)); dgeo.setAttribute('aR', new THREE.BufferAttribute(dr, 3));
  const DU = { uTime: U.uTime, uTw: U.uTw, uAcc: U.uAcc, uInk: U.uInk, uBurst: { value: 0 }, uB: { value: 1 }, uCold: { value: 0 }, uScale: { value: 10 }, uHeat: { value: 0.5 } };
  const dust = new THREE.Points(dgeo, new THREE.ShaderMaterial({ vertexShader: DUST_VERT, fragmentShader: DUST_FRAG, uniforms: DU, ...add })); dust.frustumCulled = false; dust.renderOrder = 3; dust.visible = !clay; scene.add(dust);
  const BU = { uRes: U.uRes, uTime: U.uTime, uAcc: U.uAcc, uHalo: { value: new THREE.Vector2(0.5, 0.6) }, uOrg: { value: new THREE.Vector2() }, uWarm: { value: 1 }, uCold: { value: 0 } };
  const bg = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial({ vertexShader: BG_VERT, fragmentShader: BG_FRAG, uniforms: BU, depthTest: false, depthWrite: false })); bg.frustumCulled = false; bg.renderOrder = 0; bg.visible = !transparent; scene.add(bg);

  let exposure = 0.3, cw = 1, ch = 1, last: Pose | null = null, touchK = 0, touching = false, ripAge = 9, ripSeen = 0;
  const tmp = new THREE.Vector3(), inv = new THREE.Matrix4(), ro = new THREE.Vector3(), rd = new THREE.Vector3(), hitP = new THREE.Vector3(), ndc = new THREE.Vector2(), ray = new THREE.Raycaster(), acc = new THREE.Vector3();
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
    const th = rayEll(0, 0.05, 0, 0.86, 1.25, 1.04), tb = Math.max(rayEll(0, -2.43, -0.15, 1.95, 0.95, 0.8), rayEll(0, -1.3, -0.2, 0.5, 0.5, 0.5));
    const t = th > 0 && (tb < 0 || th < tb) ? th : tb; if (t < 0) return null;
    hitP.copy(rd).multiplyScalar(t).add(ro); return t === th ? 'head' : 'body';
  };
  const px = (): number => ch / (2 * cam.position.z * Math.tan((FOV * Math.PI) / 360)); // píxeles por unidad a la profundidad del busto

  return {
    setSurface(light) { U.uInk.value = light ? 1 : 0; },
    info: { strands: () => weaver?.W.strands ?? 0, prof: () => weaver?.W.prof ?? {}, verts: () => weaver?.W.solid.verts ?? 0, weaveMs: () => weaver?.W.ms ?? 0, woven: () => weaver?.W.done ?? false, calls: () => gl.info.render.calls },
    init,
    weave(ms) {
      if (!weaver) return false; const W = weaver.W;
      if (W.done && uploaded === W.strands && solidReady) return true;
      weaver.step(ms);
      if (W.strands > uploaded) { // sube solo las hebras nuevas
        const v0 = uploaded * NP * 2, vn = (W.strands - uploaded) * NP * 2;
        for (const a of attrs) { a.clearUpdateRanges(); a.addUpdateRange(v0 * a.itemSize, vn * a.itemSize); a.needsUpdate = true; }
        uploaded = W.strands; geo.setDrawRange(0, uploaded * (NP - 1) * 6);
      }
      if (W.done && !solidReady) { // el busto sólido se sube de una vez, ya recortado a su tamaño real (menos de 1 MB)
        const S = W.solid, n = S.verts, g = new THREE.BufferGeometry();
        g.setAttribute('position', new THREE.BufferAttribute(S.pos.subarray(0, n * 3), 3)); g.setAttribute('normal', new THREE.BufferAttribute(S.nrm.subarray(0, n * 3), 3)); g.setAttribute('aB', new THREE.BufferAttribute(S.b.subarray(0, n * 4), 4));
        g.setAttribute('aC', new THREE.BufferAttribute(S.c.subarray(0, n * 4), 4, true)); g.setAttribute('aD', new THREE.BufferAttribute(S.d.subarray(0, n * 4), 4, true)); g.setIndex(new THREE.BufferAttribute(S.index.subarray(0, S.indices), 1));
        solid.geometry.dispose(); solid.geometry = g; solidReady = true;
      }
      return W.done;
    },
    /** Compila los shaders sin bloquear (KHR_parallel_shader_compile). */
    compile: () => gl.compileAsync(scene, cam).then(() => undefined),
    dispose() { geo.dispose(); mat.dispose(); solid.geometry.dispose(); smat.dispose(); dgeo.dispose(); (dust.material as THREE.Material).dispose(); bg.geometry.dispose(); (bg.material as THREE.Material).dispose(); },
    resize(w, h, dpr) {
      cw = w; ch = h;
      const small = 1 - Math.min(1, Math.max(0, (h - 340) / 240)), vh = 4.12 - 0.62 * small; // en lienzos pequeños, plano más cerrado: la cara manda
      const t = Math.tan((FOV * Math.PI) / 360), z = Math.max(vh / (2 * t), (vh * 0.833) / (w / h) / (2 * t));
      cam.aspect = w / h; const ly = LOOK_Y + 0.2 * small; cam.position.set(0, ly, z); cam.lookAt(0, ly, 0); cam.near = z - 3.2; cam.far = z + 4.5; cam.updateProjectionMatrix();
      U.uRes.value.set(w * dpr, h * dpr); U.uCamZ.value = z; const k = Math.min(1.25, Math.max(0.55, (h * dpr) / 600)); U.uDpr.value = (0.78 + 0.22 * dpr) * (0.8 + 0.2 * Math.min(1, k)); exposure = 0.4 * Math.pow(k, 0.75); DU.uScale.value = (h * dpr) / (2 * t) / 62;
    },
    render(p, dt, ox = 0, oy = 0) {
      last = p; BU.uOrg.value.set(ox, oy);
      U.uTime.value = p.t; U.uTw.value = p.tw; U.uSpin.value = p.spin; U.uBreath.value = p.breath; U.uHPhase.value = p.histPhase; U.uEmber.value = p.ember; U.uGlow.value = p.glow;
      U.uBright.value = p.bright * exposure; U.uAttract.value = p.attract; U.uStray.value = p.stray; U.uVerge.value = p.verge; U.uSmirk.value = p.smirk; U.uInert.value.set(p.inertX, p.inertY);
      U.uHead.value.set(p.yaw, p.pitch, p.roll); U.uGaze.value.set(p.gx, p.gy, p.lidL, p.lidR); U.uBrow.value.set(p.browL, p.browR, p.furrow, p.squint);
      U.uMouth.value.set(p.jaw, p.round, p.spread, p.smile); U.uForm.value.set(p.cond, p.think, p.loose, p.shed); U.uLight.value.set(p.heat, p.cold, p.glitch, p.sag);
      U.uFx.value.set(p.flow, p.inward, p.flashY, p.flashK); U.uShut.value.set(p.shutX, p.shutY, p.dustRing); U.uHist.value.set(p.hist);
      // Acento de color: ámbar rojizo en el error, blanco cálido en el éxito. El resto del tiempo, todo azul.
      const warm = p.accent < 0; acc.set(warm ? 1 : 1, warm ? 0.9 : 0.42, warm ? 0.72 : 0.1); U.uAcc.value.set(acc.x, acc.y, acc.z, Math.min(1, Math.abs(p.accent)));
      U.uSolid.value = clay ? 1 : solidReady ? Math.min(1, Math.max(0, (p.cond - 0.3) / 0.38)) : 0; solid.visible = U.uSolid.value > 0.01;
      lean.rotation.set(p.bpitch, p.byaw, 0); lean.updateMatrixWorld(true);
      // Onda del clic: nace donde se tocó (o en la boca, al interrumpirle).
      if (p.ripple !== ripSeen) { ripSeen = p.ripple; ripAge = 0; if (p.rippleZone === 'mouth' || !touching) headLocal(MOUTH[0], MOUTH[1], MOUTH[2], hitP); U.uRip.value.set(hitP.x, hitP.y, hitP.z, 0); }
      ripAge += dt; U.uRip.value.w = Math.min(ripAge, 9);
      touchK += ((touching ? 1 : 0) - touchK) * (1 - Math.exp(-dt * 9)); U.uTouch.value.w = touchK;
      DU.uBurst.value = p.dustBurst; DU.uB.value = p.dustB; DU.uCold.value = p.cold; DU.uHeat.value = p.heat;
      toScreen(headLocal(0, 0.1, 0, tmp)); BU.uHalo.value.set(tmp.x / cw, 1 - tmp.y / ch); BU.uWarm.value = (0.35 + p.heat * 0.9 + p.level * 0.5) * p.bright * (1 - p.cold); BU.uCold.value = p.cold;
      gl.clearDepth(); // solo dentro del recuadro (scissor del anfitrión)
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
      if (near(-EYE.x, EYE.y, 0.86, 0.2)) return 'eyeL';
      if (near(EYE.x, EYE.y, 0.86, 0.2)) return 'eyeR';
      if (near(0, -0.22, 1.04, 0.15)) return 'nose';
      if (near(0, -0.56, 0.9, 0.17, 2)) return 'mouth';
      toScreen(tmp.set(KNOT[0], KNOT[1], KNOT[2])); if ((x - tmp.x) ** 2 + (y - tmp.y) ** 2 < (0.24 * u) ** 2) return 'knot';
      if (z === 'head') return hitP.y > 0.42 ? 'hair' : 'head';
      return z;
    },
  };
}
