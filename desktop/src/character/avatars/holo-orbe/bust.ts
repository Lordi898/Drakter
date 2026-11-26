// Busto procedural de «Holo-Orbe»: un SDF (cabeza, cuello, torso) del que salen dos cosas:
//  1. miles de filamentos trazados sobre la superficie (y un enjambre libre que orbita), y
//  2. una cáscara de malla que da volumen holográfico y oclusión real.
// Todo se genera por código y con semilla fija. El trabajo es incremental (step(ms)) y nunca bloquea el hilo principal.
// Ejes: +x derecha de pantalla, +y arriba, +z hacia el espectador. La cabeza mide ~2,25 unidades.

export const NP = 8; // puntos por filamento
export const MAXS = 12500; // filamentos reservados
export const EYE = { x: 0.3, y: 0.08, z: 0.56, r: 0.2, halfW: 0.175, up: 0.07, low: 0.047 };
export const YM = -0.64; // línea de la boca
export const PIVOT = [0, -0.95, -0.15] as const; // base del cráneo: gira la cabeza
export const MOUTH = [0, YM, 0.88] as const;
export const K = { SKIN: 0, FREE: 1, BROW: 2, LIP: 3, LINE: 4, HAIR: 5 } as const;
export const SH_COLS = 168;

export interface Weave {
  strands: number; done: boolean; ms: number;
  pos: Float32Array; dir: Float32Array; nrm: Float32Array;
  a: Float32Array; // lado, t, semilla, periferia
  b: Float32Array; // pesoCabeza, pesoMandíbula, soltura, ganancia
  c: Uint8Array; // labioSup, labioInf, comisura, mejilla
  d: Uint8Array; // ceja, cejaInterior, párpadoSup, párpadoInf
  f: Float32Array; // tipo, ancho extra
}
export interface Shell {
  ready: boolean; verts: number;
  pos: Float32Array; nrm: Float32Array; b: Float32Array; c: Uint8Array; d: Uint8Array; index: Uint16Array;
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

/** Distancia con signo al busto. Caballero de 55-60: frente alta, órbitas hundidas bajo el arco superciliar,
 *  pómulo marcado con la mejilla algo enjuta, nariz larga de caballete suave, labio fino y mandíbula limpia. */
export function sdf(x: number, y: number, z: number): number {
  const ax = Math.abs(x);
  let d = 1e9;
  if (y > -1.45) {
    d = ell(x, y, z, 0, 0.3, -0.12, 0.74, 0.77, 0.92); // cráneo
    d = smin(d, ell(x, y, z, 0, -0.25, 0.15, 0.58, 0.7, 0.62), 0.25); // macizo facial
    d = smin(d, ell(ax, y, z, 0.41, -0.55, 0.04, 0.2, 0.27, 0.3), 0.2); // ángulo de la mandíbula, ancho
    d = smin(d, ell(ax, y, z, 0.23, -0.84, 0.4, 0.21, 0.15, 0.3), 0.16); // cuerpo de la mandíbula
    d = smin(d, ell(x, y, z, 0, -0.94, 0.65, 0.25, 0.14, 0.16), 0.12); // mentón ancho
    d = smin(d, sph(ax, y, z, 0.13, -0.97, 0.66, 0.085), 0.1); // y cuadrado
    d = smin(d, ell(ax, y, z, 0.25, 0.32, 0.67, 0.26, 0.1, 0.21), 0.14); // arco superciliar marcado
    d = smin(d, sph(x, y, z, 0, 0.27, 0.75, 0.09), 0.1); // glabela
    d = smin(d, ell(ax, y, z, 0.45, -0.13, 0.44, 0.2, 0.14, 0.22), 0.16); // pómulo
    d = smin(d, cap(ax, y, z, 0.5, -0.1, 0.4, 0.72, -0.03, -0.02, 0.07), 0.12); // arco cigomático
    d = smin(d, ell(ax, y, z, 0.33, -0.44, 0.42, 0.17, 0.22, 0.22), 0.2); // mejilla, algo enjuta
    d = smax(d, -sph(ax, y, z, 0.3, 0.09, 0.89, 0.19), 0.15); // cuenca
    d = smin(d, sph(ax, y, z, EYE.x, EYE.y, EYE.z, EYE.r), 0.02); // globo ocular
    d = smin(d, ell(ax, y, z, 0.31, 0.19, 0.64, 0.19, 0.04, 0.12), 0.06); // párpado superior, algo caído
    d = smin(d, ell(ax, y, z, 0.3, -0.05, 0.63, 0.16, 0.03, 0.11), 0.06); // bolsa
    d = smin(d, cap(x, y, z, 0, 0.17, 0.74, 0, -0.27, 1.03, 0.058), 0.08); // dorso de la nariz
    d = smin(d, sph(x, y, z, 0, -0.04, 0.925, 0.06), 0.08); // caballete
    d = smin(d, sph(x, y, z, 0, -0.31, 1.055, 0.078), 0.05); // punta
    d = smin(d, ell(x, y, z, 0, -0.2, 0.86, 0.095, 0.2, 0.12), 0.08); // paredes de la nariz
    d = smin(d, sph(ax, y, z, 0.095, -0.335, 0.915, 0.05), 0.09); // aletas
    d = smin(d, cap(x, y, z, 0, -0.38, 1.0, 0, -0.41, 0.9, 0.036), 0.04); // columela
    d = smin(d, ell(x, y, z, 0, -0.57, 0.67, 0.27, 0.18, 0.19), 0.12); // maxilar
    d = smax(d, -cap(x, y, z, 0, -0.45, 0.91, 0, -0.55, 0.925, 0.02), 0.03); // surco del filtrum
    d = smin(d, cap(ax, y, z, 0, -0.605, 0.885, 0.2, -0.63, 0.79, 0.033), 0.04); // labio superior, fino
    d = smin(d, cap(ax, y, z, 0, -0.682, 0.868, 0.17, -0.66, 0.78, 0.045), 0.04); // labio inferior
    d = smin(d, ell(ax, y, z, 0.76, -0.02, -0.13, 0.045, 0.21, 0.13), 0.05); // oreja
    d = smax(d, -sph(ax, y, z, 0.81, 0.27, 0.38, 0.15), 0.15); // sien algo hundida
    d = smax(d, -cap(ax, y, z, 0.165, -0.36, 0.88, 0.285, -0.62, 0.76, 0.02), 0.05); // surco nasogeniano
    d = smax(d, (-0.77 - 0.5 * z - y) * 0.89, 0.16); // borde inferior de la mandíbula: un plano limpio del mentón al ángulo
  }
  d = smin(d, cap(x, y, z, 0, -0.7, -0.14, 0, -1.85, -0.24, 0.44), 0.2); // cuello grueso
  if (y < -0.6 && y > -2.1) {
    d = smin(d, cap(ax, y, z, 0.36, -0.62, -0.3, 0.08, -1.8, 0.12, 0.07), 0.1); // esternocleidomastoideo
    d = smin(d, sph(x, y, z, 0, -1.32, 0.27, 0.05), 0.1); // nuez discreta
  }
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
type Opt = { periph: number; loose: number; gain: number; kind?: number; wide?: number; w?: (i: number, t: number) => Partial<Record<WKey, number>> };

/** Pesos del rig facial a partir de la posición en reposo. Los comparten los filamentos y la cáscara. */
function rig(x: number, y: number, z: number): Record<WKey, number> {
  const ax = Math.abs(x), front = ss(0.35, 0.6, z);
  const g = (dx: number, dy: number, dz: number, r: number): number => Math.exp(-(dx * dx + dy * dy + dz * dz) / (r * r));
  const brow = Math.exp(-(((y - 0.31) / 0.12) ** 2)) * ss(0.72, 0.5, ax) * front;
  // Mandíbula: suave en la cara, pero con un corte limpio en la línea de la boca para que los labios se separen.
  const t = Math.min(1, ax / 0.25), below = y < YM;
  const jawSmooth = ss(-0.5, -0.78, y) * ss(-0.35, 0.1, z) * ss(-1.55, -1.12, y);
  const inM = ss(0.31, 0.24, ax) * ss(0.5, 0.66, z) * ss(-0.82, -0.74, y) * ss(-0.5, -0.56, y);
  const jawM = below ? 1 - 0.5 * t * t : 0.5 * t * t * Math.exp(-(((y - YM) / 0.07) ** 2));
  return {
    head: ss(-1.8, -1.02, y),
    jaw: jawSmooth + (jawM - jawSmooth) * inM,
    lipU: below ? 0 : g(0, y + 0.6, z - 0.88, 0.12) * ss(0.44, 0.2, ax),
    lipL: below ? g(0, y + 0.69, z - 0.86, 0.12) * ss(0.4, 0.18, ax) : 0,
    corner: g(ax - 0.25, y - YM, z - 0.76, 0.16), cheek: g(ax - 0.42, y + 0.22, z - 0.52, 0.28),
    brow, browIn: brow * ss(0.36, 0.08, ax),
    lidU: Math.exp(-(((ax - EYE.x) / 0.2) ** 2 + ((y - 0.2) / 0.055) ** 2)) * front,
    lidL: Math.exp(-(((ax - EYE.x) / 0.19) ** 2 + ((y + 0.0) / 0.05) ** 2)) * front,
  };
}
const u8 = (v: number): number => Math.max(0, Math.min(255, v * 255));
const inEyeBox = (ax: number, y: number, z: number): boolean => ((ax - EYE.x) / (EYE.halfW + 0.035)) ** 2 + ((y - EYE.y - 0.01) / 0.095) ** 2 < 1 && z > 0.45;

export function createWeaver(): { W: Weave; S: Shell; step(ms: number): boolean } {
  const V = MAXS * NP * 2;
  const W: Weave = { strands: 0, done: false, ms: 0, pos: new Float32Array(V * 3), dir: new Float32Array(V * 3), nrm: new Float32Array(V * 3), a: new Float32Array(V * 4), b: new Float32Array(V * 4),
    c: new Uint8Array(V * 4), d: new Uint8Array(V * 4), f: new Float32Array(V * 2) };
  // Filas de la cáscara: casquete esférico arriba y anillos horizontales desde las cejas hasta el pecho.
  const CAPN = 26, ys: number[] = [];
  for (let y = 0.3; y > -1.17; y -= y < -0.7 ? 0.011 : 0.02) { if (Math.abs(y - YM) < 0.005) ys.push(YM + 0.004, YM - 0.004); else ys.push(y); } // más filas bajo la mandíbula
  for (let y = -1.2; y > -3.05; y -= 0.04) ys.push(y);
  const ROWS = CAPN + ys.length, SV = ROWS * SH_COLS;
  const S: Shell = { ready: false, verts: SV, pos: new Float32Array(SV * 3), nrm: new Float32Array(SV * 3), b: new Float32Array(SV * 4), c: new Uint8Array(SV * 4), d: new Uint8Array(SV * 4), index: new Uint16Array((ROWS - 1) * SH_COLS * 6) };

  const R = rng(0x0b10e5), pts = new Float32Array(NP * 3), nrs = new Float32Array(NP * 3);
  let deadline = 0; const late = (): boolean => performance.now() > deadline;

  /** Vuelca el filamento (pts/nrs, con `valid` puntos reales) a los búferes: dos vértices por punto (cinta). */
  const add = (valid: number, o: Opt): void => {
    if (valid < 3 || W.strands >= MAXS) return;
    const seed = R();
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
        W.f.set([o.kind ?? 0, o.wide ?? 0], v * 2);
      }
    }
    W.strands++;
  };
  const put = (i: number, x: number, y: number, z: number, nx: number, ny: number, nz: number): void => { pts[i * 3] = x; pts[i * 3 + 1] = y; pts[i * 3 + 2] = z; nrs[i * 3] = nx; nrs[i * 3 + 1] = ny; nrs[i * 3 + 2] = nz; };
  /** Filamento de autor: f(t) da (x, y) de frente y se posa sobre la superficie con `lift` de separación. */
  const front = (f: (t: number) => [number, number], lift: (t: number) => number, o: Opt): void => {
    for (let i = 0; i < NP; i++) { const t = i / (NP - 1), [x, y] = f(t), z = frontZ(x, y), g = grad(x, y, z), l = lift(t); put(i, x + g.x * l, y + g.y * l, z + g.z * l, g.x, g.y, g.z); }
    add(NP, o);
  };

  // ── Campos de flujo: la piel se dibuja en curvas de nivel que rodean ojos y boca y bajan por la nariz.
  const flow = (x: number, y: number, z: number, n: typeof G, out: number[]): void => {
    const ax = Math.abs(x), sg = x < 0 ? -1 : 1;
    let fx = sg * n.z, fy = 0, fz = -sg * n.x; // de la línea media hacia fuera
    fy += 0.85 * ss(0.05, -0.15, y) * ss(0.02, 0.14, ax) * ss(-1.2, -1.0, y) * ss(-0.25, 0.15, z); // mejilla y mandíbula: barrido diagonal hacia la oreja
    for (const s of [-1, 1]) { const vx = x - s * EYE.x, vy = y - EYE.y, w = 1.3 * Math.exp(-(vx * vx + vy * vy + (z - 0.7) ** 2) / 0.09), l = Math.hypot(vx, vy) || 1; fx += (s * -vy * w) / l; fy += (s * vx * w) / l; } // orbicular de los ojos
    { const vx = x, vy = y - YM, w = (vy > 0 ? 1.5 : 0.7) * Math.exp(-(vx * vx + vy * vy + (z - 0.8) ** 2) / 0.07), l = Math.hypot(vx, vy) || 1; fx += (sg * vy * w) / l; fy += (-sg * vx * w) / l; } // orbicular de la boca
    { const w = 2.5 * Math.exp(-(x * x) / 0.012) * ss(0.3, 0.16, y) * ss(-0.42, -0.28, y) * ss(0.6, 0.8, z); fy -= w; } // dorso de la nariz
    { const w = 2.2 * ss(-0.95, -1.25, y) * ss(-2.0, -1.7, y); fy -= w; fx *= 1 - w * 0.3; } // tendones del cuello
    { const w = 2.4 * ss(-1.85, -2.15, y) * ss(-0.2, 0.2, z); fx += -sg * 0.6 * w * ss(0.05, 0.3, ax); fy -= w; } // caída de la chaqueta
    const dn = fx * n.x + fy * n.y + fz * n.z; fx -= n.x * dn; fy -= n.y * dn; fz -= n.z * dn; const l = len(fx, fy, fz);
    if (l > 1e-4) { out[0] = fx / l; out[1] = fy / l; out[2] = fz / l; }
  };
  const hairFlow = (x: number, _y: number, z: number, n: typeof G, out: number[], jit: number): void => {
    const back = ss(0.15, -0.75, z), side = ss(0.3, 0.7, Math.abs(x));
    let fx = Math.sign(x) * 0.1 * (1 - back) + 0.1 + jit, fy = -0.1 - 0.9 * back - 0.5 * side, fz = -1 + 0.75 * back; // peinado hacia atrás, con la raya a un lado
    const dn = fx * n.x + fy * n.y + fz * n.z; fx -= n.x * dn; fy -= n.y * dn; fz -= n.z * dn; const l = len(fx, fy, fz);
    if (l > 1e-4) { out[0] = fx / l; out[1] = fy / l; out[2] = fz / l; }
  };
  const inMouth = (ax: number, y: number, z: number): boolean => ax < 0.275 && y < -0.555 && y > -0.75 && z > 0.6;
  const isHair = (ax: number, y: number, z: number): boolean => {
    if (ax > 0.69 && y > -0.26 && y < 0.3 && z < 0.12 && z > -0.36) return false; // oreja
    return y > Math.max(-0.42, 0.75 - 0.07 * Math.exp(-((ax / 0.13) ** 2)) - Math.max(0, 0.6 - z) * 0.95) + 0.2 * ss(0.16, 0.42, ax) * ss(0.1, 0.5, z) + 0.025 * Math.sin(ax * 41 + z * 13); // pico central, entradas y borde irregular
  };
  const fdir = [1, 0, 0];
  /** Proyecta un punto al azar de la caja sobre la superficie. Devuelve false si no converge. */
  const seedPoint = (box: number[], p: number[]): boolean => {
    let x = box[0]! + R() * (box[1]! - box[0]!), y = box[2]! + R() * (box[3]! - box[2]!), z = box[4]! + R() * (box[5]! - box[4]!);
    for (let i = 0; i < 7; i++) { const g = grad(x, y, z); x -= g.x * g.d; y -= g.y * g.d; z -= g.z * g.d; if (Math.abs(g.d) < 0.0015) { p[0] = x; p[1] = y; p[2] = z; return y > -3.05 && y < 1.4; } }
    return false;
  };
  const sp = [0, 0, 0];

  /** Siembra en la superficie y traza cada filamento por su campo de flujo. */
  function* grow(box: number[], quota: Record<string, number>): Generator<void> {
    let left = Object.values(quota).reduce((s, v) => s + v, 0), tries = 0;
    while (left > 0 && tries++ < 90000) {
      if (late()) yield;
      if (!seedPoint(box, sp)) continue;
      let x = sp[0]!, y = sp[1]!, z = sp[2]!; const ax = Math.abs(x); let kind: string;
      if (y > -1.12) { if (inEyeBox(ax, y, z) || inMouth(ax, y, z) || isHair(ax, y, z)) continue; kind = 'skin'; }
      else kind = y > -1.8 ? 'neck' : y > -2.72 ? 'torso' : 'fringe';
      if (!quota[kind]) continue;
      quota[kind]!--; left--;
      const g0 = grad(x, y, z); fdir[0] = g0.z; fdir[1] = 0; fdir[2] = -g0.x;
      const jit = (R() - 0.5) * 0.5, y0 = y, z0 = z;
      if (kind === 'fringe') { // flecos: el busto se deshace en hilos de luz hacia abajo
        const L = 0.5 + R() * 0.8; for (let i = 0; i < NP; i++) { const t = i / (NP - 1); put(i, x + Math.sin(t * 3 + jit * 9) * 0.03, y - t * L, z, g0.x, g0.y * 0.3, g0.z); }
        add(NP, { periph: 0.96 + R() * 0.1, loose: 1.5, gain: 0.3 }); continue;
      }
      const step = kind === 'torso' ? 0.05 : 0.036;
      let valid = 0;
      for (let i = 0; i < NP; i++) {
        const g = grad(x, y, z);
        if (i > 0 && (inEyeBox(Math.abs(x), y, z) || inMouth(Math.abs(x), y, z))) break;
        put(i, x + g.x * 0.004, y + g.y * 0.004, z + g.z * 0.004, g.x, g.y, g.z); valid++;
        flow(x, y, z, g, fdir);
        x += fdir[0]! * step; y += fdir[1]! * step; z += fdir[2]! * step;
        const g2 = grad(x, y, z); x -= g2.x * g2.d; y -= g2.y * g2.d; z -= g2.z * g2.d;
      }
      const down = ss(-1.8, -3.0, y0);
      if (kind === 'skin') add(valid, { periph: 0.06 + 0.22 * ss(0.5, -0.3, z0) + R() * 0.12, loose: 0.1, gain: 0.42, wide: -0.3 });
      else if (kind === 'neck') add(valid, { periph: 0.4 + R() * 0.12, loose: 0.12, gain: 0.5 });
      else add(valid, { periph: 0.52 + 0.42 * down + R() * 0.1, loose: 0.2 + 0.6 * down, gain: 0.3 });
    }
  }

  function* run(): Generator<void> {
    // ── El enjambre libre va primero: el orbe existe desde el primer fotograma ─────────────────────
    for (let k = 0; k < 1700; k++) { for (let i = 0; i < NP; i++) put(i, 0, 0, 0, 0, 0, 1); add(NP, { periph: 9, loose: 0, gain: 1, kind: K.FREE }); }
    if (late()) yield;
    for (const s of [-1, 1]) {
      // Cejas pobladas y canas, con el arco exterior marcado: son media expresión.
      for (let k = 0; k < 120; k++) {
        const u = R(), x0 = 0.095 + 0.45 * u, y0 = 0.268 + 0.05 * Math.sin(Math.PI * Math.min(1, u * 1.05) * 0.8) - 0.05 * u * u + (R() - 0.5) * 0.05 * (1 - 0.6 * u), L = 0.09 + R() * 0.06, rise = 0.75 - 1.5 * u;
        front((t) => [s * (x0 + L * t), y0 + L * t * rise * 0.45 - 0.02 * t * t], (t) => 0.012 + 0.02 * t, { periph: 0.03, loose: 0.2, gain: 1.0, kind: K.BROW, wide: 0.3, w: () => ({ brow: 1, browIn: ss(0.36, 0.1, x0), lidU: 0, lidL: 0 }) });
        if (late()) yield;
      }
      // Labios: el contorno interior (la abertura), el borde del bermellón y fibras verticales que dan cuerpo.
      const top = (x: number): number => { const t = x / 0.25; return (-0.592 + 0.014 * Math.exp(-((x - 0.055) ** 2) / 0.0016)) * (1 - t * t) + YM * t * t; };
      const bot = (x: number): number => { const t = x / 0.25; return -0.715 * (1 - t * t) + YM * t * t; };
      const lip = (gain: number, wide: number): Opt => ({ periph: 0, loose: 0, gain, wide, kind: K.LIP });
      for (const h of [0, 1]) { // dos tramos por lado para que la curva sea limpia
        const xa = 0.125 * h, xb = 0.125 * (h + 1);
        front((t) => [s * (xa + (xb - xa) * t * 1.02), YM + 0.006], () => 0.006, lip(1.75, 0.5));
        front((t) => [s * (xa + (xb - xa) * t * 1.02), YM - 0.006], () => 0.006, lip(1.25, 0.3));
        front((t) => { const x = xa + (xb - xa) * t * 1.02; return [s * x, top(Math.min(x, 0.25))]; }, () => 0.006, lip(0.75 - 0.2 * h, 0.1));
        front((t) => { const x = xa + (xb - xa) * t * 1.02; return [s * x, bot(Math.min(x, 0.25))]; }, () => 0.006, lip(0.62 - 0.3 * h, 0.1));
      }
      for (const h of [0, 1]) for (let j = 1; j <= 3; j++) { // el cuerpo de los labios: líneas que siguen su curva, más luz en el inferior
        const xa = 0.115 * h, xb = 0.115 * (h + 1), q = j / 4;
        if (j < 3) front((t) => { const x = xa + (xb - xa) * t * 1.02; return [s * x, YM + 0.006 + (top(x) - YM - 0.006) * (j / 3)]; }, () => 0.005, lip(0.26, -0.2));
        front((t) => { const x = xa + (xb - xa) * t * 1.02; return [s * x, YM - 0.006 + (bot(x) - YM + 0.006) * q]; }, () => 0.005, lip((j === 2 ? 0.5 : 0.3) * (1 - 0.4 * h), -0.2));
      }
      if (late()) yield;
      // Las líneas de la edad: surco nasolabial, patas de gallo, ojera, entrecejo y filtrum.
      for (let k = 0; k < 3; k++) { const o = k * 0.012; front((t) => [s * (0.175 + o + 0.15 * t - 0.03 * Math.sin(Math.PI * t)), -0.34 - 0.31 * t + o * 0.5], () => 0.004, { periph: 0.05, loose: 0, gain: 0.9 - k * 0.2, kind: K.LINE }); }
      for (let k = 0; k < 3; k++) { const a = -0.5 + k * 0.42; front((t) => [s * (EYE.x + EYE.halfW + 0.035 + 0.1 * t * Math.cos(a)), EYE.y + 0.1 * t * Math.sin(a)], () => 0.004, { periph: 0.05, loose: 0, gain: 0.62, kind: K.LINE }); }
      front((t) => [s * (EYE.x - 0.13 + 0.27 * t), EYE.y - 0.115 - 0.03 * Math.sin(Math.PI * t)], () => 0.004, { periph: 0.05, loose: 0, gain: 0.34, kind: K.LINE });
      front((t) => [s * (0.045 + 0.012 * t), 0.2 + 0.13 * t], () => 0.004, { periph: 0.05, loose: 0, gain: 0.3, kind: K.LINE, w: () => ({ brow: 0.5, browIn: 1 }) });
      front((t) => [s * (0.03 + 0.012 * t), -0.455 - 0.1 * t], () => 0.004, { periph: 0.05, loose: 0, gain: 0.3, kind: K.LINE });
    }
    for (const [y0, wd, gn] of [[0.5, 0.4, 0.44], [0.63, 0.36, 0.34]] as const) for (const s of [-1, 1]) { // arrugas de la frente
      front((t) => { const x = s * wd * t; return [x, y0 + 0.022 * Math.cos((x / wd) * 1.9) - 0.01]; }, () => 0.004, { periph: 0.08, loose: 0, gain: gn, kind: K.LINE, w: () => ({ brow: 0.45 }) });
    }
    if (late()) yield;
    yield* grow([-0.95, 0.95, -1.25, 1.3, -1.15, 1.2], { skin: 2700 });
    // Barba corta y cana, perfilada: mandíbula, mentón y un bigote fino que deja ver el labio.
    for (let n = 0, tries = 0; n < 1500 && tries < 40000; tries++) {
      if (!seedPoint([-0.7, 0.7, -1.15, -0.3, -0.15, 1.05], sp)) continue;
      let x = sp[0]!, y = sp[1]!, z = sp[2]!; const ax = Math.abs(x), g0 = grad(x, y, z);
      const stache = ax < 0.27 && y < -0.44 && y > -0.56 && z > 0.78 && ax > 0.018;
      const beard = y < -0.8 + 0.52 * ss(0.3, 0.6, ax) && z > -0.2 && g0.y > -0.8 && !(ax < 0.3 && y > -0.78);
      if (!(stache || beard) || inMouth(ax, y, z)) continue;
      n++;
      const jit = (R() - 0.5) * 0.5, sg = x < 0 ? -1 : 1; let valid = 0;
      for (let i = 0; i < 5; i++) {
        const g = grad(x, y, z), t = i / 4; put(i, x + g.x * (0.006 + 0.018 * t), y + g.y * (0.006 + 0.018 * t), z + g.z * (0.006 + 0.018 * t), g.x, g.y, g.z); valid++;
        let fx = sg * (stache ? 0.9 : 0.12) + jit * 0.3, fy = -1, fz = 0.1; const dn = fx * g.x + fy * g.y + fz * g.z; fx -= g.x * dn; fy -= g.y * dn; fz -= g.z * dn; const l = len(fx, fy, fz) || 1;
        x += (fx / l) * 0.014; y += (fy / l) * 0.014; z += (fz / l) * 0.014; const g2 = grad(x, y, z); x -= g2.x * g2.d; y -= g2.y * g2.d; z -= g2.z * g2.d;
      }
      add(valid, { periph: 0.15 + R() * 0.1, loose: 0.15, gain: 0.95 + R() * 0.35, kind: K.HAIR });
      if (late()) yield;
    }
    // Pelo en mechones peinados hacia atrás: cada guía arrastra una veintena de filamentos que se juntan en la punta.
    const gp = new Float32Array(NP * 6);
    for (const [box, count] of [[[-0.95, 0.95, -0.5, 1.3, -1.15, 1.0], 82], [[-0.7, 0.7, 0.45, 1.2, 0.1, 0.9], 70]] as const) for (let lock = 0, tries = 0; lock < count && tries < 20000; tries++) {
      if (!seedPoint(box as unknown as number[], sp)) continue;
      let x = sp[0]!, y = sp[1]!, z = sp[2]!; if (y < -1.1 || !isHair(Math.abs(x), y, z)) continue;
      lock++;
      const jit = (R() - 0.5) * 0.18, quiff = ss(0.05, 0.5, z) * ss(0.45, 0.8, y), step = 0.085 + R() * 0.03, rise = 0.03 + R() * 0.04 + 0.1 * quiff, curl = R() * 0.02;
      for (let i = 0; i < NP; i++) { // la guía
        const g = grad(x, y, z); gp.set([x, y, z, g.x, g.y, g.z], i * 6);
        hairFlow(x, y, z, g, fdir, jit); x += fdir[0]! * step; y += fdir[1]! * step; z += fdir[2]! * step;
        const g2 = grad(x, y, z); x -= g2.x * g2.d; y -= g2.y * g2.d; z -= g2.z * g2.d;
      }
      const nx = gp[3]!, ny = gp[4]!, nz = gp[5]!, lockGain = 0.4 + R() * 0.28 + 0.6 * ss(0.4, 0.6, Math.abs(gp[0]!)) * ss(-0.5, 0.0, gp[2]!); // sienes plateadas
      for (let c = 0; c < 23; c++) {
        let ox = R() - 0.5, oy = R() - 0.5, oz = R() - 0.5; const dn = ox * nx + oy * ny + oz * nz; ox -= nx * dn; oy -= ny * dn; oz -= nz * dn;
        const ol = (0.12 * Math.sqrt(R())) / (len(ox, oy, oz) || 1), up = R() * 0.02;
        for (let i = 0; i < NP; i++) {
          const t = i / (NP - 1), q = i * 6, k = ol * (1 - 0.6 * t), lift = 0.012 + up + rise * Math.pow(Math.sin(Math.PI * Math.min(1, t * 1.08)), 0.8) + curl * t * t;
          put(i, gp[q]! + ox * k + gp[q + 3]! * lift, gp[q + 1]! + oy * k + gp[q + 4]! * lift, gp[q + 2]! + oz * k + gp[q + 5]! * lift, gp[q + 3]!, gp[q + 4]!, gp[q + 5]!);
        }
        add(NP, { periph: 0.3 + 0.25 * ss(0.4, -0.6, gp[2]!) + R() * 0.12, loose: 0.45 + R() * 0.6, gain: lockGain + (c < 4 ? 0.28 : 0), kind: K.HAIR });
      }
      if (late()) yield;
    }
    yield* grow([-2.05, 2.05, -3.1, -1.1, -1.1, 0.9], { neck: 430, torso: 1750, fringe: 240 });
    for (const s of [-1, 1]) for (let k = 0; k < 4; k++) for (let seg = 0; seg < 5; seg++) { // cruce de la chaqueta: líneas que caen en V
      const o = k * 0.05;
      front((t) => { const u = (seg + t * 1.08) / 5; return [s * (0.5 + o - (0.44 + o * 0.6) * u ** 1.3), -1.72 - 1.3 * u]; }, () => 0.03, { periph: 0.5 + 0.09 * seg, loose: 0.1 + 0.08 * seg, gain: k === 0 ? 0.8 : 0.42 });
      if (late()) yield;
    }
    for (let k = 0; k < 3; k++) for (let seg = 0; seg < 12; seg++) { // cuello alto, abierto por delante
      for (let i = 0; i < NP; i++) {
        const th = 0.3 + ((seg + (i / (NP - 1)) * 1.06) / 12) * (Math.PI * 2 - 0.6);
        let x = 0.5 * Math.sin(th), y = -1.44 - k * 0.055 - 0.1 * Math.cos(th), z = -0.2 + 0.5 * Math.cos(th);
        for (let q = 0; q < 5; q++) { const g = grad(x, y, z); x -= g.x * g.d; y -= g.y * g.d * 0.2; z -= g.z * g.d; }
        const g = grad(x, y, z); put(i, x + g.x * 0.05, y, z + g.z * 0.05, g.x, g.y, g.z);
      }
      add(NP, { periph: 0.4, loose: 0.05, gain: k === 0 ? 0.85 : 0.45 });
      if (late()) yield;
    }
  }

  /** La cáscara: un rayo por vértice hacia el eje del busto. Da el volumen y tapa lo que queda detrás. */
  function* shell(): Generator<void> {
    const RF = 2.75, zc = (y: number): number => -0.12 - 0.12 * ss(-0.7, -1.6, y);
    for (let r = 0; r < ROWS; r++) {
      const isCap = r < CAPN, phi = isCap ? (1 - r / CAPN) * Math.PI * 0.5 : 0, y0 = isCap ? 0.3 : ys[r - CAPN]!;
      for (let c = 0; c < SH_COLS; c++) {
        const s = (2 * c) / SH_COLS - 1, th = Math.PI * s - 0.5 * Math.sin(Math.PI * s); // columnas más densas en la cara
        const dx = Math.sin(th) * Math.cos(phi), dy = Math.sin(phi), dz = Math.cos(th) * Math.cos(phi);
        const tilt = isCap ? 0 : 0.8 * ss(-0.74, -0.9, y0) * ss(-1.45, -1.2, y0); // bajo la mandíbula los rayos suben, para no rozarla
        let t = 0, x = 0, y = 0, z = 0, hit = false;
        for (let i = 0; i < 110; i++) {
          x = dx * (RF - t); y = y0 + (dy - tilt) * (RF - t); z = zc(y0) + dz * (RF - t);
          const d = sdf(x, y, z); if (d < 0.0006) { hit = true; break; } t += d * 0.88; if (t > RF) break;
        }
        if (!hit) { x = 0; y = y0; z = zc(y0); }
        const v = r * SH_COLS + c, g = grad(x, y, z), w = rig(x, y, z), ax = Math.abs(x);
        let nx = g.x, ny = g.y, nz = g.z;
        if (inEyeBox(ax, y, z)) { // en el ojo, la normal es la de una esfera limpia
          const ex = (x - Math.sign(x) * EYE.x) / EYE.r, ey = (y - EYE.y) / EYE.r, k = ss(1, 0.7, ((ax - EYE.x) / (EYE.halfW + 0.035)) ** 2 + ((y - EYE.y - 0.01) / 0.095) ** 2);
          const ez = Math.sqrt(Math.max(0.05, 1 - ex * ex - ey * ey)); nx += (ex - nx) * k; ny += (ey - ny) * k; nz += (ez - nz) * k;
        }
        S.pos.set([x, y, z], v * 3); S.nrm.set([nx, ny, nz], v * 3);
        S.b.set([w.head, w.jaw, hit ? ss(-3.0, -2.15, y) : 0, y > -1.1 ? [-0.16, -0.08, 0, 0.08, 0.16].reduce((k, o) => k + (isHair(ax, y + o, z) ? 0.2 : 0), 0) : 0], v * 4);
        S.c.set([u8(w.lipU), u8(w.lipL), u8(w.corner), u8(w.cheek)], v * 4); S.d.set([u8(w.brow), u8(w.browIn), 0, 0], v * 4);
      }
      if (late()) yield;
    }
    for (let r = 0, o = 0; r < ROWS - 1; r++) for (let c = 0; c < SH_COLS; c++) {
      const a = r * SH_COLS + c, b = r * SH_COLS + ((c + 1) % SH_COLS), d = a + SH_COLS, e = b + SH_COLS;
      S.index[o++] = a; S.index[o++] = d; S.index[o++] = b; S.index[o++] = b; S.index[o++] = d; S.index[o++] = e;
    }
    S.ready = true;
  }
  function* all(): Generator<void> { yield* run(); yield* shell(); }
  const it = all();
  return { W, S, step(ms) { if (W.done) return true; const t0 = performance.now(); deadline = t0 + ms; W.done = it.next().done === true; W.ms += performance.now() - t0; return W.done; } };
}
