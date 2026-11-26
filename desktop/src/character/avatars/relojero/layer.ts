// El Relojero v2 como capa de un renderer ajeno (AvatarLayer). Es el núcleo único: createAvatar (index.ts)
// solo le pone alrededor un renderer, un bucle (30 fps) y la entrada de ratón.
// Construye la escena en varias etapas (ningún bloqueo largo del hilo principal) y compila los shaders en asíncrono.
import * as THREE from 'three';
import type { AvatarLayer, AvatarOptions, AvatarViewport } from '../types';
import { Brain, HALO, type Pose, type Zone } from './brain';
import type { Viseme } from './voice';
import {
  FX, FY, FYC, XW, EYE_X, EYE_Y, EYE_R, MOUTH_Y, LIP_W, lipUp, lipLo, zE, zM, relief, yb, yTop, yBot, patch, caseGeo, tube, tag, merge, wheel, spiral, breguetHand,
} from './geo';
import { lux, glassMat, BASE, G } from './lux';
import { FACE_GLSL, faceDeformJS, type FaceU } from './face';
import { nightSky, glowPoints, backdrop } from './mats';

export type AvatarTheme = 'dark' | 'light';
export interface RelojeroOptions extends AvatarOptions {
  /** Con `transparent`, el tema sobre el que flota: 'light' baja la ganancia de los destellos aditivos. */
  readonly theme?: AvatarTheme;
}
/** La capa más lo que el envoltorio necesita para la entrada de ratón. */
export interface RelojeroLayer extends AvatarLayer {
  readonly ready: Promise<void>;
  readonly brain: Brain;
  /** Zona bajo un punto del recuadro (px CSS, origen arriba a la izquierda), o null. */
  hit(x: number, y: number): Zone | null;
  /** Posición de la cabeza en el recuadro (px CSS). */
  faceScreen(): { x: number; y: number };
  /** `lookAt` se ha llamado: el anfitrión dirige la mirada y el ratón ya no. */
  externalGaze(): boolean;
  setTheme(theme: AvatarTheme): void;
}

const RY_TOP = 0.94;
const V = (x: number, y: number, z: number): THREE.Vector3 => new THREE.Vector3(x, y, z);
const L3 = (c: [number, number, number]): THREE.Color => new THREE.Color().setRGB(c[0], c[1], c[2]);
const BRASS = L3(BASE.brass), STEEL = L3(BASE.steel), BLUED = L3(BASE.blued), RUBY = new THREE.Color().setRGB(0.5, 0.012, 0.03);
const VIS = new Set(['A', 'E', 'I', 'O', 'U', 'M', 'F', 'C', '_']);

function grid(nu: number, nv: number, f: (u: number, v: number) => [number, number, number]): THREE.BufferGeometry {
  const pos: number[] = [], idx: number[] = [];
  for (let i = 0; i <= nu; i++) for (let j = 0; j <= nv; j++) pos.push(...f(i / nu, j / nv));
  for (let i = 0; i < nu; i++) for (let j = 0; j < nv; j++) { const a = i * (nv + 1) + j, b = a + nv + 1; idx.push(a, b, a + 1, b, b + 1, a + 1); }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setIndex(idx); g.computeVertexNormals();
  return g;
}
function bar(pts: [number, number][], w: number, z: number, d = 0.012): THREE.BufferGeometry {
  const L: [number, number][] = [], R: [number, number][] = [];
  pts.forEach((p, i) => {
    const a = pts[Math.max(0, i - 1)]!, b = pts[Math.min(pts.length - 1, i + 1)]!;
    const dx = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dx, dy) || 1, nx = -dy / l, ny = dx / l;
    L.push([p[0] + nx * w, p[1] + ny * w]); R.push([p[0] - nx * w, p[1] - ny * w]);
  });
  const sh = new THREE.Shape(); sh.moveTo(...L[0]!); L.slice(1).forEach((p) => sh.lineTo(...p)); R.reverse().forEach((p) => sh.lineTo(...p)); sh.closePath();
  const g = new THREE.ExtrudeGeometry(sh, { depth: d, bevelEnabled: true, bevelThickness: 0.003, bevelSize: 0.003, bevelSegments: 2, curveSegments: 12 });
  g.translate(0, 0, z); return g;
}

const HALO_VS = /* glsl */ `
uniform float uMode, uVal, uHT, uGlow; uniform vec3 uAccent; varying vec3 vC;
void main() {
  float i = float(gl_InstanceID), b = 0.06, sec = mod(uHT, 60.0), d = mod(i - sec + 60.0, 60.0), sym = min(i, 60.0 - i);
  bool big = mod(i, 5.0) < 0.5;
  if (uMode < 0.5) b = 0.1 + 0.85 * exp(-(60.0 - d) / 2.2) * step(30.0, d) + (big ? 0.08 : 0.0);
  else if (uMode < 1.5) b = sym < uVal * 34.0 ? 0.25 + 0.6 * (1.0 - sym / 34.0) : 0.05;
  else if (uMode < 2.5) { float m = 0.0; for (int c = 0; c < 3; c++) { float hd = mod(uVal * 22.0 + float(c) * 20.0, 60.0), dd = mod(hd - i + 60.0, 60.0); m = max(m, exp(-dd / 3.0) * step(dd, 20.0)); } b = 0.05 + 0.85 * m; }
  else if (uMode < 3.5) { float n = uVal * 60.0; b = i < n ? 0.5 : 0.05; if (abs(i - n) < 1.0) b = 1.2; }
  else if (uMode < 4.5) { float fr = uVal * 45.0; b = 0.25 * exp(-uVal * 0.8) + 1.1 * exp(-abs(sym - fr) / 2.5); }
  else if (uMode < 5.5) b = (sin(uHT * 31.0) > 0.0 && uVal < 0.9 ? 0.8 : 0.22) * (big ? 1.0 : 0.6);
  else if (uMode < 6.5) b = i < 0.5 ? 1.2 : 0.035;
  else if (uMode < 7.5) b = 0.015 + (abs(i - floor(mod(uHT / 2.0, 60.0))) < 0.5 ? 0.08 : 0.0);
  else { float w = sin(uVal * 30.0); b = 0.05 + (i < 0.5 ? 0.7 : 0.0) + (abs(i - 59.0) < 0.5 ? step(0.0, w) : 0.0) + (abs(i - 1.0) < 0.5 ? step(w, 0.0) : 0.0); }
  vC = mix(uAccent, vec3(1.0), 0.12) * b * (0.6 + 0.4 * uGlow);
  gl_Position = projectionMatrix * modelViewMatrix * instanceMatrix * vec4(position, 1.0);
}`;

export function createRelojeroLayer(gl: THREE.WebGLRenderer, opts: RelojeroOptions = {}): RelojeroLayer {
  if (!gl.capabilities.isWebGL2) throw new Error('webgl2-unavailable');
  const transparent = opts.transparent === true;
  let pr = opts.pixelRatio ?? 1, external = false;
  const scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(24, 1, 3, 14);
  const brain = new Brain(); brain.reduced = !!opts.reducedMotion; brain.microGestures = !brain.reduced;
  const bg = backdrop(); bg.visible = !transparent; scene.add(bg);
  const root = new THREE.Group(); scene.add(root);
  const body = new THREE.Group(); root.add(body);
  const headPivot = new THREE.Group(); headPivot.position.set(0, 0.12, 0); root.add(headPivot);
  const head = new THREE.Group(); head.position.set(0, 0.88, 0); headPivot.add(head);
  const halo = new THREE.Group(); halo.position.set(0, 1.0, -0.8); root.add(halo);

  // ── Materiales «lux».
  const M = {
    caseM: lux({ base: BASE.caseGold, rough: 0.28, pattern: 'soleil', tint: 0.05, roughVar: 0.18, side: THREE.DoubleSide }),
    rose: lux({ base: BASE.rose, rough: 0.12 }),
    brass: lux({ base: BASE.brass, rough: 0.2 }),
    blued: lux({ base: [0.012, 0.024, 0.13], rough: 0.3, side: THREE.DoubleSide }),
    steel: lux({ base: BASE.steel, rough: 0.1 }),
    lacquer: lux({ base: BASE.lacquer, metal: 0, rough: 0.28, side: THREE.DoubleSide }),
    ivory: lux({ base: [0.8, 0.76, 0.68], metal: 0, rough: 0.34, side: THREE.DoubleSide }),
    bust: lux({ base: [0.012, 0.02, 0.07], metal: 0, rough: 0.42, pattern: 'guilloche', bump: 0.0, tint: 0.12, roughVar: 0.12, clear: 0.6 }),
    lid: lux({ base: [0.9, 0.82, 0.68], metal: 0, rough: 0.22, lidEdge: true }),
    plate: lux({ base: BASE.plate, rough: 0.3, pattern: 'cotes', bump: 0.006, tint: 0.14, roughVar: 0.25 }),
    mech: lux({ base: [1, 1, 1], mech: true, rough: 0.18 }),
    jewel: lux({ base: [0.42, 0.01, 0.03], metal: 0, rough: 0.04 }),
    face: lux({ base: BASE.enamel, metal: 0, rough: 0.16, dial: true, face: true, aoInColor: true }),
    lips: lux({ base: BASE.rose, rough: 0.12, face: true }),
    tines: lux({ base: [1, 1, 1], rough: 0.08 }),
    tint: lux({ base: [1, 1, 1], rough: 0.14 }),
    sun: new THREE.MeshBasicMaterial({ color: 0xffffff }),
    crystal: glassMat([1, 0.96, 0.9], 1), lens: glassMat([0.8, 0.9, 1], 1.2), sky: nightSky(),
    cavity: new THREE.ShaderMaterial({
      uniforms: { ...G, uL: { value: 0 } },
      vertexShader: `${FACE_GLSL}\nvarying vec2 vP; void main(){ vec3 p = position, n = normal; vP = position.xy; faceDeform(p, n); gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0); }`,
      fragmentShader: /* glsl */ `uniform vec3 uAccent; uniform float uL; varying vec2 vP;
        void main(){ vec2 d = (vP - vec2(0.0, ${MOUTH_Y.toFixed(3)})) / vec2(0.17, 0.06); float r = length(d);
          vec3 col = vec3(0.006, 0.006, 0.012) + uAccent * (0.03 + uL * 1.5) * exp(-r * r * 1.4);
          gl_FragColor = vec4(col, 1.0);
          #include <colorspace_fragment>
        }`,
    }),
    ticks: new THREE.ShaderMaterial({
      uniforms: { uMode: { value: 0 }, uVal: { value: 0 }, uHT: { value: 0 }, uGlow: G.uGlow, uAccent: G.uAccent },
      vertexShader: HALO_VS, fragmentShader: `varying vec3 vC; void main(){ gl_FragColor = vec4(vC, 1.0);\n#include <colorspace_fragment>\n}`,
    }),
  };
  M.jewel.uniforms.uEmis!.value = new THREE.Vector3();

  // ── Piezas que el bucle anima (se rellenan durante el montaje).
  const eyeC = (s: number): THREE.Vector3 => V(s * EYE_X, EYE_Y, zM(s * EYE_X, EYE_Y) + 0.03);
  const eyeRotY = 0.3;
  const eyeBase = [-1, 1].map((s) => new THREE.Matrix4().compose(eyeC(s), new THREE.Quaternion().setFromEuler(new THREE.Euler(0, s * eyeRotY, 0)), V(1, 1, 1)));
  const B: [number, number] = [0.02, 0.53], E: [number, number] = [0.27, 0.41], PP: [number, number] = [0.165, 0.47];
  const W4: [number, number] = [0.34, 0.3], W3: [number, number] = [-0.08, 0.36], W2: [number, number] = [-0.33, 0.42], BR: [number, number] = [-0.19, 0.64];
  const jewelPos: THREE.Vector3[] = [V(B[0], B[1], 0.36), V(E[0], E[1], 0.29), V(PP[0], PP[1], 0.3), V(W4[0], W4[1], 0.318), V(W3[0], W3[1], 0.318), V(W2[0], W2[1], 0.318), V(BR[0], BR[1], 0.27), V(-0.795, 0.06, -0.03), V(0.795, 0.06, -0.03)];
  const NT = 19, tineX = (i: number): number => (i < 10 ? (i - 4.5) * 0.03 : (i - 10 - 4) * 0.03);
  const H = V(-0.63, 0.12, 0.22), LENS_ON = V(-EYE_X, EYE_Y, zM(-EYE_X, EYE_Y) + 0.19), LENS_OFF = V(-0.74, 0.56, 0.02);
  const vOn = LENS_ON.clone().sub(H), vOff = LENS_OFF.clone().sub(H), lenOn = vOn.length(), lenOff = vOff.length();
  const qArc = new THREE.Quaternion().setFromUnitVectors(vOff.clone().normalize(), vOn.clone().normalize());
  let suns!: THREE.InstancedMesh, rings!: THREE.InstancedMesh, planets!: THREE.InstancedMesh, lids!: THREE.InstancedMesh, brows!: THREE.InstancedMesh;
  let tines!: THREE.InstancedMesh, crowns!: THREE.InstancedMesh, arm!: THREE.Mesh, heart!: THREE.Mesh, ticks!: THREE.InstancedMesh;
  const lens = new THREE.Group();
  const glow = glowPoints(14);
  const proxies: THREE.Mesh[] = [];
  const HC = { x: 0.44, y: -0.72 }, heartRot = 0.27;

  // ── Montaje por etapas.
  const prof: [number, number][] = [[0.15, 0.03], [0.19, -0.04], [0.32, -0.13], [0.56, -0.24], [0.78, -0.35], [0.92, -0.5], [0.99, -0.74], [1.02, -1.1], [1.02, -1.9]];
  const Rof = (y: number): number => { for (let i = 1; i < prof.length; i++) { const a = prof[i - 1]!, b = prof[i]!; if (y >= b[1]) { const u = (a[1] - y) / (a[1] - b[1]); return a[0] + (b[0] - a[0]) * u; } } return 1.02; };
  const ZS = 0.56, torsoZ = (x: number, y: number): number => ZS * Math.sqrt(Math.max(0.0001, Rof(y) ** 2 - x * x));
  const heartPos = V(HC.x, HC.y, torsoZ(HC.x, HC.y));

  const mechParts: THREE.BufferGeometry[] = [];
  const atM = (g: THREE.BufferGeometry, p: [number, number], z: number): THREE.BufferGeometry => { g.translate(p[0], p[1], z); return g; };
  const steps: (() => void)[] = [
    () => { // Caja, esfera de esmalte, cristal y platina.
      head.add(new THREE.Mesh(caseGeo(), M.caseM));
      const maskTop = (x: number): number => Math.min(yb(x), yTop(x));
      const ao = (x: number, y: number): number => { const e = Math.hypot(x / FX, (y - FYC) / FY); return Math.max(0.5, Math.min(1.04, 1 + relief(x, y) * 1.2 + Math.min(0, relief(x, y)) * 6)) * (1 - 0.22 * Math.max(0, (e - 0.82) / 0.18)); };
      head.add(new THREE.Mesh(patch(FX * 0.999, yBot, maskTop, zM, 72, 64, ao), M.face));
      head.add(Object.assign(new THREE.Mesh(patch(XW, yb, yTop, (x, y) => zE(x, y) + 0.035, 40, 18), M.crystal), { renderOrder: 5 }));
      const sh = new THREE.Shape(); const N = 40;
      for (let i = 0; i <= N; i++) { const x = -XW + (2 * XW * i) / N; const p: [number, number] = [x, yTop(x) * 0.995 + 0.004]; if (i) sh.lineTo(...p); else sh.moveTo(...p); }
      for (let i = N; i >= 0; i--) { const x = -XW + (2 * XW * i) / N; sh.lineTo(x, yb(x) - 0.06); }
      const g = new THREE.ShapeGeometry(sh, 4); g.translate(0, 0, 0.2); head.add(new THREE.Mesh(g, M.plate));
    },
    () => { // Biseles, cuencas, coronas fijas, asa (oro rosa) y labios.
      const bezelPts: THREE.Vector3[] = [], browPts: THREE.Vector3[] = [];
      for (let i = 0; i < 96; i++) { const a = (i / 96) * Math.PI * 2, x = Math.cos(a) * FX, y = FYC + Math.sin(a) * FY; bezelPts.push(V(x, y, zE(x, y) + 0.03)); }
      for (let i = 0; i <= 40; i++) { const x = -XW + (2 * XW * i) / 40; browPts.push(V(x, yb(x), zM(x, yb(x)) + 0.004)); }
      const st: THREE.BufferGeometry[] = [tube(bezelPts, 0.034, true, 140, 240), tube(browPts, 0.011, false, 0, 60)];
      for (const s of [-1, 1]) { const t = new THREE.TorusGeometry(EYE_R + 0.008, 0.019, 10, 48); t.rotateY(s * eyeRotY); const c = eyeC(s); t.translate(c.x, c.y, c.z + 0.012); st.push(t); }
      for (const s of [-1, 1]) { const c = new THREE.CylinderGeometry(0.035, 0.045, 0.06, 20); c.rotateZ(Math.PI / 2); c.translate(s * 0.685, 0.06, -0.03); st.push(c); }
      const pend = new THREE.CylinderGeometry(0.05, 0.065, 0.11, 32); const pp = pend.attributes.position!;
      for (let i = 0; i < pp.count; i++) { const x = pp.getX(i), z = pp.getZ(i), r = Math.hypot(x, z); if (r > 0.045) { const k = 1 - 0.1 * (Math.sin(Math.atan2(z, x) * 16) > 0 ? 1 : 0); pp.setX(i, x * k); pp.setZ(i, z * k); } }
      pend.computeVertexNormals(); pend.translate(0, RY_TOP + 0.03, -0.02); st.push(pend);
      st.push(new THREE.SphereGeometry(0.03, 16, 10).translate(0, RY_TOP + 0.1, -0.02));
      const bowRing = new THREE.TorusGeometry(0.13, 0.02, 12, 56, Math.PI * 1.62); bowRing.rotateZ(-0.31 * Math.PI); bowRing.translate(0, RY_TOP + 0.235, -0.02); st.push(bowRing);
      head.add(new THREE.Mesh(merge(st), M.rose));
      const lp: THREE.Vector3[] = []; const N = 40;
      for (let i = 0; i <= N; i++) { const x = LIP_W * Math.cos(Math.PI * (1 - i / N)); lp.push(V(x, lipUp(x) + 0.004, zM(x, lipUp(x)) + 0.01)); }
      for (let i = 1; i < N; i++) { const x = LIP_W * Math.cos(Math.PI * (i / N)); lp.push(V(x, lipLo(x) - 0.004, zM(x, lipLo(x)) + 0.01)); }
      head.add(new THREE.Mesh(tube(lp, 0.0105, true, 0, 140), M.lips));
      head.add(new THREE.Mesh(patch(LIP_W, lipLo, lipUp, (x, y) => zM(x, y) + 0.003, 20, 6), M.cavity));
    },
    // Movimiento: una rueda por etapa (cada extrusión cuesta), y al final un solo draw call.
    ...([
      () => tag(atM(wheel(0.125, 80, { spokes: 0, rim: 0.02 }), BR, 0.215), BR, [0.004, 0, 0], BRASS),
      () => tag(atM(wheel(0.082, 36, { spokes: 0 }), BR, 0.24), BR, [0.004, 0, 0], STEEL),
      () => tag(atM(wheel(0.13, 72, { spokes: 4 }), W2, 0.23), W2, [-0.02, 0, 0], BRASS),
      () => tag(atM(wheel(0.1, 60, { spokes: 4 }), W3, 0.248), W3, [0.07, 0, 0], BRASS),
      () => tag(atM(wheel(0.085, 56, { spokes: 4 }), W4, 0.255), W4, [-0.25, 0, 0], BRASS),
      () => tag(atM(wheel(0.066, 15, { style: 'escape', spokes: 4, rim: 0.01 }), E, 0.268), E, [1, 0, 0], STEEL),
      () => tag(atM(wheel(0.145, 0, { style: 'rim', spokes: 3, rim: 0.016, hub: 0.022, depth: 0.014 }), B, 0.3), B, [0, 1, 0], BRASS),
      () => merge([tag(atM(spiral(0.02, 0.07, 4, 0.0035), BR, 0.255), BR, [0.004, 0, 0], BLUED), tag(atM(spiral(0.022, 0.085, 7, 0.0028), B, 0.322), B, [0, 0.7, 0], BLUED)]),
    ] as (() => THREE.BufferGeometry)[]).map((mk) => () => { mechParts.push(mk()); }),
    () => { const mech: THREE.BufferGeometry[] = [];
      const at = (g: THREE.BufferGeometry, p: [number, number], z: number): THREE.BufferGeometry => { g.translate(p[0], p[1], z); return g; };
      for (let i = 0; i < 10; i++) { const a = (i / 10) * Math.PI * 2; mech.push(tag(at(new THREE.SphereGeometry(0.009, 8, 6), [B[0] + Math.cos(a) * 0.147, B[1] + Math.sin(a) * 0.147], 0.307), B, [0, 1, 0], i % 2 ? BRASS : STEEL)); }
      const sh = new THREE.Shape(), dx = B[0] - PP[0], dy = B[1] - PP[1], l = Math.hypot(dx, dy), ux = dx / l, uy = dy / l, w = 0.009;
      const tipX = PP[0] + ux * 0.11, tipY = PP[1] + uy * 0.11;
      sh.moveTo(PP[0] - uy * w, PP[1] + ux * w); sh.lineTo(tipX - uy * w * 1.6, tipY + ux * w * 1.6); sh.lineTo(tipX + uy * w * 1.6, tipY - ux * w * 1.6); sh.lineTo(PP[0] + uy * w, PP[1] - ux * w); sh.closePath();
      const ex = E[0] - PP[0], ey = E[1] - PP[1], el = Math.hypot(ex, ey), vx = ex / el, vy = ey / el, cx = PP[0] + vx * 0.055, cy = PP[1] + vy * 0.055;
      const armS = new THREE.Shape();
      armS.moveTo(cx - vy * 0.06 - vx * 0.008, cy + vx * 0.06 - vy * 0.008); armS.lineTo(cx - vy * 0.06 + vx * 0.012, cy + vx * 0.06 + vy * 0.012);
      armS.lineTo(cx + vy * 0.06 + vx * 0.012, cy - vx * 0.06 + vy * 0.012); armS.lineTo(cx + vy * 0.06 - vx * 0.008, cy - vx * 0.06 - vy * 0.008); armS.closePath();
      const bar0 = new THREE.CylinderGeometry(0.008, 0.008, 0.06, 6); bar0.rotateZ(Math.atan2(vy, vx) - Math.PI / 2); bar0.translate(PP[0] + vx * 0.03, PP[1] + vy * 0.03, 0.005);
      for (const g of [new THREE.ExtrudeGeometry(sh, { depth: 0.01, bevelEnabled: false }), new THREE.ExtrudeGeometry(armS, { depth: 0.01, bevelEnabled: false }), bar0]) mech.push(tag(at(g, [0, 0], 0.282), PP, [0, 0, 1], STEEL));
      for (const s of [-1, 1]) { const b = new THREE.BoxGeometry(0.012, 0.022, 0.012); b.translate(cx + s * vy * 0.055 + vx * 0.02, cy - s * vx * 0.055 + vy * 0.02, 0.287); mech.push(tag(b, PP, [0, 0, 1], RUBY)); }
      mech.push(tag(bar([[-0.3, 0.7], [-0.15, 0.62], [B[0], B[1]]], 0.026, 0.338), [0, 0], [0, 0, 0], BRASS));
      mech.push(tag(bar([[-0.5, 0.36], [W2[0], W2[1]], [W3[0], W3[1]], [0.1, 0.33], [W4[0], W4[1]]], 0.022, 0.295), [0, 0], [0, 0, 0], BRASS));
      for (const p of [[-0.3, 0.7], [-0.5, 0.36], [0.1, 0.33]] as [number, number][]) { const sc = new THREE.CylinderGeometry(0.014, 0.014, 0.01, 14); sc.rotateX(Math.PI / 2); mech.push(tag(at(sc, p, 0.355), [0, 0], [0, 0, 0], BLUED)); }
      mechParts.push(...mech); },
    () => { head.add(new THREE.Mesh(merge(mechParts), M.mech)); mechParts.length = 0; },
    () => { // Rubíes, ojos-orrery, párpados, cejas.
      const jewels = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1, 2), M.jewel, jewelPos.length);
      const m = new THREE.Matrix4(); jewelPos.forEach((p, i) => { const r = i >= 7 ? 0.03 : 0.015; m.makeScale(r, r, r * 0.6).setPosition(p); jewels.setMatrixAt(i, m); }); head.add(jewels);
      const sockets = merge([-1, 1].map((s) => { const g = new THREE.CircleGeometry(EYE_R - 0.008, 40); g.rotateY(s * eyeRotY); const c = eyeC(s); g.translate(c.x, c.y, c.z + 0.004); return g; }));
      { const p = sockets.attributes.position!, a = new Float32Array(p.count); for (let i = 0; i < p.count; i++) a[i] = p.getX(i) < 0 ? -1 : 1; sockets.setAttribute('aSide', new THREE.BufferAttribute(a, 1)); }
      head.add(new THREE.Mesh(sockets, M.sky));
      suns = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1, 3), M.sun, 2);
      rings = new THREE.InstancedMesh(new THREE.TorusGeometry(1, 0.06, 6, 64), M.tint, 4);
      planets = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1, 1), M.tint, 4);
      lids = new THREE.InstancedMesh(new THREE.SphereGeometry(EYE_R - 0.014, 32, 16, 0, Math.PI, 0, Math.PI), M.lid, 4);
      brows = new THREE.InstancedMesh(breguetHand(0.33), M.blued, 2);
      for (const im of [suns, rings, planets, lids, brows]) { im.instanceMatrix.setUsage(THREE.DynamicDrawUsage); im.frustumCulled = false; head.add(im); }
      [BRASS, RUBY, BRASS, RUBY].forEach((c, i) => planets.setColorAt(i, c));
      [BLUED, BRASS, BLUED, BRASS].forEach((c, i) => rings.setColorAt(i, c));
    },
    () => { // Boca de láminas, coronas, lupa.
      const tg = new THREE.CylinderGeometry(0.0065, 0.0065, 1, 6); tg.translate(0, 0.5, 0); tg.scale(1, 1, 0.7);
      tines = new THREE.InstancedMesh(tg, M.tines, NT); tines.instanceMatrix.setUsage(THREE.DynamicDrawUsage); tines.frustumCulled = false; head.add(tines);
      for (let i = 0; i < NT; i++) tines.setColorAt(i, STEEL);
      const cg = new THREE.CylinderGeometry(0.075, 0.075, 0.075, 48, 1); const p = cg.attributes.position!;
      for (let i = 0; i < p.count; i++) { const x = p.getX(i), z = p.getZ(i), r = Math.hypot(x, z); if (r > 0.07) { const k = 1 - 0.09 * (Math.sin(Math.atan2(z, x) * 24) > 0 ? 1 : 0); p.setX(i, x * k); p.setZ(i, z * k); } }
      cg.computeVertexNormals(); cg.rotateZ(Math.PI / 2);
      crowns = new THREE.InstancedMesh(cg, M.brass, 2); crowns.instanceMatrix.setUsage(THREE.DynamicDrawUsage); head.add(crowns);
      const ag = new THREE.CylinderGeometry(0.012, 0.012, 1, 8); ag.translate(0, 0.5, 0); arm = new THREE.Mesh(ag, M.brass); head.add(arm);
      head.add(lens);
      const barrel = merge([
        (() => { const g = new THREE.CylinderGeometry(0.09, 0.075, 0.08, 40, 1, true); g.rotateX(Math.PI / 2); return g; })(),
        new THREE.TorusGeometry(0.09, 0.012, 8, 40).translate(0, 0, 0.04), new THREE.TorusGeometry(0.076, 0.009, 8, 40).translate(0, 0, -0.04),
        new THREE.SphereGeometry(0.02, 10, 8).translate(-0.095, 0, 0),
      ]);
      lens.add(new THREE.Mesh(barrel, M.rose));
      const gl0 = new THREE.Mesh(new THREE.CircleGeometry(0.088, 32).translate(0, 0, 0.035), M.lens); gl0.renderOrder = 6; lens.add(gl0);
    },
    () => { // Busto.
      const lathe = new THREE.LatheGeometry(new THREE.SplineCurve([...prof].reverse().map(([r, y]) => new THREE.Vector2(r, y))).getPoints(60), 72); lathe.scale(1, 1, ZS); lathe.computeVertexNormals();
      body.add(new THREE.Mesh(lathe, M.bust));
      const plW = (y: number): number => 0.1 - Math.max(0, -y - 0.05) * 0.02;
      const shirt = grid(20, 30, (u, v) => { const y = -0.04 - v * 1.5, w = plW(y), x = (u * 2 - 1) * w; return [x, y, torsoZ(x, y) + 0.012]; });
      const collar = new THREE.LatheGeometry([new THREE.Vector2(0.2, -0.03), new THREE.Vector2(0.195, 0.03), new THREE.Vector2(0.205, 0.075)], 40, 0.3, Math.PI * 2 - 0.6);
      body.add(new THREE.Mesh(merge([shirt, collar]), M.ivory));
      const lapel = (s: number): THREE.BufferGeometry => grid(14, 30, (u, v) => {
        const y = -0.08 - v * 1.45, w0 = plW(y), bulge = Math.sin(Math.min(1, v * 1.3) * Math.PI) * 0.13 + 0.035, x = s * (w0 + u * bulge);
        return [x, y, torsoZ(x, y) + 0.018 + 0.012 * Math.sin(u * Math.PI)];
      });
      const bs = new THREE.Shape(); bs.moveTo(0, 0.012); bs.bezierCurveTo(0.05, 0.05, 0.1, 0.07, 0.12, 0.04); bs.lineTo(0.12, -0.04); bs.bezierCurveTo(0.1, -0.07, 0.05, -0.05, 0, -0.012);
      bs.bezierCurveTo(-0.05, -0.05, -0.1, -0.07, -0.12, -0.04); bs.lineTo(-0.12, 0.04); bs.bezierCurveTo(-0.1, 0.07, -0.05, 0.05, 0, 0.012);
      const bow = merge([new THREE.ExtrudeGeometry(bs, { depth: 0.03, bevelEnabled: true, bevelThickness: 0.012, bevelSize: 0.01, bevelSegments: 3, curveSegments: 10 }), new THREE.BoxGeometry(0.04, 0.05, 0.05).translate(0, 0, 0.02)]);
      bow.translate(0, -0.03, 0.2);
      body.add(new THREE.Mesh(merge([lapel(-1), lapel(1), bow]), M.lacquer));
      body.add(new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.15, 0.5, 24, 1, true).translate(0, 0.25, 0), M.steel));
      body.add(new THREE.Mesh(merge([
        ...[0.07, 0.16, 0.25].map((y) => new THREE.TorusGeometry(0.15, 0.014, 8, 32).rotateX(Math.PI / 2).translate(0, y, 0)),
        new THREE.TorusGeometry(0.135, 0.02, 10, 48).rotateY(heartRot).translate(heartPos.x, heartPos.y, heartPos.z + 0.01),
        ...[-0.36, -0.6, -0.84].map((y) => new THREE.SphereGeometry(0.018, 12, 8).translate(0, y, torsoZ(0, y) + 0.022)),
      ]), M.rose));
      body.add(new THREE.Mesh(new THREE.CircleGeometry(0.125, 40).rotateY(heartRot).translate(heartPos.x, heartPos.y, heartPos.z - 0.004), M.plate));
      heart = new THREE.Mesh(merge([
        tag(wheel(0.105, 64, { spokes: 0, rim: 0.02 }), [0, 0], [0, 0, 0], BRASS),
        tag(spiral(0.018, 0.08, 6, 0.0035).translate(0, 0, 0.018), [0, 0], [0, 0, 0], BLUED),
        tag(new THREE.CylinderGeometry(0.02, 0.02, 0.02, 16).rotateX(Math.PI / 2).translate(0, 0, 0.02), [0, 0], [0, 0, 0], STEEL),
      ]), M.mech);
      const hg = new THREE.Group(); hg.position.copy(heartPos); hg.rotation.y = heartRot; hg.add(heart); body.add(hg);
    },
    () => { // Anillo horario, brillos y zonas de interacción.
      halo.add(new THREE.Mesh(merge([new THREE.TorusGeometry(1.24, 0.011, 8, 160), new THREE.TorusGeometry(1.1, 0.006, 6, 160)]), M.brass));
      ticks = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 0.012), M.ticks, 60);
      const m = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3();
      for (let i = 0; i < 60; i++) {
        const a = Math.PI / 2 - (i / 60) * Math.PI * 2, big = i % 5 === 0, r = big ? 1.17 : 1.19;
        q.setFromAxisAngle(V(0, 0, 1), a - Math.PI / 2); s.set(big ? 0.022 : 0.009, big ? 0.1 : 0.05, 1); p.set(Math.cos(a) * r, Math.sin(a) * r, 0);
        ticks.setMatrixAt(i, m.compose(p, q, s));
      }
      ticks.frustumCulled = false; halo.add(ticks);
      scene.add(glow.pts);
      const hidden = new THREE.MeshBasicMaterial({ visible: false });
      const px = (g: THREE.BufferGeometry, parent: THREE.Object3D, pos: THREE.Vector3, zone: Zone): void => { const mm = new THREE.Mesh(g, hidden); mm.position.copy(pos); mm.userData.zone = zone; parent.add(mm); proxies.push(mm); };
      px(new THREE.SphereGeometry(0.11, 8, 6), head, V(-0.75, 0.06, -0.03), 'crown'); px(new THREE.SphereGeometry(0.11, 8, 6), head, V(0.75, 0.06, -0.03), 'crown');
      px(new THREE.SphereGeometry(0.17, 8, 6), head, V(0, RY_TOP + 0.2, 0), 'crown');
      px(new THREE.SphereGeometry(0.14, 8, 6), head, eyeC(-1), 'eye'); px(new THREE.SphereGeometry(0.14, 8, 6), head, eyeC(1), 'eye');
      px(new THREE.BoxGeometry(0.4, 0.17, 0.1), head, V(0, MOUTH_Y, zM(0, MOUTH_Y)), 'mouth');
      px(new THREE.SphereGeometry(0.28, 10, 8).scale(1.6, 0.9, 0.6), head, V(0, 0.52, 0.42), 'movement');
      px(new THREE.SphereGeometry(0.17, 8, 6), body, heartPos, 'chest');
      px(new THREE.SphereGeometry(1, 16, 12).scale(0.72, 0.96, 0.75), head, V(0, 0, -0.05), 'face');
      px(new THREE.TorusGeometry(1.18, 0.1, 6, 48), halo, V(0, 0, 0), 'halo');
    },
  ];

  // ── Estado de render.
  let W = 1, Hh = 1, ready = false, disposed = false;
  const Mx = new THREE.Matrix4(), M2 = new THREE.Matrix4(), Mq = new THREE.Quaternion(), Ms = new THREE.Vector3(), Mp = new THREE.Vector3(), E3 = new THREE.Euler();
  const tmpC = new THREE.Color(), tmpV = new THREE.Vector3(), tmpV2 = new THREE.Vector3(), headWorld = new THREE.Vector3(), accent = new THREE.Color();
  const sunLocal = [new THREE.Vector3(), new THREE.Vector3()], fu: FaceU = { jaw: 0, smL: 0, smR: 0, lipW: 0, round: 0 };
  const o3: [number, number, number] = [0, 0, 0], o3b: [number, number, number] = [0, 0, 0];
  let lastMouthKey = '';
  const compose = (out: THREE.Matrix4, x: number, y: number, z: number, rx: number, ry: number, rz: number, sx: number, sy = sx, sz = sx, order: THREE.EulerOrder = 'XYZ'): THREE.Matrix4 =>
    out.compose(Mp.set(x, y, z), Mq.setFromEuler(E3.set(rx, ry, rz, order)), Ms.set(sx, sy, sz));
  const glowSet = (i: number, p: THREE.Vector3, c: THREE.Color, k: number, size: number): void => { glow.pos.set([p.x, p.y, p.z], i * 3); glow.col.set([c.r * k, c.g * k, c.b * k], i * 3); glow.size[i] = size; };
  const WHITE = new THREE.Color(0xfff2d8), GOLDY = new THREE.Color().setRGB(1, 0.85, 0.55);

  const fit = (): void => {
    const fitH = 3.45, fitW = 2.75, tan = Math.tan(THREE.MathUtils.degToRad(cam.fov / 2)), dist = Math.max(fitH / 2, fitW / 2 / (W / Hh)) / tan;
    cam.aspect = W / Hh; cam.position.set(0, 0.62, dist); cam.lookAt(0, 0.62, 0); cam.near = dist - 3; cam.far = dist + 3; cam.updateProjectionMatrix();
    glow.mat.uniforms.uPx!.value = (Hh * pr) / (2 * tan); bg.material.uniforms.uAsp!.value = W / Hh;
  };

  function draw(p: Pose): void {
    const f = p.face, g = Math.min(1.3, p.glow), cold = p.cold;
    accent.setRGB(p.accent[0], p.accent[1], p.accent[2]);
    G.uT.value = p.t; G.uGlow.value = g; G.uCold.value = cold; G.uDim.value = 1 - 0.55 * cold; G.uExpo.value = 1.05 - 0.2 * cold;
    G.uKey.value.setRGB(p.key[0], p.key[1], p.key[2]); G.uAccent.value.copy(accent);
    G.uRot.value.set(p.train, p.balance, p.pallet); G.uBlush.value = f.blush;
    G.uJaw.value = f.jaw; G.uSmL.value = f.smL; G.uSmR.value = f.smR; G.uLipW.value = f.w; G.uRound.value = f.rnd;
    body.position.set(0, p.breath * 0.014 - 0.007 + p.shrug * 0.02, p.lean * 0.03); body.rotation.y = p.yaw * 0.12; body.scale.set(1 + p.breath * 0.006, 1, 1);
    headPivot.position.set(0, 0.12 + p.rise + p.shrug * 0.015, p.lean * 0.12); headPivot.rotation.set(p.pitch, p.yaw, p.roll, 'YXZ');
    halo.position.set(p.yaw * 0.25, 1.0 + p.rise * 0.5, -0.8); halo.rotation.z = -p.haloSpin - p.t * 0.01;
    heart.rotation.z = -p.barrel * 2.4;
    M.crystal.uniforms.uFlash!.value = p.flash;
    M.sky.uniforms.uT!.value = p.orbit; (M.sky.uniforms.uC!.value as THREE.Color).copy(accent); M.sky.uniforms.uG!.value = g * (1 - cold * 0.8);
    M.ticks.uniforms.uMode!.value = p.halo; M.ticks.uniforms.uVal!.value = p.haloVal; M.ticks.uniforms.uHT!.value = p.t;
    // Ojos: sol (pupila), anillos armilares, planetas; párpados superior e inferior con inclinación propia.
    for (let e = 0; e < 2; e++) {
      const s = e === 0 ? -1 : 1, base = eyeBase[e]!, pupil = e === 0 ? p.pupilL : p.pupilR;
      const sx = p.gx * 0.035, sy = -p.gy * 0.03;
      suns.setMatrixAt(e, Mx.multiplyMatrices(base, compose(M2, sx, sy, 0.05, 0, 0, 0, 0.03 * pupil)));
      sunLocal[e]!.set(sx, sy, 0.05).applyMatrix4(base);
      const tx = 0.95 + p.gy * 0.5, ty = p.gx * 0.6 - s * 0.15;
      rings.setMatrixAt(e * 2, Mx.multiplyMatrices(base, compose(M2, sx * 0.6, sy * 0.6, 0.045, tx, ty, p.orbit * 0.3, 0.072)));
      rings.setMatrixAt(e * 2 + 1, Mx.multiplyMatrices(base, compose(M2, sx * 0.6, sy * 0.6, 0.045, -0.45 + p.gy * 0.4, -ty * 0.8 + 0.5 * s, -p.orbit * 0.2, 0.092)));
      for (let k = 0; k < 2; k++) {
        rings.getMatrixAt(e * 2 + k, M2); const a = p.orbit * (k ? 1.7 : 1.1) + e * 2 + k * 3;
        tmpV.set(Math.cos(a), Math.sin(a), 0).applyMatrix4(M2); planets.setMatrixAt(e * 2 + k, compose(Mx, tmpV.x, tmpV.y, tmpV.z, 0, 0, 0, k ? 0.012 : 0.015));
      }
      const up = e === 0 ? f.uL : f.uR, lo = e === 0 ? f.dL : f.dR, tl = e === 0 ? f.tL : f.tR;
      const rxU = -Math.acos(Math.max(-1, Math.min(1, 2 * Math.max(0.03, Math.min(1, up)) - 1)));
      const rxD = -Math.acos(Math.max(-1, Math.min(1, 2 * Math.max(0.03, Math.min(0.75, lo)) - 1)));
      lids.setMatrixAt(e, Mx.multiplyMatrices(base, compose(M2, 0, 0, 0.022, rxU, 0, s * tl, 1, 1, 1, 'ZYX')));
      lids.setMatrixAt(2 + e, Mx.multiplyMatrices(base, compose(M2, 0, 0, 0.02, rxD, 0, Math.PI - s * tl * 0.4, 1, 1, 1, 'ZYX')));
    }
    suns.instanceMatrix.needsUpdate = rings.instanceMatrix.needsUpdate = planets.instanceMatrix.needsUpdate = lids.instanceMatrix.needsUpdate = true;
    tmpC.copy(accent).lerp(WHITE, 0.35); M.sun.color.copy(tmpC).multiplyScalar(1.5 * g * (1 - cold * 0.85));
    // Cejas: agujas Breguet (pivote en el cañón, junto a la nariz).
    for (let e = 0; e < 2; e++) {
      const s = e === 0 ? -1 : 1, ang = e === 0 ? f.bAL : f.bAR + p.browSpin, lift = e === 0 ? f.lL : f.lR;
      const pxx = s * (0.075 - f.furrow * 0.018), py = 0.168 + lift - f.furrow * 0.012;
      const spinZ = e === 1 ? Math.min(0.07, Math.abs(Math.sin(p.browSpin / 2)) * 0.12) : 0;
      brows.setMatrixAt(e, compose(Mx, pxx, py, zM(pxx, py) + 0.035 + spinZ, 0, s * 0.42, s > 0 ? ang - 0.06 : Math.PI - ang + 0.06, 1.02, 1.55, 1));
    }
    brows.instanceMatrix.needsUpdate = true;
    // Boca: láminas rígidas ancladas a los labios deformados (las de abajo bajan con la mandíbula).
    fu.jaw = f.jaw; fu.smL = f.smL; fu.smR = f.smR; fu.lipW = f.w; fu.round = f.rnd;
    const mk = `${f.jaw.toFixed(3)}|${f.smL.toFixed(3)}|${f.smR.toFixed(3)}|${f.w.toFixed(3)}|${f.rnd.toFixed(3)}|${p.chime >= 0 ? p.chime.toFixed(2) : -1}|${p.cold.toFixed(2)}`;
    if (mk !== lastMouthKey) {
      lastMouthKey = mk;
      const half = LIP_W * Math.max(0.5, 1 - f.rnd * 0.45);
      for (let i = 0; i < NT; i++) {
        const up = i < 10, x0 = tineX(i), ry = up ? lipUp(x0) - 0.002 : lipLo(x0) + 0.002, z0 = zM(x0, ry) + (up ? 0.01 : 0.012);
        faceDeformJS(x0, ry, z0, fu, o3);
        const tipRest = up ? MOUTH_Y - 0.007 : MOUTH_Y + 0.007;
        const vis = Math.max(0, 1 - Math.pow(Math.abs(x0) / half, 6));
        const len = Math.max(0.003, Math.abs(ry - tipRest) * (0.35 + 0.65 * vis));
        const tau = p.chime < 0 ? -1 : p.chime - (up ? i : i - 9.5) * 0.06, pl = tau > 0 ? Math.exp(-tau * 5) : 0, wob = tau > 0 ? 0.005 * pl * Math.sin(tau * 60) : 0;
        faceDeformJS(x0, ry + (up ? -0.01 : 0.01), z0, fu, o3b); // dirección local de la lámina tras la deformación
        const rz = Math.atan2(-(o3b[0] - o3[0]), o3b[1] - o3[1]); // gira +y hacia la punta
        tines.setMatrixAt(i, compose(Mx, o3[0] + wob, o3[1], o3[2], 0, 0, rz, 1, len, 1));
        tmpC.copy(STEEL).lerp(GOLDY, Math.min(1, pl * 1.4)).multiplyScalar(1 + pl * 1.5); tines.setColorAt(i, tmpC);
      }
      tines.instanceMatrix.needsUpdate = true; tines.instanceColor!.needsUpdate = true;
    }
    M.cavity.uniforms.uL!.value = f.jaw * 0.8 * g + (p.chime >= 0 ? Math.exp(-p.chime * 2) * 0.5 : 0);
    for (let e = 0; e < 2; e++) { const s = e === 0 ? -1 : 1; crowns.setMatrixAt(e, compose(Mx, s * 0.74, 0.06, -0.03, s * p.crown, 0, 0, 1)); }
    crowns.instanceMatrix.needsUpdate = true;
    // Lupa.
    const k = Math.min(1.06, Math.max(-0.04, p.loupe));
    Mq.identity().slerp(qArc, k);
    tmpV.copy(vOff).normalize().applyQuaternion(Mq).multiplyScalar(lenOff + (lenOn - lenOff) * k);
    arm.position.copy(H); arm.quaternion.setFromUnitVectors(V(0, 1, 0), tmpV2.copy(tmpV).normalize()); arm.scale.set(1, tmpV.length() - 0.07, 1);
    lens.position.copy(H).add(tmpV); lens.rotation.set(0, -(1 - k) * 1.25, -(1 - k) * 0.3);
    // Rubíes y fondo.
    (M.jewel.uniforms.uEmis!.value as THREE.Vector3).set(RUBY.r, RUBY.g, RUBY.b).lerp(tmpV2.set(accent.r, accent.g, accent.b), 0.35).multiplyScalar(0.5 + 0.7 * g + p.flash * 0.6);
    (bg.material.uniforms.uC!.value as THREE.Color).copy(accent); bg.material.uniforms.uG!.value = g; bg.material.uniforms.uCold!.value = cold;

    root.updateMatrixWorld(true);
    const hv = p.hover;
    for (let e = 0; e < 2; e++) { tmpV.copy(sunLocal[e]!).applyMatrix4(head.matrixWorld); glowSet(e, tmpV, accent, 0.6 * g * (1 - cold * 0.9) * (hv === 'eye' ? 1.5 : 1) * (1 - 0.7 * Math.max(0, (e === 0 ? f.uL : f.uR) - 0.5) * 2), 0.2 * (e === 0 ? p.pupilL : p.pupilR)); }
    for (let e = 0; e < 2; e++) { tmpV.copy(jewelPos[7 + e]!).applyMatrix4(head.matrixWorld); glowSet(2 + e, tmpV, tmpC.copy(RUBY).lerp(accent, 0.4).multiplyScalar(2.4), (0.25 + 0.25 * g + (hv === 'crown' ? 0.5 : 0)) * (1 - cold * 0.7), 0.16); }
    tmpV.set(0, 0, 0.03).applyMatrix4(heart.matrixWorld);
    glowSet(4, tmpV, accent, (0.25 + 0.35 * p.breath * g + p.level * 0.6 + (hv === 'chest' ? 0.4 : 0)) * (1 - cold * 0.6) + cold * 0.15 * (0.5 + 0.5 * Math.sin(p.t * 1.2)), 0.34);
    tmpV.set(0, MOUTH_Y - f.jaw * 0.03, zM(0, MOUTH_Y) + 0.03).applyMatrix4(head.matrixWorld); glowSet(5, tmpV, accent, f.jaw * 0.7 * g + (p.chime >= 0 ? Math.exp(-p.chime * 2.5) * 0.6 : 0), 0.32);
    for (let j = 0; j < 7; j++) { tmpV.copy(jewelPos[j]!).applyMatrix4(head.matrixWorld); glowSet(6 + j, tmpV, tmpC.copy(RUBY).lerp(accent, 0.3).multiplyScalar(2.4), (0.18 + 0.12 * g + (j === 0 && p.beat < 0.5 ? 0.25 * (1 - p.beat * 2) : 0) + (hv === 'movement' ? 0.2 : 0)) * (1 - cold * 0.85), j === 0 ? 0.1 : 0.07); }
    tmpV.set(0.04, 0.05, 0.04).applyMatrix4(lens.matrixWorld); glowSet(13, tmpV, WHITE, Math.max(0, Math.min(1, k)) * 0.25 + p.flash * 0.2, 0.12);
    for (const n of ['position', 'aCol', 'aSize']) (glow.pts.geometry.attributes[n] as THREE.BufferAttribute).needsUpdate = true;
    head.getWorldPosition(headWorld);
    gl.clearDepth(); // solo dentro del recuadro (scissor del anfitrión): las capas de debajo no tapan al avatar; el color no se toca
    gl.render(scene, cam);
  }

  // ── Entrada: el anfitrión llama a hit()/faceScreen(); la capa no escucha nada.
  const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
  function hit(x: number, y: number): Zone | null {
    if (!ready) return null;
    ndc.set((x / W) * 2 - 1, -(y / Hh) * 2 + 1); ray.setFromCamera(ndc, cam);
    for (const m of proxies) if (ray.intersectObject(m, false).length) return m.userData.zone as Zone;
    return null;
  }
  const faceScreen = (): { x: number; y: number } => { tmpV.copy(headWorld).project(cam); return { x: (tmpV.x * 0.5 + 0.5) * W, y: (-tmpV.y * 0.5 + 0.5) * Hh }; };

  // Estado global del renderer que se toca en render() y en el montaje, y se deja como estaba.
  const canvasSize = new THREE.Vector2(), prevViewport = new THREE.Vector4(), prevScissor = new THREE.Vector4();
  const withViewport = (x: number, y: number, w: number, h: number, fn: () => void): void => {
    gl.getViewport(prevViewport); gl.getScissor(prevScissor);
    const prevScissorTest = gl.getScissorTest(), prevTone = gl.toneMapping;
    try { gl.setViewport(x, y, w, h); gl.setScissor(x, y, w, h); gl.setScissorTest(true); gl.toneMapping = THREE.NoToneMapping; fn(); }
    finally { gl.toneMapping = prevTone; gl.setViewport(prevViewport); gl.setScissor(prevScissor); gl.setScissorTest(prevScissorTest); }
  };

  // Montaje por etapas: cada una en su propia tarea, luego compilación asíncrona de shaders.
  const nextTask = (): Promise<void> => new Promise((r) => setTimeout(r, 0));
  const readyP = (async () => {
    await nextTask();
    for (const s of steps) { if (disposed) return; s(); await nextTask(); }
    fit();
    // compileAsync crea los programas de forma síncrona: el tone mapping entra en su clave y debe ser el de render().
    const prevTone = gl.toneMapping; let compiled: Promise<unknown>;
    try { gl.toneMapping = THREE.NoToneMapping; compiled = gl.compileAsync(scene, cam); } finally { gl.toneMapping = prevTone; }
    await compiled.catch(() => undefined);
    // Precalentado: sube la geometría a la GPU por grupos, cada uno en su propia tarea. Con el scissor a cero
    // no se pinta nada en el lienzo compartido, pero buffers y programas ya quedan listos.
    const groups = [body, head, halo]; const vis = groups.map((g0) => g0.visible);
    for (let i = 0; i < groups.length && !disposed; i++) { groups.forEach((g0, j) => { g0.visible = j === i; }); withViewport(0, 0, 0, 0, () => gl.render(scene, cam)); await nextTask(); }
    groups.forEach((g0, j) => { g0.visible = vis[j]!; });
    ready = true;
  })();

  const setTheme = (t: AvatarTheme): void => { glow.mat.uniforms.uGain!.value = transparent && t === 'light' ? 0.5 : 1; };
  setTheme(opts.theme ?? 'dark');

  return {
    ready: readyP, brain, hit, faceScreen, externalGaze: () => external, setTheme,
    setState: (s) => brain.setState(s),
    setAudioLevel: (l) => { brain.voice = Math.max(0, Math.min(1, l || 0)); },
    setViseme: (v) => { brain.viseme = v && VIS.has(v.toUpperCase()) ? (v.toUpperCase() as Viseme) : null; },
    lookAt: (x, y) => { external = true; brain.cursor.x = Math.max(-1, Math.min(1, x)); brain.cursor.y = Math.max(-1, Math.min(1, y)); brain.cursor.active = true; },
    notify: (e) => brain.notify(e),
    setReducedMotion: (on) => { brain.reduced = on; brain.microGestures = !on; },
    resize: (w, h, dpr) => { W = Math.max(1, w); Hh = Math.max(1, h); pr = dpr; fit(); },
    render: (dt: number, vp: AvatarViewport) => {
      if (!ready || disposed || vp.width <= 0 || vp.height <= 0) return;
      if (Math.round(vp.width) !== Math.round(W) || Math.round(vp.height) !== Math.round(Hh)) { W = vp.width; Hh = vp.height; fit(); }
      if (brain.state !== 'speaking' && brain.state !== 'listening') brain.voice = 0;
      const pose = brain.update(dt);
      gl.getSize(canvasSize);
      // Viewport en px CSS con origen abajo a la izquierda (convención de Three); el recuadro llega con origen arriba.
      withViewport(vp.x, canvasSize.y - vp.y - vp.height, vp.width, vp.height, () => draw(pose));
    },
    dispose: () => {
      disposed = true;
      const mats = new Set<THREE.Material>();
      scene.traverse((o) => { const m = o as THREE.Mesh; if (m.geometry) m.geometry.dispose(); if (m.material) (Array.isArray(m.material) ? m.material : [m.material]).forEach((x) => mats.add(x)); if (o instanceof THREE.InstancedMesh) o.dispose(); });
      mats.forEach((m) => m.dispose());
    },
  };
}
