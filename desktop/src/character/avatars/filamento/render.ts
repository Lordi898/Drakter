// Render de «Filamento»: un solo lienzo WebGL2 y tres llamadas de dibujo (fondo, trama de hebras, polvo).
// Toda la animación ocurre en el vertex shader; la CPU solo actualiza uniformes. Sin postprocesado:
// el brillo es el perfil gaussiano de cada cinta, sumado de forma aditiva.
import * as THREE from 'three';
import type { Pose, Zone } from './brain';
import { HIST } from './brain';
import { createWeaver, NP, MAXS, PIVOT, KNOT, MOUTH, EYE } from './bust';

const VERT = /* glsl */ `
attribute vec3 aDir; attribute vec3 aNrm; attribute vec4 aA; attribute vec4 aB; attribute vec4 aC; attribute vec4 aD; attribute vec4 aE; attribute vec2 aF;
uniform float uTime, uTw, uSpin, uBreath, uHPhase, uEmber, uGlow, uBright, uAttract, uStray, uVerge, uCamZ, uDpr, uSmirk;
uniform vec2 uRes, uInert; uniform vec3 uHead, uKey; uniform vec4 uGaze, uBrow, uMouth, uForm, uLight, uFx, uTouch, uRip;
uniform vec3 uShut;
uniform float uHist[${HIST}];
varying vec3 vCol; varying float vSide;
const vec3 PIV = vec3(${PIVOT.join(',')}); const vec3 HINGE = vec3(0., -0.16, -0.05); const vec3 MOUTH = vec3(${MOUTH.join(',')});
vec3 n0; float gEye; float gCond; float gTh;

vec3 rotHead(vec3 v, float w) {
  float a = uHead.x * w, b = uHead.y * w, c = uHead.z * w;
  float ca = cos(a), sa = sin(a); v = vec3(v.x * ca + v.z * sa, v.y, -v.x * sa + v.z * ca);
  float cb = cos(b), sb = sin(b); v = vec3(v.x, v.y * cb - v.z * sb, v.y * sb + v.z * cb);
  float cc = cos(c), sc = sin(c); return vec3(v.x * cc - v.y * sc, v.x * sc + v.y * cc, v.z);
}
// Rig facial: mirada, párpados, cejas, mandíbula y labios, con los pesos calculados al tejer.
vec3 face(vec3 p, float sx) {
  float lid = sx < 0. ? uGaze.z : uGaze.w, cl = 1. - lid;
  if (aF.x > 0.5 && aF.x < 1.5) {
    vec3 ec = vec3(sx * ${EYE.x}, ${EYE.y}, ${EYE.z}); vec3 l = p - ec;
    float gy = uGaze.x * 0.5 - sx * uVerge * 0.4, gp = uGaze.y * 0.42;
    float ca = cos(gy), sa = sin(gy); l = vec3(l.x * ca + l.z * sa, l.y, -l.x * sa + l.z * ca);
    float cb = cos(gp), sb = sin(gp); l = vec3(l.x, l.y * cb - l.z * sb, l.y * sb + l.z * cb);
    p = ec + l;
    float s = sqrt(max(1. - pow((p.x - ec.x) / ${EYE.halfW}, 2.), 0.));
    float yU = ec.y + (${EYE.up} - ${(EYE.up + EYE.low).toFixed(3)} * cl) * s - uBrow.w * 0.01, yL = ec.y - (${EYE.low} - uBrow.w * 0.028) * s;
    gEye = smoothstep(yU + 0.004, yU - 0.014, p.y) * smoothstep(yL - 0.004, yL + 0.014, p.y);
  }
  p.y -= aD.z * (cl * ${(EYE.up + EYE.low).toFixed(3)} + uBrow.w * 0.01); p.y += aD.w * uBrow.w * 0.028;
  float brow = sx < 0. ? uBrow.x : uBrow.y;
  p.y += aD.x * brow * 0.11 - aD.y * uBrow.z * 0.06; p.x -= sx * aD.y * uBrow.z * 0.04;
  float ja = uMouth.x * 0.25 * aB.y; vec3 q = p - HINGE; float cj = cos(ja), sj = sin(ja);
  p = HINGE + vec3(q.x, q.y * cj - q.z * sj, q.y * sj + q.z * cj);
  float lw = max(max(aC.x, aC.y), aC.z);
  p.y += aC.x * uMouth.x * 0.02; p.x *= 1. - lw * (uMouth.y * 0.32 - uMouth.z * 0.14); p.z += lw * uMouth.y * 0.06;
  float sm = uMouth.w + sx * uSmirk;
  p.y += aC.z * sm * 0.1 + aC.w * max(sm, 0.) * 0.035 + aC.y * (1. - aC.z) * max(sm, 0.) * 0.012; p.x += sx * aC.z * sm * 0.05;
  return p;
}
vec3 xform(vec3 p, float e) {
  float sx = sign(position.x), tt = aA.y, seed = aA.z, loose = aB.z, tip = tt * tt;
  p = face(p, sx);
  // Soltura: los cabos ondean, respiran, van con retraso respecto a la cabeza y se orientan al escuchar.
  float lz = loose * tip * uForm.z;
  vec3 wv = vec3(sin(uTw * 1.3 + seed * 40. + p.y * 3.), sin(uTw * 1.1 + seed * 23. + p.x * 3.), sin(uTw * 0.9 + seed * 61. + p.z * 2.));
  p += wv * lz * 0.045 + n0 * lz * 0.035 * (0.5 + 0.5 * sin(uTw * 0.7 + seed * 17.));
  p -= (vec3(p.z, 0., -p.x) * uInert.x + vec3(0., -p.z, p.y) * uInert.y) * loose * tip;
  p += vec3(0., 0.1, 1.) * loose * tip * uAttract * 0.09;
  float isStray = step(fract(seed * 17.31), 0.022) * step(0.5, loose);
  p += (n0 * 0.5 + vec3(0., 0.22, 0.) + wv * 0.16) * tip * uStray * isStray * 0.62;
  p.y -= uLight.w * (0.03 + loose * tip * 0.22 * (0.4 + seed));
  p = PIV + rotHead(p - PIV, aB.x);
  p += vec3(0., 0.02, 0.022) * uBreath * (1. - aB.x * 0.6);
  // Ovillo: al pensar, hebras de la coronilla se devanan en un ovillo que flota donde él mira; un hilo lo une a la cabeza.
  float th = aE.w * smoothstep(seed * 0.5, seed * 0.5 + 0.5, uForm.y); th = th * th * (3. - 2. * th);
  float hh = fract(seed * 13.3), an = uSpin * (1.2 + 1.6 * fract(seed * 7.)) + (tt - 0.5) * 2.4 + e * 0.07;
  vec3 ax = normalize(vec3(sin(seed * 91.), cos(seed * 57.), sin(seed * 33. + 1.))), bu = normalize(cross(ax, vec3(0.3, 1., 0.2))), bv = cross(ax, bu);
  vec3 ball = vec3(1.02, 1.0 + 0.04 * sin(uTw * 1.1), 0.5) + (bu * cos(an) + bv * sin(an)) * (0.17 + 0.13 * hh);
  float link = step(fract(seed * 3.17), 0.07); // el hilo que sale de la coronilla
  ball = mix(ball, mix(p, vec3(1.02, 1.0, 0.5), tt + e * 0.03) + vec3(0., sin(3.14159 * tt) * (0.1 + 0.05 * sin(uTw * 2. + seed * 9.)), 0.), link);
  p = mix(p, ball, th); gTh = th * (1. - link * 0.5);
  // Condensación: de la constelación al busto, primero el rostro y luego la periferia, describiendo arcos.
  float c = smoothstep(0., 0.3, uForm.x * 1.3 - aA.w);
  c *= 1. - uForm.w * smoothstep(0.9, 0.99, sin(uTime * 0.21 + seed * 50.)) * step(0.16, aA.w);
  float ang = sin(uTime * 0.07 + seed * 6.28) * 0.3, ca = cos(ang), sa = sin(ang);
  vec3 S = vec3(aE.x * ca + aE.z * sa, aE.y + sin(uTime * 0.3 + seed * 30.) * 0.06, -aE.x * sa + aE.z * ca) + aDir * ((tt - 0.5) * 0.055 + e * 0.02);
  vec3 arc = cross(vec3(0., 1., 0.), p - S) * sin(3.14159 * c) * 0.16;
  gCond = c;
  return mix(S, p, c) + arc;
}
vec3 ramp(float h) { // temperatura del filamento: brasa, ámbar, oro, blanco cálido
  vec3 c = mix(vec3(0.50, 0.075, 0.015), vec3(1.0, 0.40, 0.06), smoothstep(-0.05, 0.3, h));
  c = mix(c, vec3(1.0, 0.70, 0.27), smoothstep(0.25, 0.7, h));
  return mix(c, vec3(1.0, 0.94, 0.80), smoothstep(0.75, 1.3, h));
}
void main() {
  n0 = normalize(aNrm); gEye = 1.;
  float kind = aF.x, tt = aA.y, seed = aA.z;
  vec3 p2 = xform(position + aDir * 0.02, 1.);
  vec3 p1 = xform(position, 0.);
  vec3 N = rotHead(n0, aB.x);
  vec3 dT = p1 - uTouch.xyz; float tk = exp(-dot(dT, dT) * 11.) * uTouch.w; // la mano que pasa
  float dR = length(p1 - uRip.xyz), rk = exp(-pow((dR - uRip.w * 2.4) / 0.14, 2.)) * exp(-uRip.w * 1.7); // onda del clic
  vec3 push = N * (tk * 0.07 * (0.3 + aB.z) + rk * 0.06) * gCond; p1 += push; p2 += push;
  vec4 mv = modelViewMatrix * vec4(p1, 1.);
  vec4 c1 = projectionMatrix * mv, c2 = projectionMatrix * modelViewMatrix * vec4(p2, 1.);
  vec2 d = (c2.xy / c2.w - c1.xy / c1.w) * uRes; float dl = length(d); d = dl > 1e-5 ? d / dl : vec2(1., 0.);
  // Luz: las hebras se iluminan como un sólido (difusa + contorno) y la cara oculta se atenúa.
  vec3 Nv = normalize(normalMatrix * N); float ndv = Nv.z;
  float facing = smoothstep(-0.3, 0.3, ndv), diff = max(dot(Nv, uKey), 0.), rim = pow(1. - abs(ndv), 3.);
  float fill = max(dot(Nv, vec3(0.62, -0.1, 0.78)), 0.);
  float b = (0.33 + 0.72 * diff * diff + 0.36 * fill + 0.4 * rim) * mix(0.05, 1., facing);
  float heat = uLight.x - 0.2 + diff * 0.42 + tk * 0.6 + rk * 0.8;
  // La voz viaja por la trama: sale de la boca al hablar y converge hacia la cabeza al escuchar.
  float a = mix(distance(position, MOUTH), max(0., 2.7 - distance(position, vec3(0., 0.1, 0.))), uFx.y) * 5.5;
  float f = a + 1. - uHPhase; int i0 = int(clamp(f, 0., ${HIST - 2}.)); float hv = mix(uHist[i0], uHist[i0 + 1], clamp(f - float(i0), 0., 1.)) * exp(-a * 0.1);
  heat += hv * 0.5; b *= 1. + hv * 0.6;
  float gl = smoothstep(0.86, 1., sin((tt * 1.6 - uTw * (0.6 + uFx.x * 1.8) + seed * 9.) * 6.2832)); // pulsos del telar
  b *= 1. + gl * (0.25 + uFx.x * 2.3); heat += gl * uFx.x * 0.35;
  float fl = exp(-pow((p1.y - uFx.z) / 0.36, 2.)) * uFx.w; heat += fl * 0.8; b *= 1. + fl * 1.7;
  b *= 1. - uLight.z * step(fract(seed * 5.3), 0.4) * step(0.5, fract(sin(seed * 91.7 + floor(uTime * 13.) * 7.13) * 43758.5)) * 0.93; // hebras fundidas
  b = mix(b, 0.75, gTh); heat = mix(heat, 0.72, gTh);
  // Lanzadera: al ejecutar, una cuenta de luz recorre el pecho de lado a lado y teje fila a fila.
  float row = exp(-pow((position.y - uShut.y) / 0.07, 2.)) * (1. - aB.x), bead = exp(-pow((position.x - uShut.x) / 0.16, 2.));
  float sh = uShut.z * row * (0.5 + 2.6 * bead); b *= 1. + sh * 2.2; heat += sh * 0.5;
  float tw = 0.5 + 0.5 * sin(uTime * (1. + seed * 2.) + seed * 80.);
  b = mix(0.35 + 3.2 * pow(tw, 5.), b, gCond); // dispersa, cada hebra es una estrella que titila
  float gain = mix(0.8, aB.w, gCond);
  float open = smoothstep(0.03, 0.4, uMouth.x);
  if (kind > 0.5) {
    if (kind < 1.5) { b = 0.95 * gEye * facing; heat = mix(1.0, 0.3, tt) * clamp(uLight.x * 1.7 + 0.15, 0.25, 1.15) + hv * 0.3 + aF.y; }
    else if (kind < 2.5) { b = open * (0.5 + 0.45 * uGlow) * facing; heat = 0.12 + 0.25 * uGlow; } // fondo cálido de la boca
    else if (kind < 3.5) { b = uEmber * mix(0.25, 1., facing); heat = 0.16 + uEmber * 0.3; }
    else if (kind < 4.5) { b = b * 1.05 + 0.04 * facing; heat = heat * 0.8 - 0.02; } // labios: más rojizos que la piel
    else { b = open * 0.5 * facing; heat = 0.9; } // dientes
  }
  vec3 col = ramp(heat);
  if (kind < 2.5 || kind > 3.5) col = mix(col, vec3(0.36, 0.47, 0.72) * (0.55 + 0.45 * dot(col, vec3(0.33))), uLight.y);
  float depth = 1. + (mv.z + uCamZ) * 0.16;
  float taper = smoothstep(0., 0.2, tt) * smoothstep(1., 0.68, tt);
  vCol = col * b * gain * taper * uBright * clamp(depth, 0.55, 1.3);
  float wpx = (0.95 + 0.5 * clamp(heat, 0., 1.3) + aF.y + (1. - gCond) * 0.45) * uDpr * clamp(depth, 0.7, 1.25) * (0.55 + 0.45 * taper);
  c1.xy += vec2(-d.y, d.x) * aA.x * wpx * 2. / uRes * c1.w;
  gl_Position = c1; vSide = aA.x;
}`;
const FRAG = /* glsl */ `
varying vec3 vCol; varying float vSide;
void main() { float d = vSide * vSide; gl_FragColor = vec4(vCol * (exp(-d * 4.5) * 0.9 + 0.1 * (1. - d)), 0.); }`;

const DUST_VERT = /* glsl */ `
attribute vec3 aR;
uniform float uTime, uTw, uBurst, uB, uCold, uScale, uHeat;
varying vec3 vCol;
void main() {
  float seed = aR.x, ang = uTw * 0.05 * (0.4 + seed) + seed * 6.28, ca = cos(ang), sa = sin(ang);
  vec3 p = vec3(position.x * ca + position.z * sa, position.y + sin(uTw * 0.25 + aR.z) * 0.12, -position.x * sa + position.z * ca);
  p += normalize(position - vec3(0., -1.7, 0.)) * uBurst * (1. - uBurst) * 4. * (0.4 + seed); // atar cabos: ráfaga desde el nudo
  vec4 mv = modelViewMatrix * vec4(p, 1.);
  float tw = 0.5 + 0.5 * sin(uTime * (0.8 + seed * 2.5) + aR.z * 7.);
  gl_PointSize = aR.y * 0.8 * uScale * (0.7 + 0.6 * tw) * (1. + uBurst * 1.5) / -mv.z;
  vec3 col = mix(vec3(1.0, 0.5, 0.12), vec3(1.0, 0.86, 0.55), clamp(uHeat + seed * 0.5, 0., 1.));
  vCol = mix(col, vec3(0.4, 0.5, 0.75), uCold) * (0.18 + 0.6 * tw * tw) * uB * (1. + uBurst * 2.);
  gl_Position = projectionMatrix * mv;
}`;
const DUST_FRAG = /* glsl */ `
varying vec3 vCol;
void main() { vec2 q = gl_PointCoord - 0.5; gl_FragColor = vec4(vCol * exp(-dot(q, q) * 18.), 0.); }`;

const BG_VERT = /* glsl */ `void main() { gl_Position = vec4(position.xy, 0., 1.); }`;
const BG_FRAG = /* glsl */ `
uniform vec2 uRes, uHalo, uOrg; uniform float uWarm, uCold, uCard;
void main() {
  vec2 uv = (gl_FragCoord.xy - uOrg) / uRes; vec2 q = (uv - uHalo) * vec2(uRes.x / uRes.y, 1.); float r2 = dot(q, q);
  vec3 ink = mix(vec3(0.036, 0.04, 0.085), vec3(0.008, 0.008, 0.022), smoothstep(0.1, 1., length((uv - vec2(0.5, 0.56)) * vec2(1.1, 1.25)) * 1.45));
  ink += mix(vec3(0.20, 0.075, 0.02) * uWarm, vec3(0.03, 0.045, 0.09), uCold) * (exp(-r2 * 9.) * 0.3 + exp(-r2 * 2.2) * 0.16);
  ink += (fract(52.9829189 * fract(dot(gl_FragCoord.xy, vec2(0.06711056, 0.00583715)))) - 0.5) / 255.; // sin bandas en el degradado
  // Tarjeta (tema claro): el mismo fondo oscuro con esquinas redondeadas y borde suave; con uCard = 0 llena el recuadro.
  vec2 hs = uRes * 0.5, r = vec2(min(uRes.x, uRes.y) * 0.06); vec2 qd = abs((uv - 0.5) * uRes) - hs + r;
  float a = uCard > 0.5 ? 1. - smoothstep(-1., 1., length(max(qd, 0.)) + min(max(qd.x, qd.y), 0.) - r.x) : 1.;
  gl_FragColor = vec4(ink * a, a);
}`;

export interface AvatarRenderer {
  /** `ox`/`oy`: origen del recuadro en px del lienzo (device px, `oy` desde abajo), para el fondo. */
  render(p: Pose, dt: number, ox?: number, oy?: number): void;
  resize(w: number, h: number, dpr: number): void;
  face(): { x: number; y: number };
  hit(x: number, y: number): Zone | null;
  /** Cursor sobre el escenario (px) o null si sale: excita las hebras cercanas. Devuelve si toca el busto. */
  touch(x: number | null, y?: number): boolean;
  info: { strands: () => number; weaveMs: () => number; woven: () => boolean; calls: () => number };
  /** Teje durante `ms` como mucho y sube lo nuevo. Devuelve true al terminar. */
  weave(ms: number): boolean;
  compile(): Promise<void>;
  /** Reserva búferes y geometría; se llama en una tarea distinta de la creación del contexto. */
  init(): void;
  /** Con `transparent`: tema claro = el fondo oscuro pasa a tarjeta de esquinas redondeadas (la luz aditiva no se ve sobre claro); oscuro = flota sin fondo. */
  setTheme(light: boolean): void;
  dispose(): void;
}

/** El renderer es del anfitrión (lienzo propio o Stage): aquí no se crea, no se dimensiona ni se destruye. */
export function createRenderer(gl: THREE.WebGLRenderer, transparent = false): AvatarRenderer {
  if (!gl.capabilities.isWebGL2) throw new Error('webgl2-unavailable');
  const scene = new THREE.Scene(), FOV = 26, cam = new THREE.PerspectiveCamera(FOV, 1, 4, 30), LOOK_Y = -0.44;
  // Búferes reservados de antemano (en init(), en una tarea aparte): el tejedor los rellena por tandas y solo se sube a la GPU el tramo nuevo.
  let weaver: ReturnType<typeof createWeaver> | null = null, uploaded = 0;
  const geo = new THREE.BufferGeometry(), attrs: THREE.BufferAttribute[] = [];
  const init = (): void => {
    if (weaver) return; weaver = createWeaver(); const W = weaver.W;
    const attr = (name: string, arr: Float32Array | Uint8Array, n: number, norm = false): void => { const a = new THREE.BufferAttribute(arr, n, norm); a.setUsage(THREE.DynamicDrawUsage); geo.setAttribute(name, a); attrs.push(a); };
    attr('position', W.pos, 3); attr('aDir', W.dir, 3); attr('aNrm', W.nrm, 3); attr('aA', W.a, 4); attr('aB', W.b, 4); attr('aC', W.c, 4, true); attr('aD', W.d, 4, true); attr('aE', W.e, 4); attr('aF', W.f, 2);
    const index = new Uint32Array(MAXS * (NP - 1) * 6);
    for (let st = 0, o = 0; st < MAXS; st++) for (let i = 0; i < NP - 1; i++) { const v = st * NP * 2 + i * 2; index[o++] = v; index[o++] = v + 1; index[o++] = v + 2; index[o++] = v + 1; index[o++] = v + 3; index[o++] = v + 2; }
    geo.setIndex(new THREE.BufferAttribute(index, 1)); geo.setDrawRange(0, 0); mesh.visible = true;
  };
  const v4 = (): { value: THREE.Vector4 } => ({ value: new THREE.Vector4() });
  const U = {
    uTime: { value: 0 }, uTw: { value: 0 }, uSpin: { value: 0 }, uBreath: { value: 0 }, uHPhase: { value: 0 }, uEmber: { value: 0.5 }, uGlow: { value: 0 }, uBright: { value: 1 },
    uAttract: { value: 0 }, uStray: { value: 0 }, uVerge: { value: 0 }, uCamZ: { value: 11 }, uDpr: { value: 1 }, uSmirk: { value: 0 }, uRes: { value: new THREE.Vector2(1, 1) }, uInert: { value: new THREE.Vector2() },
    uHead: { value: new THREE.Vector3() }, uShut: { value: new THREE.Vector3() }, uKey: { value: new THREE.Vector3(-0.42, 0.5, 0.76).normalize() },
    uGaze: v4(), uBrow: v4(), uMouth: v4(), uForm: v4(), uLight: v4(), uFx: v4(), uTouch: v4(), uRip: { value: new THREE.Vector4(0, 0, 0, 9) }, uHist: { value: new Float32Array(HIST) },
  };
  const add = { blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor, depthTest: false, depthWrite: false, transparent: true, side: THREE.DoubleSide } as const;
  const mat = new THREE.ShaderMaterial({ vertexShader: VERT, fragmentShader: FRAG, uniforms: U, ...add });
  const mesh = new THREE.Mesh(geo, mat); mesh.frustumCulled = false; mesh.renderOrder = 1; mesh.visible = false;
  const lean = new THREE.Group(); lean.position.y = -2.7; mesh.position.y = 2.7; lean.rotation.order = 'YXZ'; lean.add(mesh); scene.add(lean);

  // Polvo: motas a distintas profundidades, para que el giro tenga paralaje.
  const ND = 900, dp = new Float32Array(ND * 3), dr = new Float32Array(ND * 3); let s = 0x9e3779b9;
  const rnd = (): number => { s = (Math.imul(s ^ (s >>> 15), s | 1) + 0x6d2b79f5) >>> 0; return ((s ^ (s >>> 14)) >>> 0) / 4294967296; };
  for (let i = 0; i < ND; i++) { const a = rnd() * 6.2832, r = 1.1 + rnd() * 2.4; dp[i * 3] = Math.cos(a) * r; dp[i * 3 + 1] = -3.3 + rnd() * 5.6; dp[i * 3 + 2] = Math.sin(a) * r * 0.9; dr[i * 3] = rnd(); dr[i * 3 + 1] = 1.5 + rnd() * rnd() * 5; dr[i * 3 + 2] = rnd() * 6.28; }
  const dgeo = new THREE.BufferGeometry(); dgeo.setAttribute('position', new THREE.BufferAttribute(dp, 3)); dgeo.setAttribute('aR', new THREE.BufferAttribute(dr, 3));
  const DU = { uTime: U.uTime, uTw: U.uTw, uBurst: { value: 0 }, uB: { value: 1 }, uCold: { value: 0 }, uScale: { value: 10 }, uHeat: { value: 0.5 } };
  const dust = new THREE.Points(dgeo, new THREE.ShaderMaterial({ vertexShader: DUST_VERT, fragmentShader: DUST_FRAG, uniforms: DU, ...add })); dust.frustumCulled = false; dust.renderOrder = 2; scene.add(dust);
  const BU = { uRes: U.uRes, uHalo: { value: new THREE.Vector2(0.5, 0.6) }, uOrg: { value: new THREE.Vector2() }, uWarm: { value: 1 }, uCold: { value: 0 }, uCard: { value: 0 } };
  const bg = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial({ vertexShader: BG_VERT, fragmentShader: BG_FRAG, uniforms: BU, depthTest: false, depthWrite: false, transparent: true, blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor }));
  bg.visible = !transparent; bg.frustumCulled = false; bg.renderOrder = 0; scene.add(bg);

  let exposure = 0.3, cw = 1, ch = 1, last: Pose | null = null, touchK = 0, touching = false, ripAge = 9, ripSeen = 0;
  const tmp = new THREE.Vector3(), inv = new THREE.Matrix4(), ro = new THREE.Vector3(), rd = new THREE.Vector3(), hitP = new THREE.Vector3(), ndc = new THREE.Vector2(), ray = new THREE.Raycaster();
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
    setTheme(light) { bg.visible = !transparent || light; BU.uCard.value = transparent && light ? 1 : 0; },
    info: { strands: () => weaver?.W.strands ?? 0, weaveMs: () => weaver?.W.ms ?? 0, woven: () => weaver?.W.done ?? false, calls: () => gl.info.render.calls },
    init,
    weave(ms) {
      if (!weaver) return false; const W = weaver.W;
      if (W.done && uploaded === W.strands) return true;
      weaver.step(ms);
      if (W.strands > uploaded) { // sube solo las hebras nuevas
        const v0 = uploaded * NP * 2, vn = (W.strands - uploaded) * NP * 2;
        for (const a of attrs) { a.clearUpdateRanges(); a.addUpdateRange(v0 * a.itemSize, vn * a.itemSize); a.needsUpdate = true; }
        uploaded = W.strands; geo.setDrawRange(0, uploaded * (NP - 1) * 6);
      }
      return W.done;
    },
    /** Compila los shaders sin bloquear (KHR_parallel_shader_compile). */
    compile: () => gl.compileAsync(scene, cam).then(() => undefined),
    dispose() { geo.dispose(); mat.dispose(); dgeo.dispose(); (dust.material as THREE.Material).dispose(); bg.geometry.dispose(); (bg.material as THREE.Material).dispose(); },
    resize(w, h, dpr) {
      cw = w; ch = h;
      const t = Math.tan((FOV * Math.PI) / 360), z = Math.max(4.12 / (2 * t), 3.43 / (w / h) / (2 * t)); // encuadre: cabe la cabeza con el pelo y los hombros
      cam.aspect = w / h; cam.position.set(0, LOOK_Y, z); cam.lookAt(0, LOOK_Y, 0); cam.updateProjectionMatrix();
      U.uRes.value.set(w * dpr, h * dpr); U.uCamZ.value = z; U.uDpr.value = 0.78 + 0.22 * dpr; exposure = 0.4 + 0.2 * (dpr - 1); DU.uScale.value = (h * dpr) / (2 * t) / 62;
    },
    render(p, dt, ox = 0, oy = 0) {
      last = p; BU.uOrg.value.set(ox, oy);
      U.uTime.value = p.t; U.uTw.value = p.tw; U.uSpin.value = p.spin; U.uBreath.value = p.breath; U.uHPhase.value = p.histPhase; U.uEmber.value = p.ember; U.uGlow.value = p.glow;
      U.uBright.value = p.bright * exposure; U.uAttract.value = p.attract; U.uStray.value = p.stray; U.uVerge.value = p.verge; U.uSmirk.value = p.smirk; U.uInert.value.set(p.inertX, p.inertY);
      U.uHead.value.set(p.yaw, p.pitch, p.roll); U.uGaze.value.set(p.gx, p.gy, p.lidL, p.lidR); U.uBrow.value.set(p.browL, p.browR, p.furrow, p.squint);
      U.uMouth.value.set(p.jaw, p.round, p.spread, p.smile); U.uForm.value.set(p.cond, p.think, p.loose, p.shed); U.uLight.value.set(p.heat, p.cold, p.glitch, p.sag);
      U.uFx.value.set(p.flow, p.inward, p.flashY, p.flashK); U.uShut.value.set(p.shutX, p.shutY, p.dustRing); U.uHist.value.set(p.hist);
      lean.rotation.set(p.bpitch, p.byaw, 0); lean.updateMatrixWorld(true);
      // Onda del clic: nace donde se tocó (o en la boca, al interrumpirle).
      if (p.ripple !== ripSeen) { ripSeen = p.ripple; ripAge = 0; if (p.rippleZone === 'mouth' || !touching) headLocal(MOUTH[0], MOUTH[1], MOUTH[2], hitP); U.uRip.value.set(hitP.x, hitP.y, hitP.z, 0); }
      ripAge += dt; U.uRip.value.w = Math.min(ripAge, 9);
      touchK += ((touching ? 1 : 0) - touchK) * (1 - Math.exp(-dt * 9)); U.uTouch.value.w = touchK;
      DU.uBurst.value = p.dustBurst; DU.uB.value = p.dustB; DU.uCold.value = p.cold; DU.uHeat.value = p.heat;
      toScreen(headLocal(0, 0.1, 0, tmp)); BU.uHalo.value.set(tmp.x / cw, 1 - tmp.y / ch); BU.uWarm.value = (0.35 + p.heat * 0.9 + p.level * 0.5) * p.bright * (1 - p.cold); BU.uCold.value = p.cold;
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
      if (near(-EYE.x, EYE.y, 0.84, 0.2)) return 'eyeL';
      if (near(EYE.x, EYE.y, 0.84, 0.2)) return 'eyeR';
      if (near(0, -0.22, 1.02, 0.15)) return 'nose';
      if (near(0, -0.56, 0.9, 0.17, 2)) return 'mouth';
      toScreen(tmp.set(KNOT[0], KNOT[1], KNOT[2] + 0.1)); if ((x - tmp.x) ** 2 + (y - tmp.y) ** 2 < (0.24 * u) ** 2) return 'knot';
      if (z === 'head') return hitP.y > 0.42 ? 'hair' : 'head';
      return z;
    },
  };
}
