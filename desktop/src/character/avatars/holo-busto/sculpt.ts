// Escultura de Holo-busto: cabeza humana masculina madura con proporciones clásicas, hecha con SDF analíticos
// proyectados sobre una esfera (polo en la cara para concentrar resolución), normales por gradiente, oclusión horneada
// y pesos de rig por vértice. Atributos: position, normal, aMat, aAux (ao, pelo, ceja), aRig (ceja, mandíbula, boca, comisura interior), aUv.
import * as THREE from 'three';
import { mergeGeometries, mergeVertices } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

export const MAT = { skin: 0, eye: 1, lidUp: 7, lidLow: 8, body: 2 } as const;
type SDF = (x: number, y: number, z: number) => number;
export type V3 = [number, number, number];

const L = (x: number, y: number, z: number): number => Math.sqrt(x * x + y * y + z * z);
const cl = (v: number, a: number, b: number): number => Math.min(b, Math.max(a, v));
export const ss = (a: number, b: number, x: number): number => { const t = cl((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
const ell = (x: number, y: number, z: number, a: number, b: number, c: number): number => {
  const k0 = L(x / a, y / b, z / c), k1 = L(x / (a * a), y / (b * b), z / (c * c));
  return k1 < 1e-9 ? -Math.min(a, b, c) : (k0 * (k0 - 1)) / k1;
};
const sph = (x: number, y: number, z: number, r: number): number => L(x, y, z) - r;
const cap = (px: number, py: number, pz: number, a: V3, b: V3, r: number): number => {
  const pax = px - a[0], pay = py - a[1], paz = pz - a[2], bax = b[0] - a[0], bay = b[1] - a[1], baz = b[2] - a[2];
  const h = cl((pax * bax + pay * bay + paz * baz) / (bax * bax + bay * bay + baz * baz), 0, 1);
  return L(pax - bax * h, pay - bay * h, paz - baz * h) - r;
};
const rcone = (px: number, py: number, pz: number, a: V3, b: V3, r1: number, r2: number): number => {
  const bx = b[0] - a[0], by = b[1] - a[1], bz = b[2] - a[2], l2 = bx * bx + by * by + bz * bz, rr = r1 - r2, a2 = l2 - rr * rr, il2 = 1 / l2;
  const pax = px - a[0], pay = py - a[1], paz = pz - a[2], y = pax * bx + pay * by + paz * bz, z = y - l2;
  const xx = pax * l2 - bx * y, xy = pay * l2 - by * y, xz = paz * l2 - bz * y, x2 = xx * xx + xy * xy + xz * xz, y2 = y * y * l2, z2 = z * z * l2;
  const k = Math.sign(rr) * rr * rr * x2;
  if (Math.sign(z) * a2 * z2 > k) return Math.sqrt(x2 + z2) * il2 - r2;
  if (Math.sign(y) * a2 * y2 < k) return Math.sqrt(x2 + y2) * il2 - r1;
  return (Math.sqrt(x2 * a2 * il2) + y * rr) * il2 - r1;
};
const smin = (a: number, b: number, k: number): number => { const h = Math.max(k - Math.abs(a - b), 0) / k; return Math.min(a, b) - h * h * k * 0.25; };
const smax = (a: number, b: number, k: number): number => -smin(-a, -b, k);

// ---------- anatomía (espacio local de la cabeza: +z cara, +y arriba; altura de la cabeza ≈ 2) ----------
export const EYE: V3 = [0.29, 0.04, 0.74]; // ojo izquierdo del personaje (+x)
export const EYE_R = 0.118;
export const MOUTH_Y = -0.598;
export const HINGE: V3 = [0, -0.1, -0.06]; // articulación temporomandibular
export const browY = (ax: number): number => 0.205 + 0.055 * Math.sin(Math.PI * cl((ax - 0.07) / 0.5, 0, 1)) - 0.03 * ss(0.4, 0.58, ax);
/** Línea del nacimiento del pelo (altura mínima del pelo en función de x, z). */
const hairline = (ax: number, z: number): number => -0.32 + 1.0 * ss(-0.6, 0.62, z) + 0.09 * Math.exp(-(((ax - 0.42) / 0.13) ** 2)) * ss(0.25, 0.6, z);

function skull(x: number, y: number, z: number): number {
  const ax = Math.abs(x);
  let d = ell(x, y - 0.22, z + 0.05, 0.72, 0.82, 0.92); // cráneo
  d = smin(d, ell(x, y - 0.38, z - 0.38, 0.6, 0.48, 0.52), 0.22); // frente
  d = smin(d, ell(x, y + 0.32, z - 0.25, 0.6, 0.55, 0.62), 0.28); // mandíbula y carrillos
  d = smin(d, ell(ax - 0.35, y + 0.22, z - 0.6, 0.26, 0.25, 0.27), 0.2); // carrillos llenos (grasa malar)
  d = smin(d, ell(ax - 0.47, y + 0.08, z - 0.54, 0.2, 0.12, 0.24), 0.12); // pómulos
  d = smin(d, cap(ax, y, z, [0.5, -0.1, 0.4], [0.72, -0.06, 0.0], 0.06), 0.12); // arco cigomático
  d = smax(d, -ell(ax - 0.74, y - 0.3, z - 0.42, 0.09, 0.17, 0.22), 0.12); // sienes algo hundidas (edad)
  d = smin(d, cap(ax, y, z, [0.07, 0.19, 0.9], [0.3, 0.215, 0.86], 0.052), 0.12); d = smin(d, cap(ax, y, z, [0.3, 0.215, 0.86], [0.52, 0.16, 0.7], 0.045), 0.12); // arco superciliar
  d = smin(d, sph(x, y - 0.15, z - 0.93, 0.07), 0.1); // glabela
  d = smax(d, -ell(ax - 0.29, y - 0.03, z - 0.975, 0.17, 0.1, 0.1), 0.08); // órbitas (cuenco somero)
  { // abertura almendrada: elipsoide inclinado (canto exterior algo caído); la piel tapa el resto del globo
    const ey = y - 0.04 + 0.05 * (ax - 0.29);
    d = smax(d, -ell(ax - 0.292, ey, z - 0.9, 0.145, 0.064, 0.13), 0.016);
  }
  // Nariz: caballete estrecho, punta definida, aletas en ala fundidas con la punta, fosas hacia abajo.
  d = smin(d, rcone(x / 0.8, y, z, [0, 0.12, 0.9], [0, -0.26, 1.15], 0.05, 0.062), 0.08);
  d = smin(d, ell(x, y + 0.295, z - 1.125, 0.068, 0.066, 0.07), 0.07);
  d = smin(d, ell(ax - 0.092, y + 0.348, z - 0.97, 0.042, 0.042, 0.075), 0.12);
  d = smin(d, ell(x, y + 0.383, z - 1.075, 0.028, 0.028, 0.055), 0.04); // columela
  d = smax(d, -ell(ax - 0.05, y + 0.412, z - 1.04, 0.022, 0.01, 0.03), 0.016);
  // Boca: arco dentario discreto, filtro, labios con arco de Cupido, surco mentolabial.
  d = smin(d, ell(x, y + 0.55, z - 0.72, 0.32, 0.22, 0.27), 0.15);
  d = smax(d, -ell(x, y + 0.48, z - 1.005, 0.026, 0.05, 0.03), 0.025);
  const bow = 0.014 * Math.exp(-((x / 0.045) ** 2)) - 0.008 * Math.exp(-(((ax - 0.07) / 0.035) ** 2)) - 0.012 * ss(0.12, 0.23, ax);
  d = smin(d, ell(x, y + 0.567 - bow, z - 0.965, 0.225, 0.034, 0.06), 0.045); // labio superior
  d = smin(d, ell(x, y + 0.638, z - 0.945, 0.19, 0.046, 0.062), 0.05); // labio inferior
  d = smax(d, -ell(x, y - MOUTH_Y + 0.01 * ss(0.12, 0.23, ax), z - 0.99, 0.23, 0.016, 0.08), 0.028);
  d = smax(d, -ell(x, y + 0.725, z - 0.955, 0.12, 0.02, 0.035), 0.05);
  d = smax(d, -cap(ax, y, z, [0.13, -0.36, 0.99], [0.265, -0.65, 0.89], 0.014), 0.035); // surco nasogeniano marcado
  // Mentón cuadrado y línea mandibular limpia.
  d = smin(d, ell(x, y + 0.84, z - 0.78, 0.2, 0.15, 0.16), 0.2);
  d = smin(d, cap(ax, y, z, [0.12, -0.86, 0.66], [0.56, -0.56, 0.0], 0.09), 0.24);
  // Orejas: pabellón aplanado con concha.
  d = smin(d, ell(ax - 0.71, y, z + 0.05, 0.058, 0.235, 0.135), 0.05);
  d = smax(d, -ell(ax - 0.765, y + 0.02, z + 0.035, 0.025, 0.13, 0.07), 0.03);
  return d;
}
function hair(x: number, y: number, z: number): number {
  const ax = Math.abs(x);
  let h = ell(x, y - 0.27, z + 0.07, 0.775, 0.895, 0.985);
  h = smin(h, ell(x + 0.14, y - 0.86, z - 0.38, 0.5, 0.17, 0.42), 0.18); // volumen peinado hacia el lado largo de la raya
  h = smin(h, ell(x - 0.42, y - 0.72, z - 0.3, 0.3, 0.14, 0.36), 0.16);
  h = smax(h, hairline(ax, z) - y, 0.1);
  h = smax(h, -cap(x, y, z, [0.3, 0.99, 0.5], [0.33, 1.07, -0.25], 0.013), 0.016); // raya
  // Surcos del peinado: mechones que barren hacia atrás y hacia el lado (relieve real para que la luz los dibuje).
  const comb = (x - 0.31) * 30 + Math.sin(z * 3.1 + x * 2) * 1.6 + Math.sin(y * 5 + z * 2.3) * 0.9;
  h += 0.009 * Math.abs(Math.sin(comb)) * ss(-0.3, 0.2, y);
  return h;
}
export const headSDF: SDF = (x, y, z) => smin(skull(x, y, z), hair(x, y, z), 0.04);

// Cuello, trapecios, clavículas y hombros (espacio del mundo; la cabeza va en HEAD).
export const HEAD: V3 = [0, 0.42, 0.0];
export const PIVOT: V3 = [0, -0.45, -0.12];
/** Cuello corto que entra en un jersey de cuello vuelto, bajo una chaqueta abierta en V. Espacio del mundo. */
export const lapelW = (y: number): number => 0.22 + Math.max(0, -1.12 - y) * 0.42; // media anchura de la V de la chaqueta
export const bodySDF: SDF = (x, y, z) => {
  const ax = Math.abs(x);
  let d = cap(x / 1.06, y, z, [0, -0.2, -0.1], [0, -0.8, -0.12], 0.46); // cuello (solo asoma un palmo)
  d = smin(d, cap(ax, y, z, [0.44, 0.28, -0.16], [0.12, -0.7, 0.24], 0.075), 0.12); // esternocleidomastoideo
  const rN = Math.hypot(x / 1.05, (z + 0.06) / 0.97);
  // Cuello alto: tubo ceñido con el doblez arriba.
  d = smin(d, cap(x / 1.05, y, z, [0, -0.66, -0.09], [0, -1.3, -0.08], 0.52), 0.04);
  d = smin(d, Math.hypot(rN - 0.53, (y + 0.7) / 1.1) - 0.06, 0.05);
  // Chaqueta: hombros con caída y torso; la V de las solapas la dibuja el shader.
  let j = ell(x, y + 1.95, z + 0.1, 1.45, 0.8, 0.7);
  j = smin(j, cap(ax, y, z, [0.55, -1.15, -0.2], [1.2, -1.47, -0.1], 0.2), 0.3);
  j = smin(j, ell(ax - 1.2, y + 1.64, z + 0.04, 0.3, 0.36, 0.38), 0.22);
  d = smin(d, j, 0.1);
  return d;
};

// ---------- utilidades ----------
function grad(f: SDF, x: number, y: number, z: number): V3 {
  const e = 0.0012;
  const nx = f(x + e, y, z) - f(x - e, y, z), ny = f(x, y + e, z) - f(x, y - e, z), nz = f(x, y, z + e) - f(x, y, z - e), l = L(nx, ny, nz) || 1;
  return [nx / l, ny / l, nz / l];
}
function aoAt(f: SDF, x: number, y: number, z: number, n: V3): number {
  let occ = 0, w = 1;
  for (let i = 1; i <= 5; i++) { const h = 0.03 * i; occ += (h - f(x + n[0] * h, y + n[1] * h, z + n[2] * h)) * w; w *= 0.6; }
  return cl(1 - 3 * occ, 0.1, 1);
}
type Attrs = { mat: number; aux: (p: V3) => V3; rig: (p: V3) => [number, number, number, number] };
function setAttrs(g: THREE.BufferGeometry, mat: number, aux: (i: number) => V3, rig: (i: number) => [number, number, number, number]): THREE.BufferGeometry {
  const n = g.getAttribute('position').count, guv = g.getAttribute('uv');
  const m = new Float32Array(n).fill(mat), a = new Float32Array(n * 3), r = new Float32Array(n * 4), u = new Float32Array(n * 2);
  for (let i = 0; i < n; i++) {
    const q = aux(i), w = rig(i); a.set(q, i * 3); r.set(w, i * 4);
    if (guv) { u[i * 2] = guv.getX(i); u[i * 2 + 1] = guv.getY(i); }
  }
  g.setAttribute('aMat', new THREE.BufferAttribute(m, 1)); g.setAttribute('aAux', new THREE.BufferAttribute(a, 3));
  g.setAttribute('aRig', new THREE.BufferAttribute(r, 4)); g.setAttribute('aUv', new THREE.BufferAttribute(u, 2));
  if (guv) g.deleteAttribute('uv');
  return g;
}
/**
 * Malla sobre la superficie de un SDF: icosaedro subdividido (densidad desplazada hacia +z si faceForward),
 * proyección radial desde c y relajación (suavizado tangencial + vuelta a la superficie con Newton) para que
 * los vértices se repartan bien incluso en surcos y concavidades.
 */
function project(f: SDF, c: V3, detail: number, at: Attrs, faceForward = true, relax = 10): THREE.BufferGeometry {
  const base = new THREE.IcosahedronGeometry(1, detail); base.deleteAttribute('normal'); base.deleteAttribute('uv');
  const g = mergeVertices(base); base.dispose();
  const pos = g.getAttribute('position') as THREE.BufferAttribute, n = pos.count, P = pos.array as Float32Array;
  // 1) Proyección radial (con el reparto angular comprimido hacia la cara).
  for (let i = 0; i < n; i++) {
    let dx = P[i * 3]!, dy = P[i * 3 + 1]!, dz = P[i * 3 + 2]!;
    if (faceForward) {
      const th = Math.acos(cl(dz, -1, 1)), th2 = Math.PI * Math.pow(th / Math.PI, 1.28), r = Math.hypot(dx, dy) || 1;
      dx = (dx / r) * Math.sin(th2); dy = (dy / r) * Math.sin(th2); dz = Math.cos(th2);
    }
    let t = 3.2, prev = 3.2;
    for (let k = 0; k < 260; k++) {
      const d = f(c[0] + dx * t, c[1] + dy * t, c[2] + dz * t);
      if (d < 0) { let a = t, b = prev; for (let j = 0; j < 14; j++) { const m = (a + b) / 2; if (f(c[0] + dx * m, c[1] + dy * m, c[2] + dz * m) < 0) a = m; else b = m; } t = (a + b) / 2; break; }
      if (d < 5e-5) break;
      prev = t; t -= Math.max(d * 0.7, 0.0015);
      if (t <= 0) { t = 0.01; break; }
    }
    P[i * 3] = c[0] + dx * t; P[i * 3 + 1] = c[1] + dy * t; P[i * 3 + 2] = c[2] + dz * t;
  }
  // 2) Vecindad (CSR).
  const idx = g.getIndex()!.array, deg = new Uint32Array(n);
  for (let k = 0; k < idx.length; k++) deg[idx[k]!]! += 2;
  const off = new Uint32Array(n + 1); for (let i = 0; i < n; i++) off[i + 1] = off[i]! + deg[i]!;
  const nb = new Uint32Array(off[n]!), fill = off.slice(0, n);
  for (let k = 0; k < idx.length; k += 3) { const a = idx[k]!, b = idx[k + 1]!, d = idx[k + 2]!; nb[fill[a]!++] = b; nb[fill[a]!++] = d; nb[fill[b]!++] = a; nb[fill[b]!++] = d; nb[fill[d]!++] = a; nb[fill[d]!++] = b; }
  // 3) Relajación.
  const Q = new Float32Array(n * 3);
  for (let it = 0; it < relax; it++) {
    for (let i = 0; i < n; i++) {
      let sx = 0, sy = 0, sz = 0; const o = off[i]!, e = off[i + 1]!;
      for (let k = o; k < e; k++) { const j = nb[k]!; sx += P[j * 3]!; sy += P[j * 3 + 1]!; sz += P[j * 3 + 2]!; }
      const m = e - o, x = P[i * 3]!, y = P[i * 3 + 1]!, z = P[i * 3 + 2]!;
      let mx = sx / m - x, my = sy / m - y, mz = sz / m - z;
      const gn = grad(f, x, y, z), dn = mx * gn[0] + my * gn[1] + mz * gn[2];
      mx -= gn[0] * dn; my -= gn[1] * dn; mz -= gn[2] * dn;
      Q[i * 3] = x + mx * 0.55; Q[i * 3 + 1] = y + my * 0.55; Q[i * 3 + 2] = z + mz * 0.55;
    }
    for (let i = 0; i < n; i++) {
      let x = Q[i * 3]!, y = Q[i * 3 + 1]!, z = Q[i * 3 + 2]!;
      for (let s = 0; s < 2; s++) { const d = f(x, y, z), gn = grad(f, x, y, z); x -= gn[0] * d; y -= gn[1] * d; z -= gn[2] * d; }
      P[i * 3] = x; P[i * 3 + 1] = y; P[i * 3 + 2] = z;
    }
  }
  // 4) Normales, oclusión y atributos.
  const N = new Float32Array(n * 3), AUX: V3[] = [], RIG: [number, number, number, number][] = [];
  for (let i = 0; i < n; i++) {
    const x = P[i * 3]!, y = P[i * 3 + 1]!, z = P[i * 3 + 2]!, nn = grad(f, x, y, z);
    N.set(nn, i * 3);
    const p: V3 = [x, y, z], ax = at.aux(p); ax[0] = aoAt(f, x, y, z, nn) * ax[0];
    AUX.push(ax); RIG.push(at.rig(p));
  }
  g.setAttribute('normal', new THREE.BufferAttribute(N, 3));
  pos.needsUpdate = true;
  return setAttrs(g, at.mat, (i) => AUX[i]!, (i) => RIG[i]!);
}

// ---------- piezas ----------
export function buildHead(): THREE.BufferGeometry {
  return project(headSDF, [0, -0.25, 0.15], 52, {
    mat: MAT.skin,
    aux: ([x, y, z]) => {
      const ax = Math.abs(x);
      const hairW = ss(0.012, -0.01, hair(x, y, z) - skull(x, y, z));
      const bd = Math.abs(y - browY(ax)) / (0.034 - 0.012 * ss(0.3, 0.56, ax));
      const brow = (1 - ss(0.75, 1.15, bd)) * ss(0.06, 0.11, ax) * ss(0.6, 0.52, ax) * ss(0.55, 0.7, z);
      return [1, hairW, brow];
    },
    rig: ([x, y, z]) => {
      const ax = Math.abs(x);
      const browW = Math.exp(-(((y - 0.24) / 0.15) ** 2)) * ss(0.02, 0.1, ax) * ss(0.7, 0.5, ax) * ss(0.45, 0.72, z) * ss(0.5, 0.35, y);
      // Mandíbula: bajo la hendidura de la boca, con el límite subiendo hacia la articulación.
      const toEar = ss(0.22, 0.62, ax);
      const yb = MOUTH_Y + (HINGE[1] - MOUTH_Y + 0.02) * toEar;
      let jawW = ss(yb + 0.006, yb - 0.035 - 0.08 * toEar, y) * ss(-0.35, 0.05, z) * (1 - ss(0.75, 0.9, ax));
      const lipNear = Math.exp(-(((y + 0.635) / 0.07) ** 2)) * ss(0.6, 0.85, z);
      const lens = Math.sqrt(Math.max(0, 1 - (ax / 0.25) ** 2));
      jawW *= 1 - lipNear * (1 - lens) * 0.9; // apertura en lente: las comisuras siguen unidas
      const mouthW = Math.exp(-((x / 0.36) ** 2 + ((y - MOUTH_Y) / 0.16) ** 2 + ((z - 0.98) / 0.22) ** 2));
      // Interior de la boca: el fondo de la hendidura (se hunde y se oscurece al abrir).
      const inner = Math.exp(-(((y - MOUTH_Y) / 0.02) ** 2)) * Math.sqrt(Math.max(0, 1 - (ax / 0.235) ** 2)) * ss(0.88, 0.96, z);
      return [browW, jawW, mouthW, inner];
    },
  });
}

/** Cuello y hombros: tubo para el cuello (se dobla con la cabeza) fundido con el torso proyectado. */
/** Peso de chaqueta (1) frente a jersey/cuello (0), para que el shader dibuje solapas y canalé. */
function jacketW(x: number, y: number, z: number): number {
  const rN = Math.hypot(x / 1.05, (z + 0.06) / 0.97);
  return ss(0.56, 0.64, rN) * ss(-1.0, -1.15, y) + ss(-1.35, -1.6, y) * 0; void z;
}
export function buildBody(): THREE.BufferGeometry {
  const g = project(bodySDF, [0, -1.3, -0.1], 40, {
    mat: MAT.body,
    aux: () => [1, 0, 0],
    rig: ([x, y, z]) => [ss(-0.75, -0.3, y), jacketW(x, y, z), 0, 0], // x = peso de flexión con la cabeza
  }, false, 8);
  return g;
}
export function buildEye(): THREE.BufferGeometry { return setAttrs(new THREE.SphereGeometry(EYE_R, 40, 28), MAT.eye, () => [1, 0, 0], () => [0, 0, 0, 0]); }
export function buildLidUp(): THREE.BufferGeometry { return setAttrs(new THREE.SphereGeometry(EYE_R + 0.005, 36, 12, 0, Math.PI * 2, 0, Math.PI / 2), MAT.lidUp, () => [1, 0, 0], () => [0, 0, 0, 0]); }
export function buildLidLow(): THREE.BufferGeometry { return setAttrs(new THREE.SphereGeometry(EYE_R + 0.004, 36, 8, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2), MAT.lidLow, () => [1, 0, 0], () => [0, 0, 0, 0]); }
/**
 * Pelo de verdad: hebras de luz que nacen en la zona de pelo y crecen sobre la superficie siguiendo el peinado
 * (desde la raya hacia los lados y atrás). aAux = (posición a lo largo, semilla, plata en las sienes).
 */
export function buildHair(): THREE.BufferGeometry {
  let seed = 12345; const rnd = (): number => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
  const P: number[] = [], A: number[] = [], I: number[] = [];
  const N = 1900, STEPS = 7, partX = 0.31;
  let made = 0, tries = 0;
  while (made < N && tries < N * 40) {
    tries++;
    // Punto aleatorio en la esfera de la cabeza → proyectar al pelo.
    const th = Math.acos(1 - 2 * rnd()), ph = rnd() * Math.PI * 2;
    let x = Math.sin(th) * Math.cos(ph) * 1.4, y = Math.cos(th) * 1.4 + 0.25, z = Math.sin(th) * Math.sin(ph) * 1.4;
    for (let k = 0; k < 40; k++) { const dd = headSDF(x, y, z), g = grad(headSDF, x, y, z); x -= g[0] * dd; y -= g[1] * dd; z -= g[2] * dd; if (Math.abs(dd) < 1e-4) break; }
    if (hair(x, y, z) - skull(x, y, z) > -0.005) continue; // solo donde manda el pelo
    if (y < hairline(Math.abs(x), z) + 0.04) continue;
    const silver = ss(0.5, 0.66, Math.abs(x)) * ss(0.55, 0.2, y) + ss(-0.1, -0.45, z) * ss(0.4, 0.0, y) * 0.6;
    const base = P.length / 3, len = 0.028 + rnd() * 0.02;
    for (let st = 0; st <= STEPS; st++) {
      const g = grad(headSDF, x, y, z);
      P.push(x + g[0] * 0.008, y + g[1] * 0.008, z + g[2] * 0.008); A.push(st / STEPS, rnd(), Math.min(1, silver));
      if (st === STEPS) break;
      // Campo de peinado: se aleja de la raya hacia el lado y hacia atrás; delante sube un poco.
      const side = Math.sign(x - partX) || 1;
      let fx = side * (0.55 + 0.3 * Math.abs(x - partX)), fy = 0.15 * ss(0.2, 0.8, z) - 0.25 * ss(0.3, -0.4, y), fz = -1.0 + 0.4 * ss(0.5, 0.9, z);
      fx += (rnd() - 0.5) * 0.25; fz += (rnd() - 0.5) * 0.2;
      const dn = fx * g[0] + fy * g[1] + fz * g[2]; fx -= g[0] * dn; fy -= g[1] * dn; fz -= g[2] * dn;
      const fl = Math.hypot(fx, fy, fz) || 1; x += (fx / fl) * len; y += (fy / fl) * len; z += (fz / fl) * len;
      for (let k = 0; k < 3; k++) { const dd = headSDF(x, y, z), g2 = grad(headSDF, x, y, z); x -= g2[0] * dd; y -= g2[1] * dd; z -= g2[2] * dd; }
      I.push(base + st, base + st + 1);
    }
    made++;
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3)); g.setIndex(I);
  const n = P.length / 3;
  g.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
  g.setAttribute('aMat', new THREE.BufferAttribute(new Float32Array(n), 1)); g.setAttribute('aAux', new THREE.Float32BufferAttribute(A, 3));
  g.setAttribute('aRig', new THREE.BufferAttribute(new Float32Array(n * 4), 4)); g.setAttribute('aUv', new THREE.BufferAttribute(new Float32Array(n * 2), 2));
  return g;
}
export function buildAll(): Record<string, THREE.BufferGeometry> {
  return { head: buildHead(), body: buildBody(), eye: buildEye(), lidUp: buildLidUp(), lidLow: buildLidLow(), hair: buildHair() };
}
void mergeGeometries;
