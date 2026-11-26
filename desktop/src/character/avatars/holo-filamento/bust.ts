// Busto procedural de Drakter (holo): un SDF anatómico (cráneo, órbitas, pómulos, nariz, labios, mandíbula, pelo, cuello y traje)
// del que salen DOS cosas: una malla sólida (surface nets) que da cuerpo y oculta lo de detrás, y miles de hebras que lo dibujan a plumilla.
// Todo se genera por código y con semilla fija: no hay modelos ni texturas de terceros.
// El trabajo es incremental (createWeaver().step(ms)): se reparte en fotogramas y nunca bloquea el hilo principal.
// Ejes: +x derecha de pantalla, +y arriba, +z hacia el espectador. La cabeza mide ~2,3 unidades.

export const NP = 8; // puntos por hebra
export const MAXS = 9000; // hebras reservadas
export const MAXV = 62000; // vértices de malla reservados
export const EYE = { x: 0.3, y: 0.085, z: 0.565, r: 0.17, halfW: 0.16, up: 0.07, low: 0.052, lid: 0.022 };
export const PIVOT = [0, -0.95, -0.15] as const; // base del cráneo: gira la cabeza
export const KNOT = [0, -1.54, 0.36] as const; // el nudo de la corbata: el núcleo de luz
export const MOUTH = [0, -0.61, 0.84] as const;
export const K = { SKIN: 0, EYE: 1, GLOW: 2, EMBER: 3, TEETH: 5, HAIR: 6 } as const;
export const FLAG = { SKIN: 0, EYE: 1, HAIR: 2, CLOTH: 3 } as const;

export interface Solid { verts: number; indices: number; pos: Float32Array; nrm: Float32Array; b: Float32Array; c: Uint8Array; d: Uint8Array; index: Uint32Array }
export interface Weave {
  strands: number; done: boolean; ms: number; solid: Solid; phase: string; prof: Record<string, number>;
  pos: Float32Array; dir: Float32Array; nrm: Float32Array;
  a: Float32Array; // lado, t, semilla, periferia
  b: Float32Array; // pesoCabeza, pesoMandíbula, soltura, ganancia   (en la malla: cabeza, mandíbula, tipo de superficie, 0)
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
/** Cápsula de radio variable (r1 en a, r2 en b): huesos largos, nariz, cuello. */
function cone(x: number, y: number, z: number, ax: number, ay: number, az: number, bx: number, by: number, bz: number, r1: number, r2: number): number {
  const pax = x - ax, pay = y - ay, paz = z - az, bax = bx - ax, bay = by - ay, baz = bz - az;
  let h = (pax * bax + pay * bay + paz * baz) / (bax * bax + bay * bay + baz * baz); h = h < 0 ? 0 : h > 1 ? 1 : h;
  return len(pax - bax * h, pay - bay * h, paz - baz * h) - (r1 + (r2 - r1) * h);
}
const cap = (x: number, y: number, z: number, ax: number, ay: number, az: number, bx: number, by: number, bz: number, r: number): number => cone(x, y, z, ax, ay, az, bx, by, bz, r, r);
const sph = (x: number, y: number, z: number, cx: number, cy: number, cz: number, r: number): number => len(x - cx, y - cy, z - cz) - r;

/** Piel: cabeza y cuello. Caballero de 55-60: frente alta, ojos hundidos bajo la ceja, pómulo, nariz recta, mandíbula firme. */
export function skinD(x: number, y: number, z: number): number {
  const ax = Math.abs(x);
  let d = 1e9;
  if (y > -0.6) { const far = len(x, y - 0.05, z) - 1.3; if (far > 0.3) return far; } // lejos de la cabeza basta una cota
  if (y > -1.5) {
    d = ell(x, y, z, 0, 0.34, -0.14, 0.75, 0.8, 0.93); // bóveda craneal
    d = smin(d, ell(x, y, z, 0, 0.32, 0.2, 0.665, 0.6, 0.57), 0.18); // frontal
    d = smin(d, ell(x, y, z, 0, -0.3, 0.2, 0.61, 0.7, 0.6), 0.22); // macizo facial
    d = smin(d, ell(ax, y, z, 0.475, -0.12, 0.46, 0.215, 0.15, 0.22), 0.17); // pómulo marcado
    d = smin(d, cap(ax, y, z, 0.5, -0.1, 0.3, 0.7, -0.03, -0.02, 0.05), 0.16); // arco cigomático, suave
    d = smin(d, ell(ax, y, z, 0.34, -0.46, 0.44, 0.24, 0.28, 0.24), 0.22); // mejilla con carne
    d = smin(d, cap(ax, y, z, 0.13, -0.94, 0.52, 0.46, -0.69, -0.06, 0.14), 0.16); // cuerpo de la mandíbula
    d = smin(d, cap(ax, y, z, 0.46, -0.67, -0.02, 0.53, -0.2, -0.02, 0.075), 0.18); // rama de la mandíbula
    d = smin(d, ell(ax, y, z, 0.42, -0.43, 0.16, 0.12, 0.27, 0.26), 0.2); // masetero
    d = smax(d, -ell(ax, y, z, 0.72, 0.3, 0.34, 0.1, 0.2, 0.26), 0.12); // sien hundida
    d = smin(d, ell(x, y, z, 0, -0.95, 0.6, 0.2, 0.15, 0.16), 0.14); // mentón
    d = smin(d, ell(ax, y, z, 0.34, -0.82, 0.36, 0.15, 0.12, 0.17), 0.14); // caída de la mejilla (la edad)
    d = smin(d, ell(x, y, z, 0, -0.9, 0.05, 0.42, 0.2, 0.5), 0.2); // suelo de la boca
    d = smin(d, cap(ax, y, z, 0.08, 0.3, 0.785, 0.47, 0.3, 0.66, 0.072), 0.11); // arco superciliar, marcado
    d = smin(d, sph(x, y, z, 0, 0.28, 0.78, 0.085), 0.1); // glabela
    d = smax(d, -ell(ax, y, z, EYE.x + 0.01, 0.075, 0.87, 0.235, 0.135, 0.21), 0.07); // órbita
    d = smin(d, ell(x, y, z, 0, -0.1, 0.9, 0.085, 0.24, 0.12), 0.09); // pirámide nasal
    d = smin(d, cone(x, y, z, 0, 0.2, 0.8, 0, -0.22, 1.03, 0.045, 0.06), 0.06); // dorso
    d = smin(d, ell(x, y, z, 0, -0.25, 1.035, 0.075, 0.065, 0.075), 0.06); // punta
    d = smin(d, ell(ax, y, z, 0.105, -0.3, 0.94, 0.055, 0.05, 0.065), 0.07); // aletas
    d = smin(d, ell(x, y, z, 0, -0.335, 0.96, 0.06, 0.035, 0.07), 0.04); // columela
    d = smax(d, -sph(ax, y, z, 0.06, -0.375, 0.985, 0.026), 0.02); // fosas
    d = smin(d, ell(x, y, z, 0, -0.57, 0.68, 0.27, 0.2, 0.16), 0.14); // bozo
    d = smax(d, -cap(ax, y, z, 0.19, -0.33, 0.9, 0.34, -0.63, 0.76, 0.03), 0.08); // surco nasogeniano, hondo
    d = smax(d, -cap(ax, y, z, 0.27, -0.65, 0.76, 0.3, -0.84, 0.67, 0.016), 0.05); // línea de marioneta
    d = smax(d, -cap(x, y, z, 0, -0.42, 0.9, 0, -0.52, 0.895, 0.02), 0.03); // filtrum
    d = smin(d, cap(ax, y, z, 0, -0.562, 0.872, 0.2, -0.592, 0.775, 0.027), 0.04); // labio superior
    d = smin(d, sph(x, y, z, 0, -0.572, 0.882, 0.023), 0.03); // tubérculo
    d = smin(d, cap(ax, y, z, 0, -0.656, 0.862, 0.17, -0.634, 0.775, 0.041), 0.04); // labio inferior
    d = smax(d, -cap(ax, y, z, 0, -0.604, 0.915, 0.25, -0.607, 0.765, 0.014), 0.022); // la línea de la boca
    d = smax(d, -ell(x, y, z, 0, -0.76, 0.81, 0.2, 0.04, 0.07), 0.06); // surco bajo el labio
    d = smin(d, ell(ax, y, z, EYE.x, -0.065, 0.715, 0.14, 0.024, 0.05), 0.07); // bolsa leve bajo el ojo
    // Ojo: globo hundido bajo la ceja, y párpados como una cáscara con abertura almendrada.
    const shell = smax(sph(ax, y, z, EYE.x, EYE.y, EYE.z, EYE.r + EYE.lid), -ell(ax, y, z, EYE.x, EYE.y + (EYE.up - EYE.low) * 0.5, EYE.z + EYE.r, EYE.halfW + 0.014, (EYE.up + EYE.low) * 0.5 + 0.007, 0.14), 0.005);
    d = smin(d, shell, 0.03);
    d = smin(d, ell(ax, y, z, EYE.x + 0.06, EYE.y + 0.15, 0.7, 0.14, 0.026, 0.05), 0.035); // párpado superior algo caído por fuera
    d = Math.min(d, sph(ax, y, z, EYE.x, EYE.y, EYE.z, EYE.r));
    // Oreja: pabellón con concha vaciada y lóbulo.
    let ear = ell(ax, y, z, 0.76, 0.02, -0.12, 0.055, 0.22, 0.14); ear = smax(ear, -ell(ax, y, z, 0.82, 0.04, -0.09, 0.045, 0.14, 0.08), 0.03); ear = smin(ear, sph(ax, y, z, 0.74, -0.19, -0.07, 0.052), 0.04);
    d = smin(d, ear, 0.05);
  }
  d = smin(d, cone(x, y, z, 0, -0.75, -0.1, 0, -1.9, -0.22, 0.43, 0.5), 0.2); // cuello
  if (y > -2.0 && y < -0.4) {
    d = smin(d, cap(ax, y, z, 0.37, -0.55, -0.27, 0.09, -1.78, 0.12, 0.08), 0.1); // esternocleidomastoideo
    d = smin(d, sph(x, y, z, 0, -1.27, 0.24, 0.06), 0.1); // nuez
  }
  return d;
}
/** Pelo: una masa con volumen, peinada hacia atrás, con tupé y entradas. */
export function hairD(x: number, y: number, z: number): number {
  if (y < -0.6) return 1e9;
  const ax = Math.abs(x);
  let d = ell(x, y, z, 0, 0.42, -0.16, 0.815, 0.87, 1.0);
  d = smin(d, ell(x, y, z, 0.07, 0.98, 0.28, 0.52, 0.24, 0.46), 0.18); // tupé
  const hl = Math.max(-0.38, 0.8 - (0.6 - z) * 0.98) + 0.14 * ss(0.22, 0.5, ax) * ss(0.2, 0.55, z); // línea del pelo, con entradas
  d = smax(d, (hl - y) * 0.8, 0.06);
  return smax(d, -sph(ax, y, z, 0.8, 0.0, -0.1, 0.21), 0.05); // despeja la oreja
}
/** Traje: hombros, pecho, cuello de camisa, nudo de corbata y solapas en relieve. */
export function clothD(x: number, yy: number, z: number): number {
  const y = yy - 0.22; // el traje sube: cuello corto y hombros cerca de la mandíbula
  if (y > -1.2) return 1e9;
  const ax = Math.abs(x);
  let d = ell(x, y, z, 0, -2.6, -0.25, 1.85, 0.85, 0.72); // hombros
  d = smin(d, ell(x, y, z, 0, -2.75, 0.02, 1.15, 0.95, 0.68), 0.3); // pecho
  d = smin(d, cap(ax, y, z, 0.25, -1.6, -0.25, 1.2, -2.05, -0.3, 0.28), 0.3); // trapecios bajo la chaqueta
  const rr = Math.hypot(x, z + 0.2); // cuello de la camisa: un anillo inclinado alrededor del cuello
  d = smin(d, Math.hypot(rr - 0.49, (y + 1.56 + 0.3 * (z + 0.2)) * 0.5) - 0.065, 0.05);
  d = smin(d, ell(x, y, z, 0, -1.76, 0.3, 0.1, 0.115, 0.085), 0.03); // nudo
  d = smin(d, cone(x, y, z, 0, -1.86, 0.31, 0, -3.05, 0.68, 0.07, 0.11), 0.03); // corbata
  d = smin(d, cone(ax, y, z, 0.52, -1.72, 0.08, 0.14, -3.0, 0.62, 0.11, 0.09), 0.05); // solapa
  d = smin(d, ell(ax, y, z, 1.48, -2.3, -0.24, 0.46, 0.3, 0.44), 0.25); // hombrera
  return d;
}
export function sdf(x: number, y: number, z: number): number { return smin(smin(skinD(x, y, z), hairD(x, y, z), 0.025), clothD(x, y, z), 0.035); }

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
  const solid: Solid = { verts: 0, indices: 0, pos: new Float32Array(MAXV * 3), nrm: new Float32Array(MAXV * 3), b: new Float32Array(MAXV * 4), c: new Uint8Array(MAXV * 4), d: new Uint8Array(MAXV * 4), index: new Uint32Array(MAXV * 6) };
  const W: Weave = { strands: 0, done: false, ms: 0, solid, phase: 'rasgos', prof: {}, pos: new Float32Array(V * 3), dir: new Float32Array(V * 3), nrm: new Float32Array(V * 3), a: new Float32Array(V * 4), b: new Float32Array(V * 4),
    c: new Uint8Array(V * 4), d: new Uint8Array(V * 4), e: new Float32Array(V * 4), f: new Float32Array(V * 2) };
  const R = rng(0x51a7e7), pts = new Float32Array(NP * 3), nrs = new Float32Array(NP * 3);
  let deadline = 0; const late = (): boolean => performance.now() > deadline;
  const u8 = (v: number): number => Math.max(0, Math.min(255, v * 255));

  /** Pesos del rig facial a partir de la posición en reposo. Los comparten la malla y las hebras. */
  const rig = (x: number, y: number, z: number): Record<WKey, number> => {
    const ax = Math.abs(x), front = ss(0.35, 0.6, z);
    const g = (dx: number, dy: number, dz: number, r: number): number => Math.exp(-(dx * dx + dy * dy + dz * dz) / (r * r));
    const brow = Math.exp(-(((y - 0.31) / 0.12) ** 2)) * ss(0.72, 0.5, ax) * front;
    const xf = Math.sqrt(Math.max(0, 1 - ((ax - EYE.x) / (EYE.halfW * 1.18)) ** 2)) * front; // los párpados se cierran más por el centro
    return {
      head: ss(-1.42, -0.95, y),
      jaw: ss(-0.585, -0.635, y) * ss(-0.3, 0.12, z) * ss(-1.5, -1.08, y) * (1 - 0.5 * ss(0.3, 0.7, ax) * ss(-0.55, -0.2, y)),
      lipU: g(0, y + 0.555, z - 0.88, 0.12) * ss(0.44, 0.2, ax) * ss(-0.63, -0.6, y),
      lipL: g(0, y + 0.665, z - 0.86, 0.12) * ss(0.4, 0.18, ax) * ss(-0.6, -0.63, y),
      corner: g(ax - 0.27, y + 0.605, z - 0.76, 0.17), cheek: g(ax - 0.42, y + 0.2, z - 0.55, 0.28),
      brow, browIn: brow * ss(0.36, 0.08, ax),
      lidU: xf * ss(0.27, EYE.y + EYE.up + 0.012, y) * ss(EYE.y + 0.025, EYE.y + 0.05, y),
      lidL: xf * ss(-0.11, EYE.y - EYE.low - 0.012, y) * ss(EYE.y - 0.02, EYE.y - 0.04, y),
    };
  };
  /** Vuelca la hebra (pts/nrs, con `valid` puntos reales) a los búferes: dos vértices por punto (cinta). */
  const add = (valid: number, o: Opt): void => {
    if (valid < 3 || W.strands >= MAXS) return;
    const seed = R(), mid = Math.min(valid - 1, NP >> 1) * 3, r2 = R();
    const out = 0.12 + 1.5 * r2 * r2 * r2; // posición dispersa: la constelación conserva el fantasma de la silueta
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
    for (const s of [-1, 1]) { const vx = x - s * EYE.x, vy = y - EYE.y, w = 1.3 * Math.exp(-(vx * vx + vy * vy + (z - 0.72) ** 2) / 0.08), l = Math.hypot(vx, vy) || 1; fx += (s * -vy * w) / l; fy += (s * vx * w) / l; }
    { const vx = x, vy = y + 0.6, w = 3 * Math.exp(-(vx * vx + vy * vy + (z - 0.8) ** 2) / 0.09), l = Math.hypot(vx, vy) || 1; fx += (-vy * w) / l; fy += (vx * w) / l; }
    { const w = 2.5 * Math.exp(-(x * x) / 0.012) * ss(0.36, 0.2, y) * ss(-0.36, -0.2, y) * ss(0.6, 0.8, z); fy -= w; }
    { const w = ss(0.2, 0.32, y) * ss(0.15, 0.45, z) * ss(0.02, 0.1, Math.abs(x) + (y - 0.2)), l = Math.hypot(x, y - 0.1) || 1; fx = fx * (1 - w) + (x / l) * 3 * w; fy = fy * (1 - w) + ((y - 0.1) / l) * 3 * w; fz *= 1 - w; } // frontal en abanico
    { const w = 1.7 * ss(0.2, 0.36, Math.abs(x)) * ss(-0.05, -0.25, y) * ss(-1.05, -0.8, y); fx -= Math.sign(x) * 0.45 * w; fy -= w; fz += 0.25 * w; } // la mejilla cae hacia el mentón
    { const w = 2.2 * ss(-0.95, -1.15, y) * ss(-1.75, -1.45, y); fy -= w; fx *= 1 - w * 0.3; } // tendones del cuello
    { const w = 2.4 * ss(-1.65, -1.95, y) * ss(-0.2, 0.2, z); fx += -Math.sign(x) * 0.6 * w * ss(0.05, 0.3, Math.abs(x)); fy -= w; } // V de las solapas
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
  const inEye = (ax: number, y: number, z: number): boolean => ((ax - EYE.x) / (EYE.halfW + 0.02)) ** 2 + ((y - EYE.y - 0.009) / 0.08) ** 2 < 1 && z > 0.45;
  const inMouth = (ax: number, y: number, z: number): boolean => ax < 0.27 && y < -0.535 && y > -0.7 && z > 0.6;
  const isHair = (x: number, y: number, z: number): boolean => hairD(x, y, z) < skinD(x, y, z) + 0.006;
  const fdir = [1, 0, 0];
  /** Proyecta un punto al azar de la caja sobre la superficie. Devuelve false si no converge. */
  const seedPoint = (box: number[], p: number[]): boolean => {
    let x = box[0]! + R() * (box[1]! - box[0]!), y = box[2]! + R() * (box[3]! - box[2]!), z = box[4]! + R() * (box[5]! - box[4]!);
    for (let i = 0; i < 7; i++) { const g = grad(x, y, z); x -= g.x * g.d; y -= g.y * g.d; z -= g.z * g.d; if (Math.abs(g.d) < 0.0015) { p[0] = x; p[1] = y; p[2] = z; return y > -3.05 && y < 1.5; } }
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
        if (inEye(ax, y, z) || inMouth(ax, y, z) || isHair(x, y, z)) continue;
        const beardTop = -0.56 + 0.62 * ss(0.36, 0.7, ax);
        kind = quota.beard && y < beardTop && z > -0.24 && !(G.y < -0.8 && y < -1.0) && !(ax < 0.3 && y > -0.52) ? 'beard' : 'skin';
      } else kind = y > -1.4 && clothD(x, y, z) > skinD(x, y, z) ? 'neck' : y > -2.6 ? 'torso' : 'fringe';
      if (!quota[kind]) continue;
      quota[kind]!--; left--;
      const g0 = grad(x, y, z); fdir[0] = g0.z; fdir[1] = 0; fdir[2] = -g0.x;
      const jit = (R() - 0.5) * 0.5, y0 = y, z0 = z;
      if (kind === 'fringe') { // flecos: el busto se deshila hacia abajo
        const L = 0.5 + R() * 0.8; for (let i = 0; i < NP; i++) { const t = i / (NP - 1); put(i, x + Math.sin(t * 3 + jit * 9) * 0.03, y - t * L, z + 0.01, g0.x, g0.y * 0.3, g0.z); }
        add(NP, { periph: 0.96 + R() * 0.1, loose: 1.5, gain: 0.3 }); continue;
      }
      const beard = kind === 'beard', step = beard ? 0.016 + R() * 0.01 : kind === 'torso' ? 0.05 : 0.034;
      let valid = 0;
      for (let i = 0; i < NP; i++) {
        const g = grad(x, y, z), t = i / (NP - 1);
        if (!beard && i > 0 && (inEye(Math.abs(x), y, z) || inMouth(Math.abs(x), y, z))) break;
        const lift = beard ? 0.01 + 0.04 * t : 0.008;
        put(i, x + g.x * lift, y + g.y * lift, z + g.z * lift, g.x, g.y, g.z); valid++;
        if (beard) beardFlow(x, g, fdir, jit); else flow(x, y, z, g, fdir);
        x += fdir[0]! * step; y += fdir[1]! * step; z += fdir[2]! * step;
        const g2 = grad(x, y, z); x -= g2.x * g2.d; y -= g2.y * g2.d; z -= g2.z * g2.d;
      }
      const down = ss(-1.8, -3.0, y0);
      if (beard) add(valid, { periph: 0.2 + R() * 0.15, loose: 0.25 + R() * 0.25, gain: 0.5 });
      else if (kind === 'skin') add(valid, { periph: 0.08 + 0.22 * ss(0.5, -0.3, z0) + R() * 0.12, loose: 0.08, gain: 0.4 - 0.06 * ss(0.2, 0.34, y0) * ss(0.2, 0.5, z0) });
      else if (kind === 'neck') add(valid, { periph: 0.42 + R() * 0.12, loose: 0.12, gain: 0.5 });
      else add(valid, { periph: 0.52 + 0.42 * down + R() * 0.1, loose: 0.15 + 0.6 * down, gain: 0.26 });
    }
  }

  /** Malla sólida por «surface nets»: un vértice por celda que corta la superficie, proyectado luego al SDF exacto. */
  function* nets(x0: number, x1: number, y0: number, y1: number, z0: number, z1: number, cell: number): Generator<void> {
    const nx = Math.ceil((x1 - x0) / cell) + 1, ny = Math.ceil((y1 - y0) / cell) + 1, nz = Math.ceil((z1 - z0) / cell) + 1, F = new Float32Array(nx * ny * nz), at = (i: number, j: number, k: number): number => i + nx * (j + ny * k);
    // Banda estrecha: una pasada gruesa (1 de cada 27 puntos) decide dónde hace falta evaluar fino; lejos de la superficie basta el signo.
    const Q = 3, mx = Math.ceil(nx / Q), my = Math.ceil(ny / Q), mz = Math.ceil(nz / Q), C = new Float32Array(mx * my * mz), far = cell * Q * 0.9;
    for (let k = 0; k < mz; k++) { for (let j = 0; j < my; j++) for (let i = 0; i < mx; i++) C[i + mx * (j + my * k)] = sdf(x0 + (i * Q + 1) * cell, y0 + (j * Q + 1) * cell, z0 + (k * Q + 1) * cell); if (late()) yield; }
    for (let k = 0; k < nz; k++) for (let j = 0; j < ny; j++) {
      for (let i = 0; i < nx; i++) { const c = C[((i / Q) | 0) + mx * (((j / Q) | 0) + my * ((k / Q) | 0))]!; F[at(i, j, k)] = Math.abs(c) > far ? c : sdf(x0 + i * cell, y0 + j * cell, z0 + k * cell); }
      if (late()) yield;
    }
    const cx = nx - 1, cy = ny - 1, cz = nz - 1, id = new Int32Array(cx * cy * cz).fill(-1), cid = (i: number, j: number, k: number): number => i + cx * (j + cy * k);
    const S = solid;
    for (let k = 0; k < cz; k++) for (let j = 0; j < cy; j++) {
      for (let i = 0; i < cx; i++) {
        let n = 0, px = 0, py = 0, pz = 0, neg = 0;
        const f = [F[at(i, j, k)]!, F[at(i + 1, j, k)]!, F[at(i, j + 1, k)]!, F[at(i + 1, j + 1, k)]!, F[at(i, j, k + 1)]!, F[at(i + 1, j, k + 1)]!, F[at(i, j + 1, k + 1)]!, F[at(i + 1, j + 1, k + 1)]!];
        for (let c = 0; c < 8; c++) if (f[c]! < 0) neg++;
        if (neg === 0 || neg === 8 || S.verts >= MAXV) continue;
        for (let a = 0; a < 8; a++) for (let ax = 1; ax <= 4; ax <<= 1) { // las 12 aristas: a y a|eje
          if (a & ax) continue; const b = a | ax, fa = f[a]!, fb = f[b]!; if (fa < 0 === fb < 0) continue;
          const t = fa / (fa - fb); px += (a & 1) + (ax === 1 ? t : 0); py += ((a >> 1) & 1) + (ax === 2 ? t : 0); pz += ((a >> 2) & 1) + (ax === 4 ? t : 0); n++;
        }
        let x = x0 + (i + px / n) * cell, y = y0 + (j + py / n) * cell, z = z0 + (k + pz / n) * cell;
        const g = grad(x, y, z); x -= g.x * g.d; y -= g.y * g.d; z -= g.z * g.d;
        const v = S.verts++, w = rig(x, y, z), ax = Math.abs(x);
        const flag = sph(ax, y, z, EYE.x, EYE.y, EYE.z, EYE.r) < 0.006 && z > EYE.z ? FLAG.EYE : y < -1.0 && clothD(x, y, z) < skinD(x, y, z) ? FLAG.CLOTH : y > -0.5 && hairD(x, y, z) < skinD(x, y, z) + 0.004 ? FLAG.HAIR : FLAG.SKIN;
        const fw = flag === FLAG.EYE ? 0 : 1, hw = flag === FLAG.HAIR ? 0 : 1; // el globo no se mueve con los párpados ni el pelo con las cejas
        S.pos.set([x, y, z], v * 3); S.nrm.set([g.x, g.y, g.z], v * 3); S.b.set([w.head, w.jaw, flag, 0], v * 4);
        S.c.set([u8(w.lipU), u8(w.lipL), u8(w.corner), u8(w.cheek)], v * 4); S.d.set([u8(w.brow * hw), u8(w.browIn * hw), u8(w.lidU * fw), u8(w.lidL * fw)], v * 4);
        id[cid(i, j, k)] = v;
      }
      if (late()) yield;
    }
    // Cada cuadrilátero se orienta hacia fuera (según de qué lado de la arista está el interior), para poder descartar las caras traseras.
    const quad = (a: number, b: number, c: number, d: number, flip: boolean): void => { if (a < 0 || b < 0 || c < 0 || d < 0 || S.indices + 6 > S.index.length) return; S.index.set(flip ? [a, c, b, a, d, c] : [a, b, c, a, c, d], S.indices); S.indices += 6; };
    for (let k = 1; k < cz; k++) { for (let j = 1; j < cy; j++) for (let i = 1; i < cx; i++) {
      const s = F[at(i, j, k)]! < 0;
      if (s !== F[at(i + 1, j, k)]! < 0) quad(id[cid(i, j - 1, k - 1)]!, id[cid(i, j, k - 1)]!, id[cid(i, j, k)]!, id[cid(i, j - 1, k)]!, !s);
      if (s !== F[at(i, j + 1, k)]! < 0) quad(id[cid(i - 1, j, k - 1)]!, id[cid(i, j, k - 1)]!, id[cid(i, j, k)]!, id[cid(i - 1, j, k)]!, s);
      if (s !== F[at(i, j, k + 1)]! < 0) quad(id[cid(i - 1, j - 1, k)]!, id[cid(i, j - 1, k)]!, id[cid(i, j, k)]!, id[cid(i - 1, j, k)]!, !s);
    } if (late()) yield; }
  }

  function* run(): Generator<void> {
    // ── Rasgos de autor primero: lo primero que se teje es la mirada ──────────────────────────────
    for (const s of [-1, 1]) {
      const ex = s * EYE.x, RL = EYE.r + EYE.lid + 0.006;
      const eyeP = (i: number, rho: number, phi: number): void => { const dx = rho * Math.cos(phi), dy = rho * Math.sin(phi), dz = Math.sqrt(EYE.r ** 2 - rho * rho), k = 1 + 0.006 / EYE.r; put(i, ex + dx * k, EYE.y + dy * k, EYE.z + dz * k, dx / EYE.r, dy / EYE.r, dz / EYE.r); };
      // Iris: hebras radiales finas sobre el iris sombreado; la pupila queda limpia.
      for (let k = 0; k < 34; k++) {
        const phi = (k / 34) * Math.PI * 2 + R() * 0.1, r0 = EYE.r * (0.25 + R() * 0.03), r1 = EYE.r * (0.48 + R() * 0.03);
        for (let i = 0; i < NP; i++) { const t = i / (NP - 1); eyeP(i, r0 + (r1 - r0) * t, phi + 0.5 * t); }
        add(NP, { periph: 0, loose: 0, gain: 0.5, kind: K.EYE });
      }
      for (let k = 0; k < 7; k++) { const p0 = (k / 7) * Math.PI * 2; for (let i = 0; i < NP; i++) eyeP(i, EYE.r * 0.525, p0 + (i / (NP - 1)) * 1.15); add(NP, { periph: 0, loose: 0, gain: 0.9, kind: K.EYE }); }
      // Párpados: líneas sobre la cáscara; el peso sin(a) las cierra en el shader. Pestañas arriba, pliegue, y párpado inferior.
      const lidZ = (dx: number, dy: number): number => EYE.z + Math.sqrt(Math.max(0.0001, RL * RL - dx * dx - dy * dy));
      for (let k = 0; k < 4; k++) for (const half of [0, 1]) {
        for (let i = 0; i < NP; i++) { const a = (half + i / (NP - 1)) * Math.PI * 0.5 * 1.04, dx = -s * (EYE.halfW + k * 0.006) * Math.cos(a), dy = (EYE.up + (k === 0 ? 0 : 0.012 + k * 0.016)) * Math.sin(a); put(i, ex + dx, EYE.y + dy, lidZ(dx, dy) + k * 0.002, dx * 2, dy * 2 + 0.3, 0.9); }
        add(NP, { periph: 0, loose: 0, gain: k === 0 ? 2.2 : 0.6, wide: k === 0 ? 0.5 : 0, w: (i) => ({ lidU: Math.sin((half + i / (NP - 1)) * Math.PI * 0.5) * (k === 0 ? 1 : 0.8 - k * 0.15), lidL: 0, brow: 0, browIn: 0 }) });
      }
      for (let k = 0; k < 2; k++) for (const half of [0, 1]) {
        for (let i = 0; i < NP; i++) { const a = (half + i / (NP - 1)) * Math.PI * 0.5, dx = -s * EYE.halfW * Math.cos(a), dy = -(EYE.low + k * 0.022) * Math.sin(a); put(i, ex + dx, EYE.y + dy, lidZ(dx, dy), dx * 2, dy * 2 - 0.2, 0.9); }
        add(NP, { periph: 0, loose: 0, gain: k === 0 ? 0.95 : 0.35, w: (i) => ({ lidL: Math.sin((half + i / (NP - 1)) * Math.PI * 0.5) * (1 - k * 0.4), lidU: 0, brow: 0, browIn: 0 }) });
      }
      if (late()) yield;
      // Cejas: dos arcos pobladas y legibles, con cola.
      for (let k = 0; k < 110; k++) {
        const u = R(), x0 = 0.105 + 0.42 * u, y0 = 0.272 + 0.032 * Math.sin(Math.PI * Math.min(1, u * 1.05) * 0.8) - 0.012 * u * u + (R() - 0.5) * 0.05 * (1 - 0.6 * u), L = 0.09 + R() * 0.06, rise = 0.4 - 0.7 * u;
        front((t) => [s * (x0 + L * t), y0 + L * t * rise * 0.45 - 0.02 * t * t], (t) => 0.014 + 0.02 * t, { periph: 0.03, loose: 0.2, gain: 1.0, w: () => ({ brow: 1, browIn: ss(0.36, 0.1, x0), lidU: 0 }) });
        if (late()) yield;
      }
      // Bigote recortado: nace bajo la nariz, se abre hacia los lados y deja ver el labio.
      for (let k = 0; k < 105; k++) {
        const x0 = 0.022 + R() * 0.2, y0 = -0.415 - R() * 0.045 - 0.03 * (x0 / 0.22) ** 2, L = 0.085 + R() * 0.07;
        front((t) => [s * (x0 + L * t), y0 - L * (0.2 * t + 0.4 * t * t)], (t) => 0.014 + 0.03 * Math.sin(Math.PI * t) + 0.01 * t, { periph: 0.1, loose: 0.4, gain: 0.55, w: (_i, t) => ({ lipU: 0.7, corner: 0.3 * t, jaw: 0, lipL: 0 }) });
        if (late()) yield;
      }
      // Nariz a plumilla: dos líneas de dorso y el contorno de la aleta.
      front((t) => [s * (0.045 + 0.02 * t), 0.2 - 0.36 * t], () => 0.008, { periph: 0.04, loose: 0, gain: 0.9 });
      front((t) => [s * (0.065 + 0.045 * t), -0.14 - 0.14 * t], () => 0.008, { periph: 0.04, loose: 0, gain: 0.9 });
      front((t) => { const a = 2.2 - 3.3 * t; return [s * (0.13 + 0.072 * Math.cos(a)), -0.315 + 0.075 * Math.sin(a)]; }, () => 0.008, { periph: 0.04, loose: 0, gain: 0.8 });
      front((t) => [s * (0.02 + 0.1 * t), -0.385 + 0.012 * Math.sin(Math.PI * t)], () => 0.008, { periph: 0.04, loose: 0, gain: 1.0 });
      for (let k = 0; k < 3; k++) front((t) => [s * (0.205 + k * 0.012 + 0.14 * t - 0.03 * Math.sin(Math.PI * t)), -0.33 - 0.3 * t], () => 0.008, { periph: 0.05, loose: 0, gain: 1.05 - k * 0.25 }); // surco nasogeniano
      for (let k = 0; k < 4; k++) { const a = -0.62 + k * 0.38; front((t) => [s * (EYE.x + EYE.halfW + 0.03 + 0.09 * t * Math.cos(a)), EYE.y - 0.01 + 0.09 * t * Math.sin(a)], () => 0.008, { periph: 0.05, loose: 0, gain: 0.85 }); } // patas de gallo
      for (let k = 0; k < 3; k++) front((t) => [s * (0.05 + 0.45 * t), 0.47 + k * 0.085 + 0.025 * Math.sin(Math.PI * t) - 0.03 * t * t], () => 0.008, { periph: 0.05, loose: 0, gain: 0.5 }); // líneas de la frente
      front((t) => [s * (0.045 + 0.008 * t), 0.23 + 0.13 * t], () => 0.008, { periph: 0.04, loose: 0, gain: 0.8, w: () => ({ browIn: 0.8, brow: 0.5 }) }); // entrecejo
      front((t) => [s * (0.19 + 0.24 * t), -0.1 + 0.03 * t - 0.01 * Math.sin(Math.PI * t)], () => 0.008, { periph: 0.04, loose: 0, gain: 0.75 }); // bolsa bajo el ojo
      front((t) => [s * (0.27 + 0.035 * t), -0.65 - 0.19 * t], () => 0.008, { periph: 0.05, loose: 0, gain: 0.7, w: () => ({ corner: 0.5, jaw: 0.6 }) }); // marioneta
      // Labios en el mismo lenguaje: contorno, línea de la boca y trama que sigue la curva. Sin relleno.
      for (let j = 0; j < 6; j++) {
        const f = j / 5, edge = j === 0 || j === 5;
        front((t) => { const x = 0.245 * t, top = (-0.527 + 0.016 * Math.exp(-((x - 0.05) ** 2) / 0.0016) - 0.012 * Math.exp(-(x * x) / 0.0006)) * (1 - t * t) - 0.605 * t * t; return [s * x, top + (-0.6 - top) * f]; }, () => 0.007,
          { periph: 0, loose: 0, gain: j === 5 ? 1.7 : edge ? 1.25 : 0.42, wide: j === 5 ? 0.3 : 0, w: (_i, t) => ({ lipU: 1 - 0.4 * t, lipL: 0, corner: t * t, jaw: 0 }) });
        front((t) => { const bot = -0.703 * (1 - t * t) - 0.61 * t * t; return [s * 0.235 * t, -0.612 + (bot + 0.612) * f]; }, () => 0.007,
          { periph: 0, loose: 0, gain: j === 0 ? 1.1 : edge ? 1.25 : 0.42, w: (_i, t) => ({ lipL: 1 - 0.4 * t, lipU: 0, corner: t * t, jaw: 1 - 0.55 * t * t }) });
        if (late()) yield;
      }
      front((t) => [s * (0.25 + 0.035 * t), -0.607 - 0.03 * t * t], () => 0.007, { periph: 0, loose: 0, gain: 1.0, w: () => ({ corner: 1, lipU: 0.2, lipL: 0.2, jaw: 0.45 }) }); // la comisura
    }
    // Interior de la boca: dientes superiores y un fondo de luz; nunca un hueco negro.
    for (let k = 0; k < 15; k++) {
      const x = (k / 14 - 0.5) * 0.3;
      const tz = frontZ(x, -0.604) + 0.008; for (let i = 0; i < NP; i++) put(i, x, -0.6 - (i / (NP - 1)) * 0.05, tz, 0, 0, 1);
      add(NP, { periph: 0, loose: 0, gain: 1, kind: K.TEETH, wide: 2.0, w: () => ({ jaw: 0, lipU: 0, lipL: 0, corner: 0 }) });
    }
    for (let k = 0; k < 8; k++) {
      for (let i = 0; i < NP; i++) { const t = i / (NP - 1) - 0.5; const xx = t * (0.3 - k * 0.012); put(i, xx, -0.615 - k * 0.012, frontZ(xx, -0.604) + 0.004, 0, 0, 1); }
      add(NP, { periph: 0, loose: 0, gain: 1, kind: K.GLOW, wide: 2.4, w: () => ({ jaw: 0.15 + 0.12 * k, lipU: 0, lipL: 0, corner: 0 }) });
    }
    W.phase = 'malla cabeza'; yield* nets(-1.02, 1.02, -1.38, 1.5, -1.25, 1.22, 0.034); // cabeza y cuello, fino
    W.phase = 'piel y barba'; yield* grow([-0.95, 0.95, -1.25, 1.3, -1.15, 1.2], { skin: 1900, beard: 0 });
    // Pelo en mechones sobre la masa de pelo: cada guía arrastra hebras que se juntan en la punta.
    W.phase = 'pelo'; const gp = new Float32Array(NP * 6);
    for (let lock = 0, tries = 0; lock < 146 && tries < 60000; tries++) {
      if (!seedPoint([-0.95, 0.95, -0.5, 1.45, -1.2, 1.0], sp)) continue;
      let x = sp[0]!, y = sp[1]!, z = sp[2]!; if (!isHair(x, y, z)) continue;
      if (lock < 40) { const ax = Math.abs(x), hl = Math.max(-0.38, 0.8 - (0.6 - z) * 0.98) + 0.14 * ss(0.22, 0.5, ax) * ss(0.2, 0.55, z); if (y - hl > 0.13 || z < -0.1) continue; }
      else if (lock < 66 && (Math.abs(x) > 0.34 || z < 0.05 || y < 0.9)) continue; // y otros tantos en lo alto del tupé
      lock++;
      const jit = (R() - 0.5) * 0.2, y0 = y, step = 0.075 + R() * 0.03, rise = 0.012 + R() * 0.035, curl = R() * 0.025;
      for (let i = 0; i < NP; i++) { // la guía
        const g = grad(x, y, z); gp.set([x, y, z, g.x, g.y, g.z], i * 6);
        hairFlow(x, y, z, g, fdir, jit); x += fdir[0]! * step; y += fdir[1]! * step; z += fdir[2]! * step;
        const g2 = grad(x, y, z); x -= g2.x * g2.d; y -= g2.y * g2.d; z -= g2.z * g2.d;
      }
      const silver = ss(0.42, 0.6, Math.abs(gp[0]!)) * ss(-0.55, -0.05, gp[2]!) * ss(0.85, 0.5, gp[1]!); // sienes plateadas
      const nx = gp[3]!, ny = gp[4]!, nz = gp[5]!, lockGain = 0.26 + R() * 0.24 + 0.5 * silver;
      for (let c = 0; c < 18; c++) {
        let ox = R() - 0.5, oy = R() - 0.5, oz = R() - 0.5; const dn = ox * nx + oy * ny + oz * nz; ox -= nx * dn; oy -= ny * dn; oz -= nz * dn;
        const ol = (0.12 * Math.sqrt(R())) / (len(ox, oy, oz) || 1), up = R() * 0.015;
        for (let i = 0; i < NP; i++) {
          const t = i / (NP - 1), q = i * 6, k = ol * (1 - 0.6 * t), lift = 0.012 + up + rise * Math.pow(Math.sin(Math.PI * Math.min(1, t * 1.08)), 0.8) + curl * t * t;
          put(i, gp[q]! + ox * k + gp[q + 3]! * lift, gp[q + 1]! + oy * k + gp[q + 4]! * lift, gp[q + 2]! + oz * k + gp[q + 5]! * lift, gp[q + 3]!, gp[q + 4]!, gp[q + 5]!);
        }
        add(NP, { periph: 0.3 + 0.25 * ss(0.4, -0.6, gp[2]!) + R() * 0.12, loose: 0.35 + R() * 0.5, gain: lockGain + (c < 4 ? 0.3 : 0), kind: K.HAIR, wide: 0.25 * silver, think: y0 > 0.6 && R() < 0.5 ? 1 : 0 });
      }
      if (late()) yield;
    }
    W.phase = 'malla traje'; yield* nets(-2.1, 2.1, -3.14, -1.02, -1.12, 0.96, 0.056); // traje, más grueso
    W.phase = 'traje'; yield* grow([-2.05, 2.05, -3.1, -1.1, -1.1, 0.9], { neck: 200, torso: 1000, fringe: 120 });
    for (const s of [-1, 1]) for (let k = 0; k < 7; k++) for (let seg = 0; seg < 5; seg++) { // solapas tejidas: nueve hilos por lado siguen el relieve
      const o = (k - 3) * 0.038;
      front((t) => { const u = (seg + t * 1.08) / 5; return [s * (0.52 + o - (0.39 + o * 0.6) * u), -1.52 - 1.26 * u]; }, () => 0.012, { periph: 0.5 + 0.09 * seg, loose: 0.05 + 0.08 * seg, gain: k === 0 || k === 6 ? 2.0 : 1.0, wide: k === 0 || k === 6 ? 0.4 : 0 });
      if (late()) yield;
    }
    for (const o of [-0.075, -0.03, 0.03, 0.075]) for (let seg = 0; seg < 4; seg++) { // corbata: cuatro hilos rectos
      front((t) => { const u = (seg + t * 1.08) / 4; return [o * (1 + 0.5 * u), -1.68 - 1.1 * u]; }, () => 0.012, { periph: 0.5 + 0.1 * seg, loose: 0.03, gain: Math.abs(o) > 0.05 ? 1.3 : 0.7 });
    }
    for (const s of [-1, 1]) for (let k = 0; k < 2; k++) for (let seg = 0; seg < 3; seg++) { // cuello de la camisa
      front((t) => { const u = (seg + t * 1.08) / 3; return [s * (0.07 + 0.42 * u), -1.38 - k * 0.07 + 0.2 * u * u]; }, () => 0.012, { periph: 0.4, loose: 0.02, gain: k === 0 ? 1.5 : 0.8 });
    }
    for (const s of [-1, 1]) for (let k = 0; k < 3; k++) front((t) => [s * (0.07 + (0.2 - k * 0.05) * t), -1.4 - (0.27 - k * 0.03) * t], () => 0.012, { periph: 0.4, loose: 0.02, gain: 1.4 - k * 0.3 }); // picos del cuello
    const kz = frontZ(KNOT[0], KNOT[1]) + 0.03; // el núcleo de luz del nudo
    for (let k = 0; k < 6; k++) {
      const a = (k / 6) * Math.PI;
      for (let i = 0; i < NP; i++) { const t = i / (NP - 1) - 0.5; put(i, KNOT[0] + Math.cos(a) * t * 0.1, KNOT[1] + Math.sin(a) * t * 0.1, kz, 0, 0.1, 1); }
      add(NP, { periph: -1, loose: 0, gain: 1, kind: K.EMBER, wide: 4.5 });
    }
  }
  const it = run();
  return { W, step(ms) { if (W.done) return true; const t0 = performance.now(); deadline = t0 + ms; const ph = W.phase; W.done = it.next().done === true; const el = performance.now() - t0; W.ms += el; W.prof[ph] = (W.prof[ph] ?? 0) + el; return W.done; } };
}
