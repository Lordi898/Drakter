// Escultura procedural de Ascuario: SDF analíticos proyectados sobre esferas (normales por gradiente,
// oclusión horneada), tubos con perfil propio y piezas fusionadas para gastar pocas llamadas de dibujo.
// Atributos comunes: position, normal, aMat (pieza, sin interpolar), aAux (ao, peso suave, peso de flexión), aUv.
import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

export const MAT = { scale: 0, horn: 1, tooth: 2, gold: 3, membrane: 6, lidUp: 7, lidLow: 8, chain: 9 } as const;
type SDF = (x: number, y: number, z: number) => number;
export type V3 = [number, number, number];

// ---------- primitivas ----------
const L = (x: number, y: number, z: number): number => Math.sqrt(x * x + y * y + z * z);
const cl = (v: number, a: number, b: number): number => Math.min(b, Math.max(a, v));
const ss = (a: number, b: number, x: number): number => { const t = cl((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
export const ell = (x: number, y: number, z: number, a: number, b: number, c: number): number => {
  const k0 = L(x / a, y / b, z / c), k1 = L(x / (a * a), y / (b * b), z / (c * c));
  return k1 < 1e-9 ? -Math.min(a, b, c) : (k0 * (k0 - 1)) / k1;
};
const sph = (x: number, y: number, z: number, r: number): number => L(x, y, z) - r;
const cap = (px: number, py: number, pz: number, a: V3, b: V3, r: number): number => {
  const pax = px - a[0], pay = py - a[1], paz = pz - a[2], bax = b[0] - a[0], bay = b[1] - a[1], baz = b[2] - a[2];
  const h = cl((pax * bax + pay * bay + paz * baz) / (bax * bax + bay * bay + baz * baz), 0, 1);
  return L(pax - bax * h, pay - bay * h, paz - baz * h) - r;
};
/** Cono redondeado (Íñigo Quílez). */
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

// ---------- anatomía (espacio local de la cabeza: +z hocico, +y arriba, origen en el cráneo) ----------
export const mouthY = (z: number): number => -0.26 + 0.05 * z;
export const EYE: V3 = [0.41, 0.18, 0.44]; // ojo izquierdo del personaje (+x); el derecho es el espejo
export const EYE_R = 0.135;
export const HINGE: V3 = [0, -0.26, -0.14];
export const NOSTRIL: V3 = [0.095, 0.0, 1.31];
export const CORNER: V3 = [0.43, mouthY(0.02), 0.02]; // comisura (lado +x)

// Cabeza noble: cráneo amplio, hocico corto y afilado, arcos superciliares y pómulos marcados, labios definidos.
export const headSDF: SDF = (x, y, z) => {
  const ax = Math.abs(x);
  let d = ell(x, y - 0.14, z + 0.1, 0.64, 0.56, 0.8); // cráneo
  d = smin(d, rcone(x, (y + 0.02) / 0.74, z, [0, 0.08, 0.25], [0, -0.06, 1.26], 0.46, 0.16) * 0.74, 0.26); // hocico afilado
  d = smin(d, cap(x, y, z, [0, 0.5, 0.0], [0, 0.14, 1.2], 0.08), 0.16); // caballete nasal hasta la punta
  d = smin(d, cap(ax, y, z, [0.1, 0.38, 0.62], [0.5, 0.36, 0.24], 0.085), 0.1); // arco superciliar
  d = smin(d, cap(ax, y, z, [0.44, 0.0, 0.45], [0.58, 0.04, -0.25], 0.1), 0.12); // arco cigomático (pómulo)
  d = smax(d, -ell(ax - 0.47, y + 0.17, z - 0.62, 0.12, 0.08, 0.22), 0.08); // hueco bajo el pómulo
  d = smin(d, ell(ax - 0.56, y + 0.02, z + 0.35, 0.12, 0.2, 0.3), 0.14); // carrillo posterior
  d = smin(d, ell(ax - 0.09, y + 0.01, z - 1.2, 0.065, 0.055, 0.1), 0.07); // aletas nasales discretas
  d = smin(d, rcone(ax, y, z, [0.42, mouthY(-0.02) + 0.03, -0.02], [0.13, mouthY(1.2) + 0.025, 1.2], 0.038, 0.03), 0.04); // labio superior
  d = smax(d, -sph(ax - NOSTRIL[0], y - NOSTRIL[1], z - NOSTRIL[2], 0.03), 0.025); // fosas
  d = smax(d, -sph(ax - EYE[0], y - EYE[1], z - EYE[2], EYE_R + 0.03), 0.045); // cuencas
  d = smax(d, mouthY(z) - y, 0.03); // corte de la boca
  return d;
};

export const jawSDF: SDF = (x, y, z) => {
  const ax = Math.abs(x);
  let d = rcone(x, (y + 0.39) / 0.5, z, [0, 0, -0.12], [0, 0.3, 1.12], 0.46, 0.15) * 0.5;
  d = smin(d, ell(x, y + 0.38, z - 0.95, 0.12, 0.08, 0.15), 0.1); // mentón
  d = smin(d, ell(ax - 0.38, y + 0.36, z + 0.05, 0.12, 0.13, 0.28), 0.12); // ángulo mandibular
  d = smax(d, y - mouthY(z), 0.03);
  return d;
};

export const chestSDF: SDF = (x, y, z) => {
  let d = ell(x, y + 2.75, z + 0.75, 1.75, 0.92, 0.98);
  d = smin(d, cap(x, y, z, [0, -2.7, -0.75], [0, -1.9, -0.55], 0.8), 0.4);
  d = smin(d, ell(Math.abs(x) - 0.55, y + 2.45, z + 0.35, 0.58, 0.45, 0.48), 0.3); // pectorales
  return d;
};

// ---------- utilidades de geometría ----------
function grad(f: SDF, x: number, y: number, z: number): V3 {
  const e = 0.0015;
  const nx = f(x + e, y, z) - f(x - e, y, z), ny = f(x, y + e, z) - f(x, y - e, z), nz = f(x, y, z + e) - f(x, y, z - e), l = L(nx, ny, nz) || 1;
  return [nx / l, ny / l, nz / l];
}
function aoAt(f: SDF, x: number, y: number, z: number, n: V3): number {
  let occ = 0, w = 1;
  for (let i = 1; i <= 5; i++) { const h = 0.035 * i; occ += (h - f(x + n[0] * h, y + n[1] * h, z + n[2] * h)) * w; w *= 0.6; }
  return cl(1 - 2.6 * occ, 0.15, 1);
}

interface Extra { mat: number; aux?: (p: V3, n: V3) => [number, number]; }
function withAttrs(g: THREE.BufferGeometry, mat: number, aoW: (i: number) => [number, number, number], uv?: (i: number) => [number, number]): THREE.BufferGeometry {
  const n = g.getAttribute('position').count;
  const m = new Float32Array(n).fill(mat), a = new Float32Array(n * 3), u = new Float32Array(n * 2);
  const guv = g.getAttribute('uv');
  for (let i = 0; i < n; i++) {
    const [o, w, b] = aoW(i); a[i * 3] = o; a[i * 3 + 1] = w; a[i * 3 + 2] = b;
    const q = uv ? uv(i) : guv ? [guv.getX(i), guv.getY(i)] : [0, 0]; u[i * 2] = q[0]!; u[i * 2 + 1] = q[1]!;
  }
  g.setAttribute('aMat', new THREE.BufferAttribute(m, 1)); g.setAttribute('aAux', new THREE.BufferAttribute(a, 3)); g.setAttribute('aUv', new THREE.BufferAttribute(u, 2));
  g.deleteAttribute('uv');
  return g;
}

/** Proyecta una esfera sobre la superficie de un SDF estrellado respecto a c. */
function project(f: SDF, c: V3, ws: number, hs: number, ex: Extra): THREE.BufferGeometry {
  const g = new THREE.SphereGeometry(1, ws, hs);
  const pos = g.getAttribute('position') as THREE.BufferAttribute, nor = g.getAttribute('normal') as THREE.BufferAttribute;
  const ao: number[] = [], wt: number[] = [];
  for (let i = 0; i < pos.count; i++) {
    const dx = pos.getX(i), dy = pos.getY(i), dz = pos.getZ(i);
    let t = 4, prev = 4;
    for (let k = 0; k < 220; k++) {
      const d = f(c[0] + dx * t, c[1] + dy * t, c[2] + dz * t);
      if (d < 0) { let a = t, b = prev; for (let j = 0; j < 14; j++) { const m = (a + b) / 2; if (f(c[0] + dx * m, c[1] + dy * m, c[2] + dz * m) < 0) a = m; else b = m; } t = (a + b) / 2; break; }
      if (d < 1e-4) break;
      prev = t; t -= Math.max(d * 0.75, 0.002);
      if (t <= 0) { t = 0.01; break; }
    }
    const x = c[0] + dx * t, y = c[1] + dy * t, z = c[2] + dz * t, n = grad(f, x, y, z);
    pos.setXYZ(i, x, y, z); nor.setXYZ(i, n[0], n[1], n[2]);
    ao.push(aoAt(f, x, y, z, n)); wt.push(ex.aux ? ex.aux([x, y, z], n)[0] : 0);
  }
  return withAttrs(g, ex.mat, (i) => [ao[i]!, wt[i]!, 0], (i) => [0, 0]);
}

/** Tubo con perfil elíptico variable; sin costura duplicada (normales suaves). La costura queda en ang = 0 (espalda con ref = +z). */
function tube(pts: V3[], segs: number, radial: number, rad: (u: number) => [number, number], mat: number, ref: V3 = [0, 0, 1], bend?: (u: number) => number, aux?: (u: number, a: number) => number): THREE.BufferGeometry {
  const curve = new THREE.CatmullRomCurve3(pts.map((p) => new THREE.Vector3(...p)), false, 'centripetal');
  const P: number[] = [], A: number[] = [], U: number[] = [], I: number[] = [];
  const T = new THREE.Vector3(), N = new THREE.Vector3(), B = new THREE.Vector3(), R = new THREE.Vector3(...ref), C = new THREE.Vector3();
  for (let i = 0; i <= segs; i++) {
    const u = i / segs; curve.getPointAt(u, C); curve.getTangentAt(u, T);
    N.copy(R).addScaledVector(T, -R.dot(T)).normalize(); B.crossVectors(T, N).normalize();
    const [rf, rs] = rad(u);
    for (let j = 0; j < radial; j++) {
      const a = (j / radial) * Math.PI * 2, ca = -Math.cos(a), sa = Math.sin(a); // a=0 → espalda (−N)
      P.push(C.x + N.x * ca * rf + B.x * sa * rs, C.y + N.y * ca * rf + B.y * sa * rs, C.z + N.z * ca * rf + B.z * sa * rs);
      A.push(1, aux ? aux(u, a) : 0, bend ? bend(u) : 0); U.push(u, j / radial);
    }
  }
  for (let i = 0; i < segs; i++) for (let j = 0; j < radial; j++) {
    const a = i * radial + j, b = i * radial + ((j + 1) % radial), c = a + radial, d = b + radial;
    I.push(a, c, b, b, c, d);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3)); g.setIndex(I); g.computeVertexNormals();
  g.setAttribute('aMat', new THREE.BufferAttribute(new Float32Array(P.length / 3).fill(mat), 1));
  g.setAttribute('aAux', new THREE.Float32BufferAttribute(A, 3)); g.setAttribute('aUv', new THREE.Float32BufferAttribute(U, 2));
  return g;
}

/** Cono (diente, púa) de la base b hacia la dirección d. */
function spike(b: V3, d: V3, r: number, h: number, mat: number, bend = 0, seg = 7): THREE.BufferGeometry {
  const g = new THREE.ConeGeometry(r, h, seg, 2, true);
  g.translate(0, h / 2, 0);
  const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), new THREE.Vector3(...d).normalize());
  g.applyQuaternion(q); g.translate(...b);
  const pos = g.getAttribute('position');
  return withAttrs(g, mat, () => [1, 0, bend], (i) => { const p = new THREE.Vector3(pos.getX(i), pos.getY(i), pos.getZ(i)); return [cl(p.distanceTo(new THREE.Vector3(...b)) / h, 0, 1), 0]; });
}

function prim(g: THREE.BufferGeometry, mat: number, bend = 0): THREE.BufferGeometry { return withAttrs(g, mat, () => [1, 0, bend]); }
function edgeX(f: SDF, y: number, z: number): number { let x = 0; while (x < 1.2 && f(x, y, z) < 0) x += 0.004; return x; }

// ---------- piezas ----------
export function buildHead(): THREE.BufferGeometry {
  const parts: THREE.BufferGeometry[] = [];
  // Piel: peso suave = carne de la boca (cara inferior plana junto al corte).
  parts.push(project(headSDF, [0, 0.08, 0.28], 176, 128, { mat: MAT.scale, aux: (p, n) => [ss(-0.86, -0.97, n[1]) * ss(0.012, 0.0, p[1] - mouthY(p[2])) * ss(-0.15, 0.1, p[2]), 0] }));
  // Cuernos principales y secundarios.
  for (const s of [1, -1]) {
    parts.push(tube([[s * 0.26, 0.36, -0.2], [s * 0.42, 0.62, -0.55], [s * 0.56, 0.82, -1.0], [s * 0.64, 0.9, -1.45], [s * 0.66, 1.02, -1.85], [s * 0.6, 1.22, -2.12]], 56, 12,
      (u) => { const r = 0.13 * Math.pow(1 - u, 0.85) + 0.008; return [r, r * 0.92]; }, MAT.horn, [0, 1, 0]));
    parts.push(tube([[s * 0.5, 0.02, -0.4], [s * 0.72, 0.0, -0.8], [s * 0.85, 0.06, -1.1], [s * 0.9, 0.16, -1.28]], 24, 9,
      (u) => { const r = 0.075 * Math.pow(1 - u, 0.8) + 0.006; return [r, r]; }, MAT.horn, [0, 1, 0]));
    // Dientes superiores: hilera interior y un colmillo que asoma.
    for (let z = 0.26; z < 1.2; z += 0.075) {
      const y = mouthY(z) + 0.012, x = edgeX(headSDF, y + 0.02, z), canine = Math.abs(z - 0.98) < 0.04;
      parts.push(spike([s * (canine ? x - 0.025 : x - 0.07), y + 0.02, z], [canine ? s * 0.08 : 0, -1, canine ? 0.12 : 0], canine ? 0.03 : 0.018, canine ? 0.13 : 0.035, MAT.tooth));
    }
  }
  // Cresta: púas cortas sobre la línea media.
  for (let i = 0; i < 5; i++) { const u = i / 4; parts.push(spike([0, 0.57 - u * 0.12, -0.12 - u * 0.6], [0, 0.6, -1], 0.045 - u * 0.012, 0.15 - u * 0.04, MAT.horn)); }
  const g = mergeGeometries(parts)!; parts.forEach((p) => p.dispose());
  return g;
}

export function buildJaw(): THREE.BufferGeometry {
  const parts: THREE.BufferGeometry[] = [];
  parts.push(project(jawSDF, [0, -0.36, 0.5], 120, 72, { mat: MAT.scale, aux: (p, n) => [ss(0.86, 0.97, n[1]) * ss(-0.012, 0.0, p[1] - mouthY(p[2])) * ss(-0.15, 0.1, p[2]), 0] }));
  for (const s of [1, -1]) for (let z = 0.3; z < 1.12; z += 0.085) {
    const y = mouthY(z) - 0.01, x = edgeX(jawSDF, y - 0.02, z) - 0.06;
    parts.push(spike([s * x, y - 0.02, z], [0, 1, 0.05], 0.02, 0.055, MAT.tooth));
  }
  const g = mergeGeometries(parts)!; parts.forEach((p) => p.dispose());
  g.translate(-HINGE[0], -HINGE[1], -HINGE[2]);
  return g;
}

/** Cuello + pecho + púas dorsales + cadena de cargo con medallón. Espacio del mundo. */
export const NECK: V3[] = [[0, -2.45, -0.8], [0, -2.0, -0.55], [0, -1.55, -0.46], [0, -1.2, -0.52], [0, -0.92, -0.62]];
export const PIVOT: V3 = [0, -1.0, -0.58];
export const MEDAL: V3 = [0, -2.32, 0.46];
export const ANCHOR: V3 = [-0.5, -1.98, 0.42]; // donde engancha la cadena del monóculo
function onChest(x: number, y: number, out = 0.035): V3 { let z = 1.5; while (z > -1 && chestSDF(x, y, z) > 0) z -= 0.005; const n = grad(chestSDF, x, y, z); return [x + n[0] * out, y + n[1] * out, z + n[2] * out]; }

export function buildBody(): THREE.BufferGeometry {
  const parts: THREE.BufferGeometry[] = [];
  const bend = (u: number): number => ss(0.5, 1.0, u);
  parts.push(tube(NECK, 72, 40, (u) => [0.86 - 0.2 * u, 1.04 - 0.34 * u], MAT.scale, [0, 0, 1], bend, (u, a) => ss(0.35, 0.8, -Math.cos(a)) * ss(0.02, 0.12, u)));
  parts.push(project(chestSDF, [0, -2.55, -0.6], 110, 64, { mat: MAT.scale, aux: (p) => [ss(0.1, 0.5, p[2] + 0.2) * ss(0.7, 0.2, Math.abs(p[0])) * ss(-2.9, -2.2, p[1]) * 0.6, 0] }));
  // Púas dorsales a lo largo de la nuca.
  const curve = new THREE.CatmullRomCurve3(NECK.map((p) => new THREE.Vector3(...p)), false, 'centripetal');
  for (let u = 0.12; u < 0.9; u += 0.075) {
    const c = curve.getPointAt(u), t = curve.getTangentAt(u), back = new THREE.Vector3(0, 0, -1).addScaledVector(t, t.z).normalize(), rf = 0.86 - 0.2 * u;
    const b = c.clone().addScaledVector(back, rf * 0.92), d = back.clone().multiplyScalar(0.8).addScaledVector(t, 0.6);
    parts.push(spike([b.x, b.y, b.z], [d.x, d.y, d.z], 0.07 - 0.03 * u, 0.24 - 0.1 * u, MAT.horn, bend(u)));
  }
  // Cadena de cargo: eslabones entrelazados, repartidos por longitud de arco sobre el pecho.
  const cpts: THREE.Vector3[] = [];
  for (let i = 0; i <= 60; i++) { const s = i / 60 * 2 - 1; cpts.push(new THREE.Vector3(...onChest(s * 1.05, -2.36 + 0.42 * s * s, 0.03))); }
  const cc = new THREE.CatmullRomCurve3(cpts), nl = 78;
  for (let i = 0; i <= nl; i++) {
    const u = i / nl, p = cc.getPointAt(u), tg = cc.getTangentAt(u);
    if (Math.abs(p.x) < 0.2) continue;
    const g = new THREE.TorusGeometry(0.036, 0.011, 5, 10); g.scale(1.35, 1, 1);
    if (i % 2) g.rotateX(Math.PI / 2);
    g.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(1, 0, 0), tg)); g.translate(p.x, p.y, p.z);
    parts.push(prim(g, MAT.gold));
  }
  // Medallón: disco de oro con bisel; la gema va aparte.
  const disc = new THREE.CylinderGeometry(0.21, 0.23, 0.05, 32, 1); disc.rotateX(Math.PI / 2); disc.rotateX(-0.25); disc.translate(MEDAL[0], MEDAL[1], MEDAL[2] - 0.02);
  const rim = new THREE.TorusGeometry(0.215, 0.022, 8, 40); rim.rotateX(-0.25); rim.translate(MEDAL[0], MEDAL[1], MEDAL[2] + 0.01);
  parts.push(prim(disc, MAT.gold), prim(rim, MAT.gold));
  const hook = new THREE.TorusGeometry(0.035, 0.01, 6, 12); hook.translate(...ANCHOR); parts.push(prim(hook, MAT.gold));
  const g = mergeGeometries(parts)!; parts.forEach((p) => p.dispose());
  return g;
}

export function buildEye(): THREE.BufferGeometry { return prim(new THREE.SphereGeometry(EYE_R, 40, 28), 0); }
export function buildLidUp(): THREE.BufferGeometry { return withAttrs(new THREE.SphereGeometry(EYE_R + 0.008, 32, 10, 0, Math.PI * 2, 0, Math.PI / 2), MAT.lidUp, () => [1, 0, 0]); }
export function buildLidLow(): THREE.BufferGeometry { return withAttrs(new THREE.SphereGeometry(EYE_R + 0.006, 32, 6, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2), MAT.lidLow, () => [1, 0, 0]); }

/** Ceja: placa alargada sobre el arco y tres púas largas que barren hacia atrás (cejas de sabio). Pivote en el extremo interior; +x hacia fuera. */
export function buildBrow(): THREE.BufferGeometry {
  const g = new THREE.SphereGeometry(1, 28, 12); const p = g.getAttribute('position');
  for (let i = 0; i < p.count; i++) {
    let x = p.getX(i), y = p.getY(i), z = p.getZ(i); const u = (x + 1) / 2, taper = 1 - 0.55 * u * u;
    x = u * 0.46; y = y * 0.04 * taper + 0.035 * Math.sin(u * Math.PI) - 0.03 * u; z = z * 0.085 * taper + 0.03 * (1 - u);
    p.setXYZ(i, x, y, z);
  }
  g.computeVertexNormals();
  const parts = [withAttrs(g, MAT.scale, () => [1, 1, 0])];
  const sp: [V3, V3[], number][] = [
    [[0.3, 0.03, 0], [[0.36, 0.02, 0], [0.54, 0.06, -0.1], [0.72, 0.1, -0.26], [0.88, 0.16, -0.44]], 0.026],
    [[0.24, 0.05, 0.02], [[0.3, 0.04, 0.02], [0.46, 0.1, -0.08], [0.6, 0.16, -0.22], [0.72, 0.24, -0.36]], 0.022],
    [[0.34, 0.0, -0.02], [[0.4, 0.0, -0.02], [0.58, 0.02, -0.12], [0.74, 0.06, -0.26], [0.84, 0.12, -0.36]], 0.02],
  ];
  for (const [, pts, r] of sp) parts.push(tube(pts, 20, 6, (u) => { const k = r * (1 - u) + 0.003; return [k, k]; }, MAT.horn, [0, 1, 0]));
  const m = mergeGeometries(parts)!; parts.forEach((q) => q.dispose());
  return m;
}

/** Aleta: abanico de varillas con membrana festoneada. Local: varillas en el plano XY, hacia +X. */
export function buildFrill(): THREE.BufferGeometry {
  const parts: THREE.BufferGeometry[] = [];
  const ang = [-0.75, -0.3, 0.12, 0.52, 0.9], len = [0.42, 0.62, 0.72, 0.62, 0.4];
  const tip = (i: number, f = 1): V3 => [Math.cos(ang[i]!) * len[i]! * f, Math.sin(ang[i]!) * len[i]! * f, 0];
  for (let i = 0; i < ang.length; i++) parts.push(spike([0, 0, 0], tip(i), 0.022, len[i]! * 1.02, MAT.horn, 0, 6));
  // Membrana: tiras entre varillas, con el borde hundido a media distancia.
  const P: number[] = [], U: number[] = [], I: number[] = [], R = 12, C = 6;
  for (let i = 0; i < ang.length - 1; i++) {
    const base = P.length / 3;
    for (let r = 0; r <= R; r++) for (let c = 0; c <= C; c++) {
      const v = r / R, w = c / C, a = ang[i]! + (ang[i + 1]! - ang[i]!) * w, l = (len[i]! + (len[i + 1]! - len[i]!) * w) * (1 - 0.28 * Math.sin(Math.PI * w)) * 0.98;
      const rr = l * v; P.push(Math.cos(a) * rr, Math.sin(a) * rr, 0.03 * Math.sin(Math.PI * w) * v); U.push(v, w);
    }
    for (let r = 0; r < R; r++) for (let c = 0; c < C; c++) { const a = base + r * (C + 1) + c, b = a + 1, d = a + C + 1, e = d + 1; I.push(a, d, b, b, d, e); }
  }
  const m = new THREE.BufferGeometry(); m.setAttribute('position', new THREE.Float32BufferAttribute(P, 3)); m.setIndex(I); m.computeVertexNormals();
  parts.push(withAttrs(m, MAT.membrane, () => [1, 0, 0], (i) => [U[i * 2]!, U[i * 2 + 1]!]));
  const g = mergeGeometries(parts)!; parts.forEach((p) => p.dispose());
  return g;
}

export function buildMonocle(): THREE.BufferGeometry {
  const ring = new THREE.TorusGeometry(0.165, 0.016, 10, 56);
  const lip = new THREE.TorusGeometry(0.155, 0.007, 6, 56); lip.translate(0, 0, -0.012);
  const loop = new THREE.TorusGeometry(0.024, 0.008, 6, 12); loop.rotateY(Math.PI / 2); loop.translate(0.117, -0.117, 0);
  const g = mergeGeometries([prim(ring, MAT.gold), prim(lip, MAT.gold), prim(loop, MAT.gold)])!;
  return g;
}

/** Cadena del monóculo: tubo fino reconstruido cada fotograma en un búfer fijo (sin asignaciones). */
export class Chain {
  readonly geo = new THREE.BufferGeometry();
  private pos: Float32Array; private nor: Float32Array;
  private readonly S = 40; private readonly Rd = 4;
  constructor() {
    const n = (this.S + 1) * this.Rd; this.pos = new Float32Array(n * 3); this.nor = new Float32Array(n * 3);
    const uv = new Float32Array(n * 2), I: number[] = [];
    for (let i = 0; i <= this.S; i++) for (let j = 0; j < this.Rd; j++) { uv[(i * this.Rd + j) * 2] = i / this.S; uv[(i * this.Rd + j) * 2 + 1] = j / this.Rd; }
    for (let i = 0; i < this.S; i++) for (let j = 0; j < this.Rd; j++) { const a = i * this.Rd + j, b = i * this.Rd + ((j + 1) % this.Rd); I.push(a, a + this.Rd, b, b, a + this.Rd, b + this.Rd); }
    this.geo.setAttribute('position', new THREE.BufferAttribute(this.pos, 3).setUsage(THREE.DynamicDrawUsage));
    this.geo.setAttribute('normal', new THREE.BufferAttribute(this.nor, 3).setUsage(THREE.DynamicDrawUsage));
    this.geo.setAttribute('aUv', new THREE.BufferAttribute(uv, 2)); this.geo.setIndex(I);
    this.geo.setAttribute('aMat', new THREE.BufferAttribute(new Float32Array(n).fill(MAT.chain), 1));
    this.geo.setAttribute('aAux', new THREE.BufferAttribute(new Float32Array(n * 3).fill(1), 3));
    this.geo.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 10);
  }
  /** Curva cuadrática de a a b con control c. */
  update(a: THREE.Vector3, c: THREE.Vector3, b: THREE.Vector3, r = 0.011): void {
    const S = this.S, Rd = this.Rd, p = this.pos, nn = this.nor;
    let px = 0, py = 0, pz = 0;
    for (let i = 0; i <= S; i++) {
      const t = i / S, u = 1 - t;
      const x = u * u * a.x + 2 * u * t * c.x + t * t * b.x, y = u * u * a.y + 2 * u * t * c.y + t * t * b.y, z = u * u * a.z + 2 * u * t * c.z + t * t * b.z;
      // Tangente analítica y marco con referencia +z.
      let tx = 2 * u * (c.x - a.x) + 2 * t * (b.x - c.x), ty = 2 * u * (c.y - a.y) + 2 * t * (b.y - c.y), tz = 2 * u * (c.z - a.z) + 2 * t * (b.z - c.z);
      const tl = Math.hypot(tx, ty, tz) || 1; tx /= tl; ty /= tl; tz /= tl;
      let nx = -tz * tx, ny = -tz * ty, nz = 1 - tz * tz; const nl = Math.hypot(nx, ny, nz) || 1; nx /= nl; ny /= nl; nz /= nl;
      const bx = ty * nz - tz * ny, by = tz * nx - tx * nz, bz = tx * ny - ty * nx;
      for (let j = 0; j < Rd; j++) {
        const an = (j / Rd) * Math.PI * 2, ca = Math.cos(an), sa = Math.sin(an), k = (i * Rd + j) * 3;
        const ox = nx * ca + bx * sa, oy = ny * ca + by * sa, oz = nz * ca + bz * sa;
        p[k] = x + ox * r; p[k + 1] = y + oy * r; p[k + 2] = z + oz * r; nn[k] = ox; nn[k + 1] = oy; nn[k + 2] = oz;
      }
      px = x; py = y; pz = z;
    }
    void px; void py; void pz;
    this.geo.attributes.position!.needsUpdate = true; this.geo.attributes.normal!.needsUpdate = true;
  }
}
