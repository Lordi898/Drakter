// Escultura de Drakter: cabeza de caballero de 55-60 años como SDF analítico (sin modelos externos).
// Espacio local de la cabeza: +y arriba, +z hacia delante (la cara), +x a la derecha del espectador.
// Unidad ≈ 1 dm: la cabeza mide ~2,3 de mentón a coronilla. Canon de retrato: ojos a media altura,
// tercios faciales iguales (frente · nariz · boca-mentón), ~5 ojos de ancho.
export type V3 = [number, number, number];
type SDF = (x: number, y: number, z: number) => number;

const L = (x: number, y: number, z: number): number => Math.sqrt(x * x + y * y + z * z);
const cl = (v: number, a: number, b: number): number => Math.min(b, Math.max(a, v));
export const ss = (a: number, b: number, x: number): number => { const t = cl((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
const ell = (x: number, y: number, z: number, a: number, b: number, c: number): number => {
  const k0 = L(x / a, y / b, z / c), k1 = L(x / (a * a), y / (b * b), z / (c * c));
  return k1 < 1e-9 ? -Math.min(a, b, c) : (k0 * (k0 - 1)) / k1;
};
const cap = (px: number, py: number, pz: number, a: V3, b: V3, r: number): number => {
  const pax = px - a[0], pay = py - a[1], paz = pz - a[2], bax = b[0] - a[0], bay = b[1] - a[1], baz = b[2] - a[2];
  const h = cl((pax * bax + pay * bay + paz * baz) / (bax * bax + bay * bay + baz * baz), 0, 1);
  return L(pax - bax * h, pay - bay * h, paz - baz * h) - r;
};
/** Cápsula de radio variable (r1 en a, r2 en b), aproximación suave suficiente para modelar. */
const vcap = (px: number, py: number, pz: number, a: V3, b: V3, r1: number, r2: number): number => {
  const pax = px - a[0], pay = py - a[1], paz = pz - a[2], bax = b[0] - a[0], bay = b[1] - a[1], baz = b[2] - a[2];
  const h = cl((pax * bax + pay * bay + paz * baz) / (bax * bax + bay * bay + baz * baz), 0, 1);
  return L(pax - bax * h, pay - bay * h, paz - baz * h) - (r1 + (r2 - r1) * h);
};
const smin = (a: number, b: number, k: number): number => { const h = Math.max(k - Math.abs(a - b), 0) / k; return Math.min(a, b) - h * h * k * 0.25; };
const smax = (a: number, b: number, k: number): number => -smin(-a, -b, k);
void ss;

// ── Anclas de rasgos (lado +x; el otro es el espejo).
export const EYE: V3 = [0.305, 0.0, 0.7]; export const EYE_R = 0.118; // centro del globo ocular
export const MOUTH_Y = -0.655, MOUTH_W = 0.235;
export const HINGE: V3 = [0, -0.3, -0.22];
/** Marco local de la oreja (lado +x): u = grosor (hacia fuera-delante), v = alto, w = ancho (hacia delante). */
export const EAR_C: V3 = [0.72, -0.06, -0.16], EAR_B = 0.45;
export function earLocal(ax: number, y: number, z: number): V3 {
  const px = ax - EAR_C[0], py = y - EAR_C[1], pz = z - EAR_C[2], c = Math.cos(EAR_B), s = Math.sin(EAR_B);
  return [px * c + pz * s, py, -px * s + pz * c];
}
export function earWorld(u: number, v: number, w: number): V3 {
  const c = Math.cos(EAR_B), s = Math.sin(EAR_B);
  return [EAR_C[0] + u * c - w * s, EAR_C[1] + v, EAR_C[2] + u * s + w * c];
}

export const headSDF: SDF = (x, y, z) => {
  const ax = Math.abs(x);
  // Neurocráneo: amplio, frente alta que se inclina hacia atrás; occipucio marcado.
  let d = ell(x, y - 0.27, z + 0.1, 0.75, 0.93, 1.0);
  d = smin(d, ell(x, y - 0.42, z - 0.36, 0.62, 0.5, 0.5), 0.3);                       // frente
  // Macizo facial, arcada dental (sobre ella se asientan los labios) y mandíbula.
  d = smin(d, ell(x, y + 0.3, z - 0.36, 0.58, 0.64, 0.56), 0.3);
  d = smin(d, ell(x, y + 0.62, z - 0.6, 0.34, 0.3, 0.32), 0.18);                     // arcada (hocico humano)
  d = smin(d, cap(ax, y, z, [0.52, -0.62, -0.06], [0.22, -0.98, 0.6], 0.11), 0.16);    // mandíbula firme
  d = smin(d, ell(ax - 0.52, y + 0.66, z + 0.02, 0.1, 0.1, 0.12), 0.1);                // ángulo mandibular
  d = smax(d, -ell(ax - 0.42, y + 0.33, z - 0.55, 0.12, 0.13, 0.12), 0.12);           // mejilla algo enjuta
  d = smin(d, ell(x, y + 0.98, z - 0.76, 0.2, 0.13, 0.16), 0.14);                    // mentón (cuadrado, maduro)
  d = smin(d, ell(ax - 0.5, y + 0.06, z - 0.5, 0.16, 0.1, 0.25), 0.13);              // pómulos (cigomáticos)
  d = smin(d, cap(ax, y, z, [0.02, 0.215, 0.85], [0.43, 0.205, 0.7], 0.085), 0.1);    // arco superciliar marcado (madurez)
  // Órbitas con su globo ocular (el párpado lo dibujan los trazos).
  d = smax(d, -ell(ax - 0.3, y - 0.01, z - 0.86, 0.15, 0.1, 0.13), 0.07);
  {
    const ex = ax - EYE[0], ey = y - EYE[1], ez = z - EYE[2];
    const ball = L(ex, ey, ez) - EYE_R;
    // Abertura almendrada (más alta hacia dentro); fuera de ella, los párpados cubren el globo.
    const ap = ell(ex + 0.01, ey - 0.008 + 0.012 * (ex / 0.13), 0, 0.128, 0.05 + 0.006 * (1 - ex / 0.13), 1) ;
    const lids = Math.max(L(ex, ey, ez) - EYE_R - 0.016, -ap);
    d = smin(d, Math.min(ball, lids), 0.03);
  }
  // Sienes: ligeramente hundidas.
  d = smax(d, -ell(ax - 0.79, y - 0.24, z - 0.32, 0.11, 0.2, 0.24), 0.1);             // sienes algo hundidas
  // Nariz: raíz hundida, dorso recto con leve giba, punta definida, aletas.
  d = smin(d, vcap(x, y, z, [0, 0.12, 0.87], [0, -0.3, 1.08], 0.05, 0.075), 0.06);
  d = smin(d, ell(x, y + 0.02, z - 0.95, 0.045, 0.05, 0.03), 0.04);                  // giba del dorso
  d = smin(d, ell(x, y + 0.34, z - 1.055, 0.07, 0.065, 0.065), 0.045);               // lóbulo de la punta
  d = smin(d, ell(ax - 0.1, y + 0.4, z - 0.95, 0.065, 0.055, 0.07), 0.045);          // aletas nasales
  // Boca: labio superior con filtrum, inferior algo más lleno, comisuras, surco mentolabial.
  d = smin(d, ell(x, y + 0.585, z - 0.89, 0.21, 0.07, 0.07), 0.06);
  d = smax(d, -ell(x, y + 0.53, z - 0.98, 0.022, 0.055, 0.025), 0.02);               // filtrum
  d = smin(d, ell(x, y + 0.715, z - 0.875, 0.18, 0.055, 0.07), 0.05);                // labio inferior
  d = smax(d, -ell(x, y - MOUTH_Y, z - 0.98, 0.22, 0.006, 0.07), 0.012);             // línea de la boca
  d = smax(d, -ell(ax - 0.235, y + 0.655, z - 0.85, 0.03, 0.03, 0.05), 0.03);        // comisuras
  d = smax(d, -ell(x, y + 0.82, z - 0.92, 0.14, 0.03, 0.04), 0.04);                  // surco mentolabial
  // Orejas: pabellón con hélix y lóbulo, en su propio marco: enraizado delante y abierto ~25° por detrás.
  { const [u, v, w] = earLocal(ax, y, z), wt = w + v * 0.22;
    let e = ell(u, v - 0.04, wt, 0.045, 0.17, 0.115);
    e = smin(e, ell(u + 0.005, v + 0.2, wt - 0.015, 0.038, 0.075, 0.065), 0.06);
    d = smin(d, e, 0.05); }
  // Cuello robusto con nuez discreta; trapecios.
  d = smin(d, vcap(x, y, z, [0, -0.62, -0.2], [0, -2.1, -0.12], 0.44, 0.5), 0.3);
  d = smin(d, ell(x, y + 1.35, z - 0.27, 0.07, 0.09, 0.07), 0.08);
  return d;
};

function grad(f: SDF, x: number, y: number, z: number): V3 {
  const e = 0.0015, nx = f(x + e, y, z) - f(x - e, y, z), ny = f(x, y + e, z) - f(x, y - e, z), nz = f(x, y, z + e) - f(x, y, z - e), l = L(nx, ny, nz) || 1;
  return [nx / l, ny / l, nz / l];
}
function aoAt(f: SDF, x: number, y: number, z: number, n: V3): number {
  let occ = 0, w = 1;
  for (let i = 1; i <= 5; i++) { const h = 0.035 * i; occ += (h - f(x + n[0] * h, y + n[1] * h, z + n[2] * h)) * w; w *= 0.6; }
  return cl(1 - 2.6 * occ, 0.15, 1);
}

export interface Shell { pos: Float32Array; nor: Float32Array; ao: Float32Array; index: Uint32Array; ws: number; hs: number }

/** Proyecta una rejilla esférica sobre la superficie del SDF (estrellado respecto a c). Troceado por filas:
 *  devuelve una función que avanza `rows` filas por llamada y true cuando termina. */
export function projector(f: SDF, c: V3, ws: number, hs: number, clipY = -1.75): { shell: Shell; step: (rows: number) => boolean } {
  const n = (ws + 1) * (hs + 1), pos = new Float32Array(n * 3), nor = new Float32Array(n * 3), ao = new Float32Array(n);
  const idx: number[] = [];
  for (let j = 0; j < hs; j++) for (let i = 0; i < ws; i++) { const a = j * (ws + 1) + i, b = a + ws + 1; idx.push(a, b, a + 1, b, b + 1, a + 1); }
  let row = 0;
  const shell: Shell = { pos, nor, ao, index: new Uint32Array(idx), ws, hs };
  const step = (rows: number): boolean => {
    for (let r = 0; r < rows && row <= hs; r++, row++) {
      const th = (row / hs) * Math.PI;
      for (let i = 0; i <= ws; i++) {
        const ph = (i / ws) * Math.PI * 2, dx = -Math.cos(ph) * Math.sin(th), dy = Math.cos(th), dz = Math.sin(ph) * Math.sin(th);
        let t = 3.2, prev = 3.2;
        for (let k = 0; k < 240; k++) {
          const dd = f(c[0] + dx * t, c[1] + dy * t, c[2] + dz * t);
          if (dd < 0) { let a = t, b = prev; for (let q = 0; q < 12; q++) { const m = (a + b) / 2; if (f(c[0] + dx * m, c[1] + dy * m, c[2] + dz * m) < 0) a = m; else b = m; } t = (a + b) / 2; break; }
          prev = t; t -= Math.max(dd * 0.8, 0.003); if (t <= 0) { t = 0.01; break; }
        }
        let x = c[0] + dx * t, y = c[1] + dy * t, z = c[2] + dz * t;
        if (y < clipY) y = clipY; // el cuello se corta en el busto
        const nn = grad(f, x, y, z), k = row * (ws + 1) + i;
        pos.set([x, y, z], k * 3); nor.set(nn, k * 3); ao[k] = aoAt(f, x, y, z, nn);
      }
    }
    return row > hs;
  };
  return { shell, step };
}

/** Altura frontal z(x,y) de la cara (rayo desde delante), para colocar trazos sobre la piel. */
export function frontZ(x: number, y: number): number {
  let z = 1.6;
  for (let k = 0; k < 200; k++) { const d = headSDF(x, y, z); if (d < 0.0005) break; z -= Math.max(d * 0.9, 0.001); if (z < -1) break; }
  return z;
}

// ── Busto: cuello, trapecios, hombros y pecho (sin deformación facial).
export const bodySDF: SDF = (x, y, z) => {
  const ax = Math.abs(x);
  let d = vcap(x, y, z, [0, -1.5, -0.17], [0, -2.15, -0.12], 0.45, 0.52);                 // cuello
  d = smin(d, ell(x, y + 2.75, z + 0.12, 1.42, 0.72, 0.6), 0.45);                          // tórax y hombros
  d = smin(d, cap(ax, y, z, [0.35, -1.95, -0.2], [1.22, -2.35, -0.15], 0.24), 0.35);        // trapecio → hombro
  d = smin(d, ell(ax - 1.25, y + 2.55, z + 0.12, 0.3, 0.32, 0.36), 0.25);                  // deltoides
  d = smin(d, ell(ax - 0.45, y + 2.55, z - 0.22, 0.42, 0.3, 0.2), 0.3);                    // pectorales
  return d;
};

/** z frontal de un SDF cualquiera. */
export function frontOf(f: SDF, x: number, y: number): number {
  let z = 1.6;
  for (let k = 0; k < 220; k++) { const d = f(x, y, z); if (d < 0.0006) break; z -= Math.max(d * 0.9, 0.001); if (z < -1.5) break; }
  return z;
}
