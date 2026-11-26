// Pelo de caballero maduro: filamentos plateados que siguen la superficie del cráneo, peinados hacia atrás
// con raya al lado y entradas en las sienes. Se generan una vez (troceado) y viven en la cabeza.
import { headSDF, ss } from './sculpt';

type V = [number, number, number];
const L = (x: number, y: number, z: number): number => Math.sqrt(x * x + y * y + z * z);
function grad(x: number, y: number, z: number): V { const e = 0.002, f = headSDF; const nx = f(x + e, y, z) - f(x - e, y, z), ny = f(x, y + e, z) - f(x, y - e, z), nz = f(x, y, z + e) - f(x, y, z - e), l = L(nx, ny, nz) || 1; return [nx / l, ny / l, nz / l]; }

/** Altura de la línea del pelo según (x, z): frente con entradas, sienes, y nuca baja. */
export function hairline(x: number, z: number): number {
  const ax = Math.abs(x), front = 0.6 + 0.16 * ss(0.08, 0.36, ax) - 0.06 * ss(0.36, 0.6, ax);
  return front + (-0.55 - front) * ss(0.5, -0.15, z);
}
export const HAIRLINE_GLSL = /* glsl */ `
float hairlineY(float x, float z) { float ax = abs(x), front = 0.6 + 0.16 * smoothstep(0.08, 0.36, ax) - 0.06 * smoothstep(0.36, 0.6, ax);
  return front + (-0.55 - front) * smoothstep(0.5, -0.15, z); }
float scalp(vec3 p) { float ear = smoothstep(0.55, 0.65, abs(p.x)) * smoothstep(0.25, 0.1, p.y) * smoothstep(-0.45, -0.3, p.y) * smoothstep(0.15, -0.05, p.z) * smoothstep(-0.45, -0.3, p.z);
  return smoothstep(-0.02, 0.06, p.y - hairlineY(p.x, p.z)) * (1.0 - ear); }`;

function onScalp(p: V): boolean {
  const ax = Math.abs(p[0]);
  if (ax > 0.58 && p[1] < 0.16 && p[1] > -0.42 && p[2] < 0.12 && p[2] > -0.4) return false; // orejas
  return p[1] > hairline(p[0], p[2]);
}

export interface HairStrand { pts: number[]; w: number[]; a: number[]; n: number; silver?: boolean }

function rng(seed: number): () => number { let a = seed >>> 0; return () => { a = (a + 0x6d2b79f5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

/** Generador troceado: cada llamada añade `k` mechones; devuelve true al terminar. */
export function hairBuilder(count = 300): { strands: HairStrand[]; step: (k: number) => boolean } {
  const rand = rng(0x5ea1), strands: HairStrand[] = [];
  const C: V = [0, 0.2, -0.1];
  const step = (k: number): boolean => {
    for (let s = 0; s < k && strands.length < count; s++) {
      // Semilla: dirección aleatoria desde el centro del cráneo hasta la piel; más densidad junto a la línea del pelo.
      let p: V | null = null;
      for (let tries = 0; tries < 40 && !p; tries++) {
        const u = rand() * 2 - 1, ph = rand() * Math.PI * 2, r = Math.sqrt(1 - u * u), d: V = [r * Math.cos(ph), Math.abs(u) * 0.9 + 0.1, r * Math.sin(ph)];
        const dl = L(...d); d[0] /= dl; d[1] /= dl; d[2] /= dl;
        let t = 2;
        for (let i = 0; i < 80; i++) { const q: V = [C[0] + d[0] * t, C[1] + d[1] * t, C[2] + d[2] * t], dd = headSDF(...q); if (Math.abs(dd) < 0.002) break; t -= dd * 0.8; }
        const q: V = [C[0] + d[0] * t, C[1] + d[1] * t, C[2] + d[2] * t];
        if (onScalp(q) && (strands.length > count * 0.3 || q[1] - hairline(q[0], q[2]) < 0.16)) p = q;
      }
      if (!p) continue;
      const part = -0.2, left = p[0] < part, n0 = 18 + Math.floor(rand() * 10), lift0 = 0.035 + rand() * 0.06;
      const st: HairStrand = { pts: [], w: [], a: [], n: 0 };
      let x = p[0], y = p[1], z = p[2];
      const bright = 0.35 + rand() * 0.65, wid = 0.7 + rand() * 0.7;
      for (let i = 0; i < n0; i++) {
        const nn = grad(x, y, z), t = i / (n0 - 1);
        // Dirección del peinado: hacia atrás; a la izquierda de la raya cae hacia el lado; en los lados, hacia atrás y abajo.
        let dx = left ? -0.55 : 0.35 * Math.sign(x + 0.001) + 0.15, dy = 0.12 - 0.5 * ss(0.3, 0.7, Math.abs(x)), dz = -1;
        if (z < -0.5) { dy = -0.8; dz = -0.4; }
        const dot = dx * nn[0] + dy * nn[1] + dz * nn[2]; dx -= dot * nn[0]; dy -= dot * nn[1]; dz -= dot * nn[2];
        const dl = L(dx, dy, dz) || 1, stepL = 0.034;
        const off = lift0 * (0.55 + 0.45 * Math.sin(Math.PI * Math.min(1, t * 1.3))) * (1 - 0.6 * ss(0.85, 1.15, y));
        st.pts.push(x + nn[0] * off, y + nn[1] * off, z + nn[2] * off);
        st.w.push(wid * (0.45 + 0.55 * Math.sin(Math.PI * Math.min(1, t * 0.9 + 0.08)))); st.a.push(bright * Math.min(1, (1 - t) * 2.5) * Math.min(1, t * 6 + 0.25)); st.n++;
        x += (dx / dl) * stepL; y += (dy / dl) * stepL; z += (dz / dl) * stepL;
        const dd = headSDF(x, y, z); x -= nn[0] * dd; y -= nn[1] * dd; z -= nn[2] * dd; // vuelve a la piel
        if (!onScalp([x, y, z]) && i > 4) break;
      }
      st.silver = Math.abs(p[0]) > 0.42 && p[1] < 0.75; // sienes plateadas
      if (st.n >= 4) strands.push(st);
    }
    return strands.length >= count;
  };
  return { strands, step };
}
