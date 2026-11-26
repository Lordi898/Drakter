// Busto procedural de Drakter (v2): un SDF (cabeza, cuello, torso) sobre el que se trazan miles de hebras.
// Todo se genera por código y con semilla fija: no hay modelos ni texturas de terceros.
// El tejido es incremental (createWeaver().step(ms)): se reparte en fotogramas y nunca bloquea el hilo principal.
// Ejes: +x derecha de pantalla, +y arriba, +z hacia el espectador. La cabeza mide ~2,3 unidades.

export const NP = 8; // puntos por hebra
export const MAXS = 11800; // hebras reservadas
export const EYE = { x: 0.31, y: 0.09, z: 0.64, r: 0.2, halfW: 0.185, up: 0.068, low: 0.05 };
export const PIVOT = [0, -0.95, -0.15] as const; // base del cráneo: gira la cabeza
export const KNOT = [0, -1.72, 0.3] as const; // la brasa del nudo
export const MOUTH = [0, -0.61, 0.84] as const;
export const K = { SKIN: 0, EYE: 1, GLOW: 2, EMBER: 3, LIP: 4, TEETH: 5 } as const;

export interface Weave {
  strands: number; done: boolean; ms: number;
  pos: Float32Array; dir: Float32Array; nrm: Float32Array;
  a: Float32Array; // lado, t, semilla, periferia
  b: Float32Array; // pesoCabeza, pesoMandíbula, soltura, ganancia
  c: Uint8Array; // labioSup, labioInf, comisura, mejilla
  d: Uint8Array; // ceja, cejaInterior, párpadoSup, párpadoInf
  e: Float32Array; // posición dispersa xyz, ovillo (0..1)
  f: Float32Array; // tipo, ancho extra
}

function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => { a = (a + 0x6d2b79f5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const ss = (a: number, b: number, x: number): number => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
const len = (x: number, y: number, z: number): number => Math.sqrt(x * x + y * y + z * z);
const smin = (a: number, b: number, k: number): number => { const h = Math.max(k - Math.abs(a - b), 0) / k; return Math.min(a, b) - h * h * k * 0.25; };
const smax = (a: number, b: number, k: number): number => -smin(-a, -b, k);
function ell(x: number, y: number, z: number, cx: number, cy: number, cz: number, rx: number, ry: number, rz: number): number {
  const px = x - cx, py = y - cy, pz = z - cz;
  const k0 = len(px / rx, py / ry, pz / rz), k1 = len(px / (rx * rx), py / (ry * ry), pz / (rz * rz));
  return k1 < 1e-6 ? -Math.min(rx, ry, rz) : (k0 * (k0 - 1)) / k1;
}
function cap(x: number, y: number, z: number, ax: number, ay: number, az: number, bx: number, by: number, bz: number, r: number): number {
  const pax = x - ax, pay = y - ay, paz = z - az, bax = bx - ax, bay = by - ay, baz = bz - az;
  let h = (pax * bax + pay * bay + paz * baz) / (bax * bax + bay * bay + baz * baz); h = h < 0 ? 0 : h > 1 ? 1 : h;
  return len(pax - bax * h, pay - bay * h, paz - baz * h) - r;
}
const sph = (x: number, y: number, z: number, cx: number, cy: number, cz: number, r: number): number => len(x - cx, y - cy, z - cz) - r;

/** Distancia con signo al busto. Rostro maduro y lleno: frente alta, pómulos y mejillas con carne, nariz larga, mandíbula firme. */
export function sdf(x: number, y: number, z: number): number {
  const ax = Math.abs(x);
  let d = 1e9;
  if (y > -1.4) {
    d = ell(x, y, z, 0, 0.3, -0.1, 0.75, 0.8, 0.9); // cráneo
    d = smin(d, ell(x, y, z, 0, -0.28, 0.14, 0.62, 0.74, 0.67), 0.25); // macizo facial
    d = smin(d, ell(ax, y, z, 0.4, -0.6, 0.02, 0.25, 0.3, 0.34), 0.2); // ángulo de la mandíbula
    d = smin(d, ell(x, y, z, 0, -0.93, 0.5, 0.26, 0.17, 0.21), 0.18); // mentón
    d = smin(d, cap(x, y, z, -0.4, 0.31, 0.7, 0.4, 0.31, 0.7, 0.115), 0.12); // arco superciliar
    d = smin(d, ell(ax, y, z, 0.43, -0.17, 0.5, 0.24, 0.22, 0.24), 0.2); // pómulo lleno
    d = smin(d, ell(ax, y, z, 0.36, -0.5, 0.4, 0.24, 0.25, 0.27), 0.2); // mejilla
    d = smax(d, -sph(ax, y, z, EYE.x, 0.09, 0.95, 0.17), 0.12); // cuenca, poco hundida
    d = smin(d, sph(ax, y, z, EYE.x, EYE.y, EYE.z, EYE.r), 0.03); // globo ocular
    d = smin(d, cap(x, y, z, 0, 0.24, 0.8, 0, -0.24, 1.05, 0.082), 0.1); // puente de la nariz
    d = smin(d, sph(x, y, z, 0, -0.27, 1.04, 0.112), 0.06); // punta
    d = smin(d, sph(ax, y, z, 0.13, -0.31, 0.9, 0.085), 0.05); // aletas
    d = smin(d, ell(x, y, z, 0, -0.56, 0.72, 0.31, 0.2, 0.2), 0.12); // bozo
    d = smin(d, cap(ax, y, z, 0, -0.55, 0.9, 0.18, -0.565, 0.8, 0.05), 0.04); // labio superior
    d = smin(d, cap(ax, y, z, 0, -0.655, 0.885, 0.15, -0.645, 0.79, 0.062), 0.04); // labio inferior
    d = smin(d, ell(ax, y, z, 0.76, 0.02, -0.12, 0.07, 0.22, 0.15), 0.06); // oreja
  }
  d = smin(d, cap(x, y, z, 0, -0.7, -0.12, 0, -1.8, -0.22, 0.4), 0.2); // cuello
  if (y < -1.0) {
    d = smin(d, ell(x, y, z, 0, -2.6, -0.25, 1.85, 0.85, 0.72), 0.35); // hombros
    d = smin(d, ell(x, y, z, 0, -2.75, 0.02, 1.15, 0.95, 0.68), 0.3); // pecho
    d = smin(d, cap(ax, y, z, 0.25, -1.55, -0.25, 1.2, -2.05, -0.3, 0.28), 0.3); // trapecios
  }
  return d;
}

const E = 0.003;
const G = { x: 0, y: 0, z: 1, d: 0 };
/** Gradiente (normal) y distancia en 4 evaluaciones (tetraedro). */
function grad(x: number, y: number, z: number): typeof G {
  const a = sdf(x + E, y - E, z - E), b = sdf(x - E, y - E, z + E), c = sdf(x - E, y + E, z - E), e = sdf(x + E, y + E, z + E);
  let nx = a - b - c + e, ny = -a - b + c + e, nz = -a + b - c + e; const l = len(nx, ny, nz) || 1;
  nx /= l; ny /= l; nz /= l; G.x = nx; G.y = ny; G.z = nz; G.d = (a + b + c + e) * 0.25; return G;
}
/** Profundidad de la superficie vista de frente: se usa para posar los rasgos de autor. */
function frontZ(x: number, y: number): number { let z = 1.5; for (let i = 0; i < 48; i++) { const d = sdf(x, y, z); if (d < 0.0008) break; z -= d; } return z; }

type WKey = 'lipU' | 'lipL' | 'corner' | 'cheek' | 'brow' | 'browIn' | 'lidU' | 'lidL' | 'jaw' | 'head';
type Opt = { periph: number; loose: number; gain: number; kind?: number; wide?: number; think?: number; w?: (i: number, t: number) => Partial<Record<WKey, number>> };

export function createWeaver(): { W: Weave; step(ms: number): boolean } {
  const V = MAXS * NP * 2;
  const W: Weave = { strands: 0, done: false, ms: 0, pos: new Float32Array(V * 3), dir: new Float32Array(V * 3), nrm: new Float32Array(V * 3), a: new Float32Array(V * 4), b: new Float32Array(V * 4),
    c: new Uint8Array(V * 4), d: new Uint8Array(V * 4), e: new Float32Array(V * 4), f: new Float32Array(V * 2) };
  const R = rng(0x51a7e7), pts = new Float32Array(NP * 3), nrs = new Float32Array(NP * 3);
  let deadline = 0; const late = (): boolean => performance.now() > deadline;
  const u8 = (v: number): number => Math.max(0, Math.min(255, v * 255));

  /** Pesos del rig facial a partir de la posición en reposo. */
  const rig = (x: number, y: number, z: number): Record<WKey, number> => {
    const ax = Math.abs(x), front = ss(0.35, 0.6, z);
    const g = (dx: number, dy: number, dz: number, r: number): number => Math.exp(-(dx * dx + dy * dy + dz * dz) / (r * r));
    const brow = Math.exp(-(((y - 0.31) / 0.12) ** 2)) * ss(0.7, 0.5, ax) * front;
    return {
      head: ss(-1.8, -1.02, y),
      jaw: ss(-0.57, -0.69, y) * ss(-0.3, 0.12, z) * ss(-1.5, -1.08, y),
      lipU: g(0, y + 0.555, z - 0.86, 0.12) * ss(0.44, 0.2, ax) * ss(-0.625, -0.595, y),
      lipL: g(0, y + 0.665, z - 0.84, 0.12) * ss(0.4, 0.18, ax) * ss(-0.595, -0.625, y),
      corner: g(ax - 0.28, y + 0.6, z - 0.74, 0.16), cheek: g(ax - 0.42, y + 0.2, z - 0.55, 0.28),
      brow, browIn: brow * ss(0.36, 0.08, ax),
      lidU: Math.exp(-(((ax - EYE.x) / 0.2) ** 2 + ((y - 0.2) / 0.055) ** 2)) * front,
      lidL: Math.exp(-(((ax - EYE.x) / 0.19) ** 2 + ((y - 0.02) / 0.05) ** 2)) * front,
    };
  };
  /** Vuelca la hebra (pts/nrs, con `valid` puntos reales) a los búferes: dos vértices por punto (cinta). */
  const add = (valid: number, o: Opt): void => {
    if (valid < 3 || W.strands >= MAXS) return;
    const seed = R(), mid = Math.min(valid - 1, NP >> 1) * 3, r2 = R();
    const out = 0.1 + 1.5 * r2 * r2 * r2; // posición dispersa: la constelación conserva el fantasma de la silueta
    const sx = pts[mid]! + nrs[mid]! * out + (R() - 0.5) * 0.3, sy = Math.max(-3.4, Math.min(2.1, pts[mid + 1]! + nrs[mid + 1]! * out + (R() - 0.5) * 0.3)), sz = pts[mid + 2]! + nrs[mid + 2]! * out + (R() - 0.5) * 0.3;
    let v = W.strands * NP * 2;
    for (let i = 0; i < NP; i++) {
      const q = Math.min(i, valid - 1), j = q * 3, t = Math.min(1, i / (valid - 1));
      const x = pts[j]!, y = pts[j + 1]!, z = pts[j + 2]!, j0 = Math.max(0, q - 1) * 3, j1 = Math.min(valid - 1, q + 1) * 3;
      let tx = pts[j1]! - pts[j0]!, ty = pts[j1 + 1]! - pts[j0 + 1]!, tz = pts[j1 + 2]! - pts[j0 + 2]!; const tl = len(tx, ty, tz) || 1; tx /= tl; ty /= tl; tz /= tl;
      const w = rig(x, y, z); if (o.w) Object.assign(w, o.w(i, t));
      for (let side = -1; side <= 1; side += 2, v++) {
        W.pos.set([x, y, z], v * 3); W.dir.set([tx, ty, tz], v * 3); W.nrm.set([nrs[j]!, nrs[j + 1]!, nrs[j + 2]!], v * 3);
        W.a.set([side, t, seed, o.periph], v * 4); W.b.set([w.head, w.jaw, o.loose, o.gain], v * 4);
        W.c.set([u8(w.lipU), u8(w.lipL), u8(w.corner), u8(w.cheek)], v * 4); W.d.set([u8(w.brow), u8(w.browIn), u8(w.lidU), u8(w.lidL)], v * 4);
        W.e.set([sx, sy, sz, o.think ?? 0], v * 4); W.f.set([o.kind ?? 0, o.wide ?? 0], v * 2);
      }
    }
    W.strands++;
  };
  const put = (i: number, x: number, y: number, z: number, nx: number, ny: number, nz: number): void => { pts[i * 3] = x; pts[i * 3 + 1] = y; pts[i * 3 + 2] = z; nrs[i * 3] = nx; nrs[i * 3 + 1] = ny; nrs[i * 3 + 2] = nz; };
  /** Hebra de autor: f(t) da (x, y) de frente y se posa sobre la superficie con `lift` de separación. */
  const front = (f: (t: number) => [number, number], lift: (t: number) => number, o: Opt): void => {
    for (let i = 0; i < NP; i++) { const t = i / (NP - 1), [x, y] = f(t), z = frontZ(x, y), g = grad(x, y, z), l = lift(t); put(i, x + g.x * l, y + g.y * l, z + g.z * l, g.x, g.y, g.z); }
    add(NP, o);
  };

  // ── Campos de flujo: la piel sigue la fibra muscular; la frente se abre en abanico desde el entrecejo.
  const flow = (x: number, y: number, z: number, n: typeof G, out: number[]): void => {
    let fx = n.z, fy = 0, fz = -n.x; // anillos horizontales: cross(n, Y)
    for (const s of [-1, 1]) { const vx = x - s * EYE.x, vy = y - EYE.y, w = 1.3 * Math.exp(-(vx * vx + vy * vy + (z - 0.75) ** 2) / 0.09), l = Math.hypot(vx, vy) || 1; fx += (s * -vy * w) / l; fy += (s * vx * w) / l; }
    { const vx = x, vy = y + 0.6, w = 3 * Math.exp(-(vx * vx + vy * vy + (z - 0.8) ** 2) / 0.09), l = Math.hypot(vx, vy) || 1; fx += (-vy * w) / l; fy += (vx * w) / l; }
    { const w = 2.5 * Math.exp(-(x * x) / 0.012) * ss(0.36, 0.2, y) * ss(-0.36, -0.2, y) * ss(0.6, 0.8, z); fy -= w; }
    { const w = ss(0.2, 0.32, y) * ss(0.15, 0.45, z) * ss(0.02, 0.1, Math.abs(x) + (y - 0.2)), l = Math.hypot(x, y - 0.1) || 1; fx = fx * (1 - w) + (x / l) * 3 * w; fy = fy * (1 - w) + ((y - 0.1) / l) * 3 * w; fz *= 1 - w; } // frontal en abanico
    { const w = 2.2 * ss(-0.95, -1.25, y) * ss(-2.0, -1.7, y); fy -= w; fx *= 1 - w * 0.3; } // tendones del cuello
    { const w = 2.4 * ss(-1.85, -2.15, y) * ss(-0.2, 0.2, z); fx += -Math.sign(x) * 0.6 * w * ss(0.05, 0.3, Math.abs(x)); fy -= w; } // V de las solapas
    const dn = fx * n.x + fy * n.y + fz * n.z; fx -= n.x * dn; fy -= n.y * dn; fz -= n.z * dn; const l = len(fx, fy, fz);
    if (l > 1e-4) { out[0] = fx / l; out[1] = fy / l; out[2] = fz / l; }
  };
  const hairFlow = (x: number, _y: number, z: number, n: typeof G, out: number[], jit: number): void => {
    const back = ss(0.15, -0.75, z), side = ss(0.3, 0.7, Math.abs(x));
    let fx = Math.sign(x) * 0.14 * (1 - back) + jit, fy = -0.1 - 0.9 * back - 0.45 * side, fz = -1 + 0.75 * back;
    const dn = fx * n.x + fy * n.y + fz * n.z; fx -= n.x * dn; fy -= n.y * dn; fz -= n.z * dn; const l = len(fx, fy, fz);
    if (l > 1e-4) { out[0] = fx / l; out[1] = fy / l; out[2] = fz / l; }
  };
  const beardFlow = (x: number, n: typeof G, out: number[], jit: number): void => {
    let fx = Math.sign(x) * 0.1 + jit, fy = -1, fz = 0.12; const dn = fx * n.x + fy * n.y + fz * n.z; fx -= n.x * dn; fy -= n.y * dn; fz -= n.z * dn; const l = len(fx, fy, fz);
    if (l > 1e-4) { out[0] = fx / l; out[1] = fy / l; out[2] = fz / l; }
  };
  const inEye = (ax: number, y: number, z: number): boolean => ((ax - EYE.x) / 0.205) ** 2 + ((y - EYE.y) / 0.088) ** 2 < 1 && z > 0.5;
  const inMouth = (ax: number, y: number, z: number): boolean => ax < 0.27 && y < -0.535 && y > -0.7 && z > 0.6;
  const isHair = (ax: number, y: number, z: number): boolean => {
    if (ax > 0.69 && y > -0.26 && y < 0.3 && z < 0.12 && z > -0.36) return false; // oreja
    return y > Math.max(-0.42, 0.78 - (0.58 - z) * 0.95) + 0.12 * ss(0.2, 0.5, ax) * ss(0.2, 0.5, z);
  };
  const fdir = [1, 0, 0];
  /** Proyecta un punto al azar de la caja sobre la superficie. Devuelve false si no converge. */
  const seedPoint = (box: number[], p: number[]): boolean => {
    let x = box[0]! + R() * (box[1]! - box[0]!), y = box[2]! + R() * (box[3]! - box[2]!), z = box[4]! + R() * (box[5]! - box[4]!);
    for (let i = 0; i < 7; i++) { const g = grad(x, y, z); x -= g.x * g.d; y -= g.y * g.d; z -= g.z * g.d; if (Math.abs(g.d) < 0.0015) { p[0] = x; p[1] = y; p[2] = z; return y > -3.05 && y < 1.4; } }
    return false;
  };
  const sp = [0, 0, 0];

  /** Siembra en la superficie y traza cada hebra por su campo de flujo. */
  function* grow(box: number[], quota: Record<string, number>): Generator<void> {
    let left = Object.values(quota).reduce((s, v) => s + v, 0), tries = 0;
    while (left > 0 && tries++ < 90000) {
      if (late()) yield;
      if (!seedPoint(box, sp)) continue;
      let x = sp[0]!, y = sp[1]!, z = sp[2]!; const ax = Math.abs(x); let kind: string;
      if (y > -1.12) {
        if (inEye(ax, y, z) || inMouth(ax, y, z) || isHair(ax, y, z)) continue;
        const beardTop = -0.5 + 0.8 * ss(0.3, 0.7, ax);
        kind = y < beardTop && z > -0.24 && !(G.y < -0.8 && y < -1.0) && !(ax < 0.3 && y > -0.52) ? 'beard' : 'skin';
      } else kind = y > -1.8 ? 'neck' : y > -2.72 ? 'torso' : 'fringe';
      if (!quota[kind]) continue;
      quota[kind]!--; left--;
      const g0 = grad(x, y, z); fdir[0] = g0.z; fdir[1] = 0; fdir[2] = -g0.x;
      const jit = (R() - 0.5) * 0.5, y0 = y, z0 = z;
      if (kind === 'fringe') { // flecos: el busto se deshila hacia abajo
        const L = 0.5 + R() * 0.8; for (let i = 0; i < NP; i++) { const t = i / (NP - 1); put(i, x + Math.sin(t * 3 + jit * 9) * 0.03, y - t * L, z, g0.x, g0.y * 0.3, g0.z); }
        add(NP, { periph: 0.96 + R() * 0.1, loose: 1.5, gain: 0.3 }); continue;
      }
      const beard = kind === 'beard', step = beard ? 0.02 + R() * 0.012 : kind === 'torso' ? 0.05 : 0.034;
      let valid = 0;
      for (let i = 0; i < NP; i++) {
        const g = grad(x, y, z), t = i / (NP - 1);
        if (!beard && i > 0 && (inEye(Math.abs(x), y, z) || inMouth(Math.abs(x), y, z))) break;
        const lift = beard ? 0.008 + 0.045 * t : 0.004;
        put(i, x + g.x * lift, y + g.y * lift, z + g.z * lift, g.x, g.y, g.z); valid++;
        if (beard) beardFlow(x, g, fdir, jit); else flow(x, y, z, g, fdir);
        x += fdir[0]! * step; y += fdir[1]! * step; z += fdir[2]! * step;
        const g2 = grad(x, y, z); x -= g2.x * g2.d; y -= g2.y * g2.d; z -= g2.z * g2.d;
      }
      const down = ss(-1.8, -3.0, y0);
      if (beard) add(valid, { periph: 0.2 + R() * 0.15, loose: 0.3 + R() * 0.3, gain: 0.74 });
      else if (kind === 'skin') add(valid, { periph: 0.08 + 0.22 * ss(0.5, -0.3, z0) + R() * 0.12, loose: 0.12, gain: 0.6 - 0.36 * ss(0.2, 0.34, y0) * ss(0.2, 0.5, z0) });
      else if (kind === 'neck') add(valid, { periph: 0.42 + R() * 0.12, loose: 0.15, gain: 0.72 });
      else add(valid, { periph: 0.52 + 0.42 * down + R() * 0.1, loose: 0.2 + 0.6 * down, gain: 0.34 });
    }
  }

  function* run(): Generator<void> {
    // ── Rasgos de autor primero: lo primero que se teje es la mirada ──────────────────────────────
    for (const s of [-1, 1]) {
      const ex = s * EYE.x, eyeP = (i: number, rho: number, phi: number): void => { const dx = rho * Math.cos(phi), dy = rho * Math.sin(phi), dz = Math.sqrt(EYE.r ** 2 - rho * rho); put(i, ex + dx, EYE.y + dy, EYE.z + dz, dx / EYE.r, dy / EYE.r, dz / EYE.r); };
      // Iris: hebras radiales en espiral; la pupila es el hueco oscuro del centro.
      for (let k = 0; k < 58; k++) {
        const phi = (k / 58) * Math.PI * 2 + R() * 0.1, r0 = 0.03 + R() * 0.008, r1 = 0.083 + R() * 0.008;
        for (let i = 0; i < NP; i++) { const t = i / (NP - 1); eyeP(i, r0 + (r1 - r0) * t, phi + 0.55 * t); }
        add(NP, { periph: 0, loose: 0, gain: 1.5, kind: K.EYE });
      }
      for (let k = 0; k < 7; k++) { const p0 = (k / 7) * Math.PI * 2; for (let i = 0; i < NP; i++) eyeP(i, 0.093, p0 + (i / (NP - 1)) * 1.15); add(NP, { periph: 0, loose: 0, gain: 0.5, kind: K.EYE }); }
      for (let i = 0; i < NP; i++) eyeP(i, 0.046, 2.15 + (i / (NP - 1)) * 0.55); add(NP, { periph: 0, loose: 0, gain: 2.4, kind: K.EYE, wide: 1.1 }); // brillo de la mirada
      for (let i = 0; i < NP; i++) eyeP(i, 0.06, 5.4 + (i / (NP - 1)) * 0.3); add(NP, { periph: 0, loose: 0, gain: 1.2, kind: K.EYE, wide: 0.4 });
      // Párpados: arcos sobre el globo ocular; el peso sin(a) los cierra en el shader. Pliegue arriba, ojera suave abajo.
      const lidZ = (dx: number, dy: number): number => EYE.z + Math.sqrt(Math.max(0.0001, (EYE.r + 0.008) ** 2 - dx * dx - dy * dy));
      for (let k = 0; k < 5; k++) for (const half of [0, 1]) {
        for (let i = 0; i < NP; i++) { const a = (half + i / (NP - 1)) * Math.PI * 0.5 * 1.04, dx = -s * EYE.halfW * Math.cos(a), dy = (EYE.up + k * 0.013) * Math.sin(a); put(i, ex + dx, EYE.y + dy, lidZ(dx, dy) + k * 0.004, dx * 2, dy * 2 + 0.3, 0.9); }
        add(NP, { periph: 0, loose: 0, gain: k === 0 ? 2.0 : 0.55, wide: k === 0 ? 0.35 : 0, w: (i) => ({ lidU: Math.sin((half + i / (NP - 1)) * Math.PI * 0.5), lidL: 0, brow: 0, browIn: 0 }) });
      }
      for (let k = 0; k < 3; k++) for (const half of [0, 1]) {
        for (let i = 0; i < NP; i++) { const a = (half + i / (NP - 1)) * Math.PI * 0.5, dx = -s * EYE.halfW * Math.cos(a), dy = -(EYE.low + k * 0.016) * Math.sin(a); put(i, ex + dx, EYE.y + dy, lidZ(dx, dy), dx * 2, dy * 2 - 0.2, 0.9); }
        add(NP, { periph: 0, loose: 0, gain: k === 0 ? 0.7 : 0.35, w: (i) => ({ lidL: Math.sin((half + i / (NP - 1)) * Math.PI * 0.5), lidU: 0, brow: 0, browIn: 0 }) });
      }
      if (late()) yield;
      // Cejas rectas y pobladas, con un leve arco exterior.
      for (let k = 0; k < 95; k++) {
        const u = R(), x0 = 0.125 + 0.43 * u, y0 = 0.262 + 0.075 * Math.sin(Math.PI * Math.min(1, u * 1.05) * 0.8) - 0.05 * u * u + (R() - 0.5) * 0.045 * (1 - 0.65 * u), L = 0.09 + R() * 0.06, rise = 0.75 - 1.5 * u;
        front((t) => [s * (x0 + L * t), y0 + L * t * rise * 0.45 - 0.02 * t * t], (t) => 0.012 + 0.02 * t, { periph: 0.03, loose: 0.25, gain: 0.82, w: () => ({ brow: 1, browIn: ss(0.36, 0.1, x0), lidU: 0 }) });
        if (late()) yield;
      }
      // Bigote recortado: nace bajo la nariz, se abre hacia los lados y deja ver el labio.
      for (let k = 0; k < 150; k++) {
        const x0 = 0.008 + R() * 0.23, y0 = -0.4 - R() * 0.055 - 0.035 * (x0 / 0.23) ** 2, L = 0.11 + R() * 0.09;
        front((t) => [s * (x0 + L * t), y0 - L * (0.2 * t + 0.42 * t * t)], (t) => 0.014 + 0.035 * Math.sin(Math.PI * t) + 0.012 * t, { periph: 0.1, loose: 0.45, gain: 0.9, w: (_i, t) => ({ lipU: 0.7, corner: 0.3 * t, jaw: 0, lipL: 0 }) });
        if (late()) yield;
      }
      for (let k = 0; k < 5; k++) { // surco nasolabial: de la aleta de la nariz a la comisura
        const o = k * 0.012;
        front((t) => [s * (0.17 + o + 0.17 * t - 0.03 * Math.sin(Math.PI * t)), -0.3 - 0.33 * t + o * 0.5], () => 0.004, { periph: 0.05, loose: 0, gain: 0.75 - k * 0.11 });
      }
      for (let k = 0; k < 4; k++) { // patas de gallo: ha sonreído mucho
        const a = -0.55 + k * 0.33;
        front((t) => [s * (EYE.x + EYE.halfW + 0.02 + 0.1 * t * Math.cos(a)), EYE.y - 0.005 + 0.1 * t * Math.sin(a)], () => 0.004, { periph: 0.05, loose: 0, gain: 0.5 });
      }
      // Labios tejidos como superficie: filas de centro a comisura, con el arco de Cupido arriba y el inferior más carnoso.
      for (let j = 0; j < 12; j++) {
        const f = j / 11;
        front((t) => { const x = 0.245 * t, top = (-0.558 + 0.012 * Math.exp(-((x - 0.05) ** 2) / 0.0014)) * (1 - t * t) - 0.603 * t * t; return [s * x, top + (-0.6015 - top) * f]; }, () => 0.005,
          { periph: 0, loose: 0, gain: 0.5 + 0.4 * f, kind: K.LIP, w: (_i, t) => ({ lipU: 1 - 0.4 * t, lipL: 0, corner: t * t, jaw: 0 }) });
        front((t) => { const bot = -0.664 * (1 - t * t) - 0.607 * t * t; return [s * 0.24 * t, -0.6075 + (bot + 0.6075) * f]; }, () => 0.005,
          { periph: 0, loose: 0, gain: 0.95 - 0.45 * f, kind: K.LIP, w: (_i, t) => ({ lipL: 1 - 0.4 * t, lipU: 0, corner: t * t, jaw: 1 - 0.55 * t * t }) });
        if (late()) yield;
      }
    }
    // Interior de la boca: dientes superiores y un fondo cálido; nunca un hueco negro.
    for (let k = 0; k < 15; k++) {
      const x = (k / 14 - 0.5) * 0.3;
      for (let i = 0; i < NP; i++) put(i, x, -0.596 - (i / (NP - 1)) * 0.05, 0.815 - Math.abs(x) * 0.3, 0, 0, 1);
      add(NP, { periph: 0, loose: 0, gain: 1, kind: K.TEETH, wide: 0.9, w: () => ({ jaw: 0, lipU: 0, lipL: 0, corner: 0 }) });
    }
    for (let k = 0; k < 8; k++) {
      for (let i = 0; i < NP; i++) { const t = i / (NP - 1) - 0.5; put(i, t * (0.3 - k * 0.012), -0.612 - k * 0.012, 0.77, 0, 0, 1); }
      add(NP, { periph: 0, loose: 0, gain: 1, kind: K.GLOW, wide: 2.6, w: () => ({ jaw: 0.15 + 0.12 * k, lipU: 0, lipL: 0, corner: 0 }) });
    }
    yield* grow([-0.95, 0.95, -1.25, 1.3, -1.15, 1.2], { skin: 2900, beard: 2100 });
    // Pelo en mechones: cada guía arrastra una treintena de hebras que se juntan en la punta y se levantan a distinta altura.
    const gp = new Float32Array(NP * 6);
    for (let lock = 0, tries = 0; lock < 104 && tries < 20000; tries++) {
      if (!seedPoint([-0.95, 0.95, -0.5, 1.3, -1.15, 1.0], sp)) continue;
      let x = sp[0]!, y = sp[1]!, z = sp[2]!; if (y < -1.1 || !isHair(Math.abs(x), y, z)) continue;
      lock++;
      const jit = (R() - 0.5) * 0.22, y0 = y, quiff = ss(0.05, 0.5, z) * ss(0.45, 0.8, y), step = 0.085 + R() * 0.03, rise = 0.035 + R() * 0.06 + 0.075 * quiff, curl = R() * 0.03;
      for (let i = 0; i < NP; i++) { // la guía
        const g = grad(x, y, z); gp.set([x, y, z, g.x, g.y, g.z], i * 6);
        hairFlow(x, y, z, g, fdir, jit); x += fdir[0]! * step; y += fdir[1]! * step; z += fdir[2]! * step;
        const g2 = grad(x, y, z); x -= g2.x * g2.d; y -= g2.y * g2.d; z -= g2.z * g2.d;
      }
      const nx = gp[3]!, ny = gp[4]!, nz = gp[5]!, lockGain = 0.45 + R() * 0.3;
      for (let c = 0; c < 26; c++) {
        let ox = R() - 0.5, oy = R() - 0.5, oz = R() - 0.5; const dn = ox * nx + oy * ny + oz * nz; ox -= nx * dn; oy -= ny * dn; oz -= nz * dn;
        const ol = (0.125 * Math.sqrt(R())) / (len(ox, oy, oz) || 1), up = R() * 0.022;
        for (let i = 0; i < NP; i++) {
          const t = i / (NP - 1), q = i * 6, k = ol * (1 - 0.6 * t), lift = 0.012 + up + rise * Math.pow(Math.sin(Math.PI * Math.min(1, t * 1.08)), 0.8) + curl * t * t;
          put(i, gp[q]! + ox * k + gp[q + 3]! * lift, gp[q + 1]! + oy * k + gp[q + 4]! * lift, gp[q + 2]! + oz * k + gp[q + 5]! * lift, gp[q + 3]!, gp[q + 4]!, gp[q + 5]!);
        }
        add(NP, { periph: 0.3 + 0.25 * ss(0.4, -0.6, gp[2]!) + R() * 0.12, loose: 0.5 + R() * 0.7, gain: lockGain + (c < 4 ? 0.3 : 0), think: y0 > 0.6 && R() < 0.5 ? 1 : 0 });
      }
      if (late()) yield;
    }
    yield* grow([-2.05, 2.05, -3.1, -1.1, -1.1, 0.9], { neck: 420, torso: 2000, fringe: 250 });
    for (const s of [-1, 1]) for (let k = 0; k < 5; k++) for (let seg = 0; seg < 5; seg++) { // solapas: líneas que caen en V
      const o = k * 0.05;
      front((t) => { const u = (seg + t * 1.08) / 5; return [s * (0.5 + o - (0.44 + o * 0.6) * u ** 1.3), -1.72 - 1.3 * u]; }, () => 0.03, { periph: 0.5 + 0.09 * seg, loose: 0.1 + 0.08 * seg, gain: k === 0 ? 0.9 : 0.5 });
      if (late()) yield;
    }
    for (let k = 0; k < 3; k++) for (let seg = 0; seg < 12; seg++) { // cuello alto de la camisa, abierto por delante
      for (let i = 0; i < NP; i++) {
        const th = 0.3 + ((seg + (i / (NP - 1)) * 1.06) / 12) * (Math.PI * 2 - 0.6);
        let x = 0.5 * Math.sin(th), y = -1.44 - k * 0.055 - 0.1 * Math.cos(th), z = -0.2 + 0.5 * Math.cos(th);
        for (let q = 0; q < 5; q++) { const g = grad(x, y, z); x -= g.x * g.d; y -= g.y * g.d * 0.2; z -= g.z * g.d; }
        const g = grad(x, y, z); put(i, x + g.x * 0.05, y, z + g.z * 0.05, g.x, g.y, g.z);
      }
      add(NP, { periph: 0.4, loose: 0.05, gain: k === 0 ? 0.95 : 0.5 });
      if (late()) yield;
    }
    const kz = frontZ(KNOT[0], KNOT[1]) + 0.05; // la brasa del nudo
    for (let k = 0; k < 6; k++) {
      const a = (k / 6) * Math.PI;
      for (let i = 0; i < NP; i++) { const t = i / (NP - 1) - 0.5; put(i, KNOT[0] + Math.cos(a) * t * 0.1, KNOT[1] + Math.sin(a) * t * 0.1, kz, 0, 0.1, 1); }
      add(NP, { periph: -1, loose: 0, gain: 1, kind: K.EMBER, wide: 5 });
    }
  }
  const it = run();
  return { W, step(ms) { if (W.done) return true; const t0 = performance.now(); deadline = t0 + ms; W.done = it.next().done === true; W.ms += performance.now() - t0; return W.done; } };
}
