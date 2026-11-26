// Geometría procedural del Relojero: todo se construye por código, sin modelos ni texturas externas.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

// ── Cabeza: elipsoide de la caja y contorno de la esfera (la «cara»). Unidades locales de la cabeza.
export const RX = 0.7, RY = 0.95, RZ = 0.72, Z0 = -0.05;
export const FX = 0.6, FY = 0.82, FYC = -0.04;
export const EYE_X = 0.25, EYE_Y = 0.0, MOUTH_Y = -0.47, EYE_R = 0.13;

export function zE(x: number, y: number): number {
  const q = 1 - (x / RX) ** 2 - (y / RY) ** 2;
  return Z0 + RZ * Math.sqrt(Math.max(0.0004, q));
}
/** Línea de la ceja: separa el esmalte (abajo) del cristal sobre el movimiento (arriba). */
export const yb = (x: number): number => 0.22 + 0.05 * (1 - (x / FX) ** 2);
const halfH = (x: number): number => FY * Math.sqrt(Math.max(0, 1 - (x / FX) ** 2));
export const yTop = (x: number): number => FYC + halfH(x);
export const yBot = (x: number): number => FYC - halfH(x);
const g = (v: number): number => Math.exp(-v * v);

/** Relieve de la cara sobre el elipsoide: nariz aquilina, arco ciliar, cuencas, pómulos, mentón. */
export function relief(x: number, y: number): number {
  const ax = Math.abs(x);
  const ss = (a: number, b: number, v: number): number => { const t = Math.min(1, Math.max(0, (v - a) / (b - a))); return t * t * (3 - 2 * t); };
  return 0.06 * g(x / (0.04 + 0.03 * ss(0.1, -0.28, y))) * ss(0.17, 0.05, y) * ss(-0.33, -0.2, y)   // dorso de la nariz, se ensancha hacia la punta
    + 0.03 * g(Math.hypot(x / 0.055, (y + 0.25) / 0.05))                                              // punta
    + 0.012 * g(Math.hypot((ax - 0.055) / 0.03, (y + 0.28) / 0.03))                                   // aletas
    + 0.045 * g((y - 0.13) / 0.045) * Math.exp(-((x / 0.42) ** 4)) * (1 - 0.6 * g(x / 0.05))          // arco ciliar
    - 0.045 * g(Math.hypot((ax - EYE_X) / 0.19, (y - EYE_Y + 0.01) / 0.17))                           // cuencas
    + 0.035 * g(Math.hypot((ax - 0.35) / 0.11, (y + 0.13) / 0.09))                                    // pómulos
    - 0.028 * g(Math.hypot((ax - 0.3) / 0.1, (y + 0.4) / 0.12))                                       // mejilla hundida
    - 0.012 * g(x / 0.025) * g((y + 0.36) / 0.035)                                                    // surco nasolabial central
    - 0.02 * Math.exp(-((x / 0.18) ** 4) - ((y - MOUTH_Y) / 0.065) ** 2)                              // asiento de la boca
    + 0.04 * g(Math.hypot(x / 0.13, (y + 0.71) / 0.09))                                               // mentón
    + 0.015 * g((ax - 0.42) / 0.08) * g((y + 0.5) / 0.15);                                            // ángulo de la mandíbula
}

/** Superficie del esmalte de la cara, con nariz, arco ciliar, cuencas, pómulos y mentón. */
export function zM(x: number, y: number): number {
  return zE(x, y) + 0.03 + relief(x, y);
}

/** x donde la línea de la ceja corta el contorno de la esfera. */
export const XW = (() => { let a = 0, b = FX; for (let i = 0; i < 40; i++) { const m = (a + b) / 2; if (yTop(m) > yb(m)) a = m; else b = m; } return a; })();

/** Malla en rejilla sobre una región x∈[-xm,xm], y∈[lo(x),hi(x)], z = f(x,y). */
export function patch(xm: number, lo: (x: number) => number, hi: (x: number) => number, f: (x: number, y: number) => number, nu = 48, nv = 40, ao?: (x: number, y: number) => number): THREE.BufferGeometry {
  const pos: number[] = [], uv: number[] = [], idx: number[] = [], col: number[] = [];
  for (let i = 0; i <= nu; i++) {
    const s = -1 + (2 * i) / nu, x = xm * Math.sin((s * Math.PI) / 2);
    const a = lo(x), b = Math.max(a + 1e-4, hi(x));
    for (let j = 0; j <= nv; j++) { const y = a + ((b - a) * j) / nv; pos.push(x, y, f(x, y)); uv.push(i / nu, j / nv); if (ao) { const k = ao(x, y); col.push(k, k * 0.985, k * 0.96); } }
  }
  for (let i = 0; i < nu; i++) for (let j = 0; j < nv; j++) {
    const a = i * (nv + 1) + j, b = a + nv + 1;
    idx.push(a, b, a + 1, b, b + 1, a + 1);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  if (ao) geo.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
  geo.setIndex(idx); geo.computeVertexNormals();
  return geo;
}

/** Caja de latón: elipsoide sin la parte frontal que ocupa la esfera. */
export function caseGeo(): THREE.BufferGeometry {
  const s = new THREE.SphereGeometry(1, 56, 40).toNonIndexed();
  const p = s.attributes.position!, n = s.attributes.normal!, keep: number[] = [], kn: number[] = [];
  for (let i = 0; i < p.count; i += 3) {
    let cx = 0, cy = 0, cz = 0;
    for (let k = 0; k < 3; k++) { cx += p.getX(i + k) * RX; cy += p.getY(i + k) * RY; cz += p.getZ(i + k) * RZ + Z0; }
    cx /= 3; cy /= 3; cz /= 3;
    if (cz > 0.05 && (cx / (FX * 0.985)) ** 2 + ((cy - FYC) / (FY * 0.985)) ** 2 < 1) continue;
    for (let k = 0; k < 3; k++) {
      keep.push(p.getX(i + k) * RX, p.getY(i + k) * RY, p.getZ(i + k) * RZ + Z0);
      const nx = n.getX(i + k) / RX, ny = n.getY(i + k) / RY, nz = n.getZ(i + k) / RZ, l = Math.hypot(nx, ny, nz);
      kn.push(nx / l, ny / l, nz / l);
    }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(keep, 3));
  geo.setAttribute('normal', new THREE.Float32BufferAttribute(kn, 3));
  return geo;
}

/** Tubo a lo largo de una curva, con estrías opcionales (canto moleteado de un bisel). */
export function tube(pts: THREE.Vector3[], r: number, closed: boolean, flutes = 0, seg = 160): THREE.BufferGeometry {
  const curve = new THREE.CatmullRomCurve3(pts, closed, 'centripetal');
  const geo = new THREE.TubeGeometry(curve, seg, r, 10, closed);
  if (flutes) {
    const p = geo.attributes.position!, n = geo.attributes.normal!, uv = geo.attributes.uv!;
    for (let i = 0; i < p.count; i++) {
      const k = Math.sign(Math.sin(uv.getX(i) * flutes * Math.PI * 2)) * r * 0.12;
      p.setXYZ(i, p.getX(i) + n.getX(i) * k, p.getY(i) + n.getY(i) * k, p.getZ(i) + n.getZ(i) * k);
    }
    geo.computeVertexNormals();
  }
  return geo;
}

// ── Mecanismo: todas las piezas móviles en UNA geometría. Cada vértice lleva su pivote y sus tasas
//    (tren, volante, áncora); el shader de vértices las hace girar. Un solo draw call.
export interface MechPart { geo: THREE.BufferGeometry; piv: [number, number]; rate: [number, number, number]; color: THREE.Color }

export function tag(geo: THREE.BufferGeometry, piv: [number, number], rate: [number, number, number], color: THREE.Color | number): THREE.BufferGeometry {
  const g0 = geo.index ? geo.toNonIndexed() : geo;
  const n = g0.attributes.position!.count, c = new THREE.Color(color);
  const ap = new Float32Array(n * 2), ar = new Float32Array(n * 3), ac = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) { ap.set(piv, i * 2); ar.set(rate, i * 3); ac.set([c.r, c.g, c.b], i * 3); }
  g0.setAttribute('aPiv', new THREE.BufferAttribute(ap, 2));
  g0.setAttribute('aRate', new THREE.BufferAttribute(ar, 3));
  g0.setAttribute('color', new THREE.BufferAttribute(ac, 3));
  if (!g0.attributes.uv) g0.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(n * 2), 2));
  if (!g0.attributes.normal) g0.computeVertexNormals();
  return g0;
}

export function merge(list: THREE.BufferGeometry[]): THREE.BufferGeometry {
  const norm = list.map((x) => {
    const y = x.index ? x.toNonIndexed() : x;
    for (const k of Object.keys(y.attributes)) if (!['position', 'normal', 'uv', 'aPiv', 'aRate', 'color'].includes(k)) y.deleteAttribute(k);
    if (!y.attributes.uv) y.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(y.attributes.position!.count * 2), 2));
    return y;
  });
  return mergeGeometries(norm, false)!;
}

/** Rueda con dientes, radios y agujero central. style: 'gear' | 'escape' (dientes de pala) | 'rim' (sin dientes). */
export function wheel(r: number, teeth: number, o: { spokes?: number; depth?: number; style?: 'gear' | 'escape' | 'rim'; rim?: number; hub?: number } = {}): THREE.BufferGeometry {
  const style = o.style ?? 'gear', th = style === 'escape' ? r * 0.22 : Math.min(r * 0.1, 0.012), rr = r - (style === 'rim' ? 0 : th);
  const sh = new THREE.Shape();
  if (style === 'rim' || teeth === 0) sh.absarc(0, 0, r, 0, Math.PI * 2, false);
  else for (let k = 0; k < teeth; k++) {
    const a = (k / teeth) * Math.PI * 2, w = (Math.PI * 2) / teeth;
    const pts: [number, number][] = style === 'escape'
      ? [[rr, a], [r, a + w * 0.12], [r * 0.97, a + w * 0.32], [rr, a + w * 0.4]]
      : [[rr, a], [r, a + w * 0.18], [r, a + w * 0.42], [rr, a + w * 0.6]];
    pts.forEach(([rad, ang], i) => { const x = Math.cos(ang) * rad, y = Math.sin(ang) * rad; if (k === 0 && i === 0) sh.moveTo(x, y); else sh.lineTo(x, y); });
  }
  const sp = o.spokes ?? 4, rimW = o.rim ?? Math.max(0.012, r * 0.16), hub = o.hub ?? Math.max(0.018, r * 0.2);
  if (sp > 0) {
    const inner = rr - rimW, half = Math.max(0.006, r * 0.06); // media anchura de cada radio
    if (inner > hub + 0.01) for (let k = 0; k < sp; k++) {
      const a0 = (k / sp) * Math.PI * 2, a1 = ((k + 1) / sp) * Math.PI * 2;
      const h = new THREE.Path();
      h.absarc(0, 0, inner, a0 + half / inner, a1 - half / inner, false);
      h.absarc(0, 0, hub + 0.004, a1 - half / (hub + 0.004), a0 + half / (hub + 0.004), true);
      h.closePath(); sh.holes.push(h);
    }
  }
  const hole = new THREE.Path(); hole.absarc(0, 0, Math.min(0.008, hub * 0.4), 0, Math.PI * 2, true); sh.holes.push(hole);
  const d = o.depth ?? 0.012;
  return new THREE.ExtrudeGeometry(sh, { depth: d, bevelEnabled: true, bevelThickness: 0.0025, bevelSize: 0.002, bevelSegments: 1, curveSegments: style === 'rim' ? 48 : 4 });
}

export function spiral(r0: number, r1: number, turns: number, w: number): THREE.BufferGeometry {
  const pts: THREE.Vector3[] = [];
  const N = Math.round(turns * 48);
  for (let i = 0; i <= N; i++) { const u = i / N, a = u * turns * Math.PI * 2, r = r0 + (r1 - r0) * u; pts.push(new THREE.Vector3(Math.cos(a) * r, Math.sin(a) * r, 0)); }
  return new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), N, w, 4, false);
}

/** Aguja Breguet («pomme» hueca cerca de la punta), a lo largo de +x desde el pivote. */
export function breguetHand(len: number): THREE.BufferGeometry {
  const parts: THREE.Shape[] = [];
  const canon = new THREE.Shape(); canon.absarc(0, 0, 0.028, 0, Math.PI * 2, false);
  const h0 = new THREE.Path(); h0.absarc(0, 0, 0.009, 0, Math.PI * 2, true); canon.holes.push(h0); parts.push(canon);
  const pr = 0.03, px = len * 0.72;
  const blade = new THREE.Shape();
  blade.moveTo(0.012, 0.014); blade.lineTo(px - pr * 0.8, 0.007); blade.lineTo(px - pr * 0.8, -0.007); blade.lineTo(0.012, -0.014); blade.closePath(); parts.push(blade);
  const pomme = new THREE.Shape(); pomme.absarc(px, 0, pr, 0, Math.PI * 2, false);
  const h1 = new THREE.Path(); h1.absarc(px + 0.004, 0, pr * 0.58, 0, Math.PI * 2, true); pomme.holes.push(h1); parts.push(pomme);
  const tip = new THREE.Shape(); tip.moveTo(px + pr * 0.8, 0.008); tip.lineTo(len, 0); tip.lineTo(px + pr * 0.8, -0.008); tip.closePath(); parts.push(tip);
  const geos = parts.map((s) => new THREE.ExtrudeGeometry(s, { depth: 0.008, bevelEnabled: true, bevelThickness: 0.002, bevelSize: 0.0015, bevelSegments: 1, curveSegments: 16 }));
  return merge(geos);
}

/** Rectángulo redondeado como contorno 3D (para el bisel de la boca). */
export function roundRectPts(w: number, h: number, r: number, z: (x: number, y: number) => number, cy: number): THREE.Vector3[] {
  const pts: THREE.Vector3[] = [];
  const cs: [number, number, number][] = [[w / 2 - r, h / 2 - r, 0], [-w / 2 + r, h / 2 - r, Math.PI / 2], [-w / 2 + r, -h / 2 + r, Math.PI], [w / 2 - r, -h / 2 + r, Math.PI * 1.5]];
  for (const [cx, cyy, a0] of cs) for (let i = 0; i <= 6; i++) { const a = a0 + (i / 6) * (Math.PI / 2), x = cx + Math.cos(a) * r, y = cyy + Math.sin(a) * r + cy; pts.push(new THREE.Vector3(x, y, z(x, y))); }
  return pts;
}

/** Contorno de los labios (rosa: arco de Cupido arriba, curva amplia abajo). */
export const LIP_W = 0.165;
export const lipUp = (x: number): number => MOUTH_Y + 0.05 * Math.pow(Math.max(0, 1 - (x / LIP_W) ** 2), 0.6) - 0.012 * Math.exp(-((x / 0.03) ** 2));
export const lipLo = (x: number): number => MOUTH_Y - 0.055 * Math.pow(Math.max(0, 1 - (x / LIP_W) ** 2), 0.75);
