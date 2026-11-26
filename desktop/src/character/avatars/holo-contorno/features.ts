// Trazos de los rasgos: cejas, párpados, iris, labios, surcos y arrugas. Se calculan en CPU a partir de la
// expresión (Face) y se colocan sobre la piel mediante un mapa de altura frontal. Mismo lenguaje visual
// que los contornos: líneas de luz de grosor variable con núcleo blanco. Legibles a 300×360.
import type { Face } from './brain';
import { EYE, EYE_R, MOUTH_Y, MOUTH_W, frontZ, ss, earWorld } from './sculpt';
import { deformJS, type DeformU } from './deform';

export interface Stroke { pts: number[]; w: number[]; a: number[]; n: number } // xyz por punto, ancho en px, intensidad
export type Strokes = Stroke[];

/** Mapa de altura frontal (rejilla) para no lanzar rayos en cada fotograma. */
export class HeightMap {
  readonly nx = 120; readonly ny = 150; readonly x0 = -0.78; readonly x1 = 0.78; readonly y0 = -1.15; readonly y1 = 0.75;
  z = new Float32Array(this.nx * this.ny); private row = 0;
  /** Avanza `rows` filas; true al terminar (montaje por etapas). */
  step(rows: number): boolean {
    for (let r = 0; r < rows && this.row < this.ny; r++, this.row++) {
      const y = this.y0 + ((this.y1 - this.y0) * this.row) / (this.ny - 1);
      for (let i = 0; i < this.nx; i++) this.z[this.row * this.nx + i] = frontZ(this.x0 + ((this.x1 - this.x0) * i) / (this.nx - 1), y);
    }
    return this.row >= this.ny;
  }
  at(x: number, y: number): number {
    const fx = Math.min(this.nx - 1.001, Math.max(0, ((x - this.x0) / (this.x1 - this.x0)) * (this.nx - 1)));
    const fy = Math.min(this.ny - 1.001, Math.max(0, ((y - this.y0) / (this.y1 - this.y0)) * (this.ny - 1)));
    const i = Math.floor(fx), j = Math.floor(fy), u = fx - i, v = fy - j, k = j * this.nx + i, Z = this.z;
    return (Z[k]! * (1 - u) + Z[k + 1]! * u) * (1 - v) + (Z[k + this.nx]! * (1 - u) + Z[k + this.nx + 1]! * u) * v;
  }
}

const out3: [number, number, number] = [0, 0, 0];
const sin = Math.sin, PI = Math.PI;
const lerp = (a: number, b: number, t: number): number => a + (b - a) * t;
const clamp = (v: number, a: number, b: number): number => Math.min(b, Math.max(a, v));

export interface FeatParams { f: Face; gx: number; gy: number; pupilL: number; pupilR: number; blink?: number }

/** Builder reutilizable: no asigna memoria en el bucle (reutiliza los arrays de cada trazo). */
export class Features {
  strokes: Strokes = [];
  private k = 0;
  /** Vello de barba (x, y, ángulo, largo); se siembra una vez. */
  beard: number[] | null = null;
  constructor(private hm: HeightMap) {}
  /** Vello de la barba como lote aparte (halo mínimo): cada pelo, un trazo de 3 puntos. */
  beardStrokes: Strokes = [];
  buildBeard(du: DeformU): Strokes {
    const b = this.beard; if (!b) return this.beardStrokes;
    const keep = this.strokes, k0 = this.k; this.strokes = this.beardStrokes; this.k = 0;
    for (let h = 0; h < b.length; h += 4) {
      const bx = b[h]!, by = b[h + 1]!, ang = b[h + 2]!, len = b[h + 3]!;
      const S = this.begin(), dx = Math.sin(ang) * len, dy = -Math.cos(ang) * len;
      for (let q = 0; q < 3; q++) { const u = q / 2; this.P(S, bx + dx * u, by + dy * u, 1.0 * (q === 1 ? 1 : 0.4), q === 1 ? 0.46 : 0.2, du, 0.022); }
    }
    this.strokes.length = this.k; this.beardStrokes = this.strokes; this.strokes = keep; this.k = k0;
    return this.beardStrokes;
  }
  seedBeard(): void {
    const b: number[] = []; let seed = 7;
    const r = (): number => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
    // Barba recortada y peinada: rejilla con poco jitter, dirección suave y coherente (cae hacia el mentón
    // siguiendo la mandíbula), densidad que se degrada hacia las mejillas. Bigote: pelos cortos hacia las comisuras.
    const NX = 44, NY = 42;
    for (let gy = 0; gy < NY; gy++) for (let gx = 0; gx < NX; gx++) {
      const x = -0.56 + (gx + 0.5 + (gy % 2) * 0.5 + (r() - 0.5) * 0.7) * (1.12 / NX), y = -0.43 - (gy + 0.5 + (r() - 0.5) * 0.5) * (0.66 / NY), ax = Math.abs(x);
      const mouthGap = Math.abs(y - MOUTH_Y) < 0.064 + 0.02 * (1 - ax / 0.3) && ax < MOUTH_W + 0.035;
      const stache = y > MOUTH_Y + 0.058 && y < -0.478 - (0.05 - ax * 0.12) && ax < MOUTH_W + 0.012 && ax > 0.016;
      const chin = y < MOUTH_Y - 0.08 && ax < 0.16 + (MOUTH_Y - y) * 0.95 && y > -1.07;
      const jawIn = ax > 0.3 && y < -0.48 + (ax - 0.3) * 0.35 && y > -1.0 + (ax - 0.15) * 0.78 && ax < 0.55;
      if (mouthGap || !(stache || chin || jawIn)) continue;
      if (this.hm.at(x, y) < 0.3 || this.hm.at(x, y - 0.04) < 0.3) continue;
      // Densidad: plena en mentón y mandíbula; se aclara hacia la mejilla (arriba y hacia fuera) y en los bordes.
      const cheek = ax > 0.26 ? Math.min(1, Math.max(0, (y + 0.48 - (ax - 0.3) * 0.35) / -0.16)) : 1;
      const edge = stache ? 1 : Math.min(1, (0.55 - ax) * 12, (y + 1.07) * 14) * cheek;
      if (r() > 0.15 + 0.85 * Math.max(0, edge)) continue;
      const flow = 0.1 * Math.sin(x * 17 + y * 11) + 0.06 * Math.sin(x * 41 - y * 29);       // remolinos suaves, como vello real
      const ang = stache ? Math.sign(x) * (0.42 + ax * 1.3) + flow * 0.5 : Math.sign(x) * (0.04 + Math.pow(ax / 0.55, 1.4) * 0.5) + flow;
      b.push(x, y, ang, (stache ? 0.028 : 0.026) * (0.85 + 0.3 * Math.max(0, edge)));
    }
    this.beard = b;
  }

  private begin(): Stroke { let s = this.strokes[this.k]; if (!s) { s = { pts: [], w: [], a: [], n: 0 }; this.strokes[this.k] = s; } s.n = 0; this.k++; return s; }
  /** Añade un punto sobre la piel (x,y en reposo) con elevación `lift` y deformación facial. */
  private P(s: Stroke, x: number, y: number, w: number, a: number, du: DeformU, lift = 0.012, z?: number): void {
    const zz = (z ?? this.hm.at(x, y)) + lift;
    deformJS(x, y, zz, du, out3);
    const i = s.n * 3; s.pts[i] = out3[0]; s.pts[i + 1] = out3[1]; s.pts[i + 2] = out3[2]; s.w[s.n] = w; s.a[s.n] = a; s.n++;
  }

  build(p: FeatParams, du: DeformU): Strokes {
    this.k = 0;
    const f = p.f, W = MOUTH_W * (1 + f.w * 0.16) * (1 - f.rnd * 0.4);
    for (const s of [-1, 1]) {
      const L = s < 0, bA = L ? f.bAL : f.bAR, bl = L ? f.lL : f.lR, up = L ? f.uL : f.uR, lo = L ? f.dL : f.dR, tl = L ? f.tL : f.tR;
      const sm = L ? f.smL : f.smR, ex = s * EYE[0], ey = EYE[1];
      // ── Ceja: una base suave y vello (pelos cortos inclinados hacia la cola), espesa junto a la nariz.
      const browAt = (t: number): [number, number] => {
        const x0 = s * (0.072 - f.furrow * 0.022 + t * 0.375);
        let y = 0.165 + 0.042 * sin(PI * Math.pow(t, 0.72)) * (1 + bA * 0.6) + bl * (0.6 + 0.4 * t) + bA * 0.13 * t;
        y += Math.max(0, -bA) * 0.07 * (1 - t) * (1 - t) - f.furrow * 0.03 * (1 - t);
        return [x0, y];
      };
      { const st = this.begin(), N = 16;
        for (let i = 0; i < N; i++) { const t = i / (N - 1), [x, y] = browAt(t); this.P(st, x, y - 0.002, 6.4 * (0.3 + 0.7 * sin(PI * clamp(t * 0.85 + 0.15, 0, 1))), 0.6, du, 0.02); } }
      for (let h = 0; h < 30; h++) {
        const t = (h + 0.5) / 30, [x, y] = browAt(t), [x2, y2] = browAt(Math.min(1, t + 0.04));
        const thick = 0.028 * (1 - t * 0.55), j = ((h * 7919) % 13) / 13 - 0.5, dx = x2 - x, dy = y2 - y, l = Math.hypot(dx, dy) || 1;
        const ux = dx / l, uy = dy / l, ang = 0.55 - t * 0.4 + j * 0.25; // la cabeza de la ceja peina hacia arriba; la cola, a lo largo
        const hx = ux * Math.cos(ang) - uy * Math.sin(ang) * s, hy = uy * Math.cos(ang) + ux * Math.sin(ang) * s;
        const st = this.begin(), len = 0.042 + 0.016 * (1 - t), off = (j * 0.9) * thick;
        for (let k = 0; k < 3; k++) { const u = k / 2; this.P(st, x - hx * len * 0.5 + hx * len * u, y + off - hy * len * 0.5 + hy * len * u, (2.7 - t * 0.9) * (k === 1 ? 1 : 0.5), 1, du, 0.022); }
      }
      // ── Ojo: abertura almendrada. Cobertura del párpado superior (up) e inferior (lo), inclinación (tl).
      const inner = s * 0.19, outer = s * 0.43, by0 = -0.004, by1 = 0.014;
      const apU = Math.max(0.067 - up * 0.088, -0.004), apL = Math.min(-0.036 + lo * 0.05, apU - 0.003);
      const lidY = (t: number, upper: boolean): number => {
        const base = lerp(by0, by1, t), skew = upper ? Math.pow(sin(PI * Math.pow(t, 0.85)), 0.75) : Math.pow(sin(PI * Math.pow(t, 1.15)), 1.1);
        const tilt = s * tl * 0.32 * (lerp(inner, outer, t) - ex) * s * (upper ? 1 : 0.4);
        return base + (upper ? apU : apL) * skew + tilt;
      };
      const NL = 20, closed = apU - apL < 0.01;
      const U = this.begin();
      for (let i = 0; i < NL; i++) { const t = i / (NL - 1); this.P(U, lerp(inner, outer, t), lidY(t, true), 3.4 * (0.45 + 0.55 * sin(PI * t)) + 0.6, 1, du, 0.022); }
      const D = this.begin();
      for (let i = 0; i < NL; i++) { const t = i / (NL - 1); this.P(D, lerp(inner, outer, t), lidY(t, false), 1.9 * (0.3 + 0.7 * sin(PI * t)), closed ? 0.6 : 0.75, du, 0.02); }
      // Pliegue del párpado (caballero maduro: algo caído) y ojera discreta; ambos se marcan al entornar.
      const C = this.begin();
      for (let i = 0; i < 14; i++) { const t = 0.08 + (i / 13) * 0.86; this.P(C, lerp(inner, outer, t) + s * 0.008, 0.004 + lerp(by0, by1, t) + 0.055 * Math.pow(sin(PI * t), 0.8) - 0.018 * t * t + Math.max(apU, 0) * 0.3 + bl * 0.35, 1.9 * sin(PI * t), 0.6 + up * 0.25, du, 0.024); }
      const B = this.begin();
      for (let i = 0; i < 10; i++) { const t = 0.12 + (i / 9) * 0.72; this.P(B, lerp(inner, outer, t), -0.075 - 0.012 * sin(PI * t) + lo * 0.025, 1.3 * sin(PI * t), 0.34 + lo * 0.5 + Math.max(sm, 0) * 0.25, du, 0.016); }
      // Iris (anillo) y pupila sobre el globo, recortados por los párpados.
      const ix = ex + p.gx * 0.05, iy = ey - p.gy * 0.035 - 0.004, R = 0.05, pr = 0.017 * (L ? p.pupilL : p.pupilR);
      const ring = (r: number, w: number, a0: number): void => {
        const S = this.begin(), N = 28;
        for (let i = 0; i <= N; i++) {
          const ang = (i / N) * PI * 2, x = ix + Math.cos(ang) * r, y = iy + Math.sin(ang) * r;
          const tt = (x - inner) / (outer - inner), inside = tt > 0.02 && tt < 0.98 && y < lidY(clamp(tt, 0, 1), true) - 0.004 && y > lidY(clamp(tt, 0, 1), false) + 0.003;
          const dx = x - ex, dy = y - ey, zb = EYE[2] + Math.sqrt(Math.max(0, (EYE_R + 0.004) ** 2 - dx * dx - dy * dy));
          this.P(S, x, y, w, inside && !closed ? a0 : 0, du, 0.0, zb);
        }
      };
      ring(R, 2.2, 0.95); ring(R * 0.62, 1.0, 0.4); ring(pr, 2.0, 1);
      // Patas de gallo: aparecen al entornar o sonreír.
      const crow = clamp(0.38 + lo * 1.2 + Math.max(sm, 0) * 0.55 - 0.15, 0, 1);
      for (let r = 0; r < 3; r++) {
        const S = this.begin(), a = -0.5 + r * 0.42;
        for (let i = 0; i < 5; i++) { const t = i / 4; this.P(S, s * (0.455 + t * 0.07 * Math.cos(a)), 0.01 + t * 0.07 * Math.sin(a), 1.3 * sin(PI * (0.15 + t * 0.7)), crow * 0.7, du, 0.014); }
      }
      // Surco nasolabial: se ahonda con la sonrisa, se alarga con la pena.
      { const S = this.begin(), k = Math.max(sm, 0), g = Math.max(-sm, 0);
        for (let i = 0; i < 14; i++) { const t = i / 13;
          const x = s * (0.135 + t * 0.12 + k * 0.035 * sin(PI * t) + 0.02 * t * t), y = -0.36 - t * 0.32 - g * 0.05 * t;
          this.P(S, x, y, 3.0 * sin(PI * (0.06 + t * 0.88)), 0.72 + k * 0.3 + g * 0.2, du, 0.014); } }
      // Aleta de la nariz: curva en C que envuelve el ala (sin agujero) y un trazo fino de narina.
      { const S = this.begin(), N = 12;
        for (let i = 0; i < N; i++) { const t = i / (N - 1), a = -0.5 * PI + t * 1.05 * PI;
          this.P(S, s * (0.105 + 0.048 * Math.cos(a)), -0.405 + 0.038 * Math.sin(a), 1.8 * sin(PI * (0.08 + 0.84 * t)), 0.62, du, 0.016); } }
      { const S = this.begin(); for (let i = 0; i < 5; i++) { const t = i / 4; this.P(S, s * (0.035 + t * 0.05), -0.437 + 0.006 * sin(PI * t), 1.1 * sin(PI * (0.15 + 0.7 * t)), 0.32, du, 0.012); } }
      // Dorso nasal (lateral, tenue).
      { const S = this.begin(); for (let i = 0; i < 8; i++) { const t = i / 7; this.P(S, s * (0.045 + 0.02 * t), 0.08 - t * 0.37, 1.2 * sin(PI * (0.1 + 0.8 * t)), 0.3, du, 0.012); } }
      // Oreja: hélix (contorno en C que baja al lóbulo) y antehélix, en el marco de la oreja.
      { const S = this.begin(), N = 24;
        for (let i = 0; i < N; i++) { const t = i / (N - 1), a = 0.62 * PI - t * 1.62 * PI;
          let v = 0.04 + 0.165 * Math.sin(a), w = 0.108 * Math.cos(a);
          if (a < -0.5 * PI) { const k = -(a + 0.5 * PI) / (0.5 * PI); v = 0.04 - 0.165 - 0.1 * k; w = 0.108 * Math.cos(a) * (1 - k) + 0.035 * k; } // lóbulo
          const [ex2, ey2, ez2] = earWorld(0.05, v, w - v * 0.22);
          this.P(S, s * ex2, ey2, 2.0 * sin(PI * (0.04 + 0.92 * t)), 0.75, du, 0, ez2); } }
      { const S = this.begin(), N = 10;
        for (let i = 0; i < N; i++) { const t = i / (N - 1), a = 0.45 * PI - t * 1.0 * PI, v = 0.05 + 0.09 * Math.sin(a), w = 0.05 * Math.cos(a) - 0.015;
          const [ex2, ey2, ez2] = earWorld(0.045, v, w - v * 0.22); this.P(S, s * ex2, ey2, 1.3 * sin(PI * t), 0.42, du, 0, ez2); } }
      // Filtrum.
      { const S = this.begin(); for (let i = 0; i < 4; i++) { const t = i / 3; this.P(S, s * (0.022 + 0.01 * t), -0.465 - t * 0.09, 1.2, 0.3, du, 0.012); } }
    }
    // ── Frente: arrugas horizontales que aparecen al subir las cejas (un poco siempre: 57 años).
    const liftAvg = (f.lL + f.lR) * 0.5, wr = clamp(0.42 + liftAvg * 9 + Math.max(0, -(f.bAL + f.bAR)) * 0.6, 0, 1);
    for (let r = 0; r < 3; r++) {
      const S = this.begin(), y0 = 0.36 + r * 0.085;
      for (let i = 0; i < 18; i++) { const t = i / 17, x = -0.3 + t * 0.6; this.P(S, x, y0 + 0.02 * sin(PI * t) + liftAvg * 0.4 + (r === 1 ? 0.006 * sin(t * 9) : 0), 1.5 * sin(PI * t), wr * (r === 1 ? 0.75 : 0.55), du, 0.012); }
    }
    // Entrecejo: dos surcos verticales con el ceño.
    for (const s of [-1, 1]) { const S = this.begin(); for (let i = 0; i < 5; i++) { const t = i / 4; this.P(S, s * (0.03 + 0.008 * t), 0.115 + t * 0.09, 1.6 * sin(PI * (0.15 + 0.7 * t)), clamp(f.furrow * 0.9 + Math.max(0, -f.bAL) * 0.3, 0, 1), du, 0.012); } }
    // Punta de la nariz: contorno inferior en U suave (lóbulo y columela).
    { const S = this.begin(); for (let i = 0; i < 13; i++) { const t = i / 12, a = PI * (1.1 - t * 1.2); this.P(S, 0.062 * Math.cos(a), -0.39 - 0.038 * Math.sin(Math.max(0, a)) * (Math.sin(a) > 0 ? 1 : 0) - 0.03 * sin(PI * t), 2.0 * sin(PI * (0.06 + 0.88 * t)), 0.7, du, 0.014); } }
    // ── Boca. Comisuras (cy por lado), apertura central con perfil, redondez y anchura.
    const open = clamp(f.jaw, 0, 1.1);
    const cyL = MOUTH_Y + f.smL * 0.062, cyR = MOUTH_Y + f.smR * 0.062;
    const mid = (x: number): number => { const t = (x / W + 1) / 2; return lerp(cyL, cyR, t) - 0.012 * Math.pow(Math.max(0, 1 - (x / W) ** 2), 1.2) * (1 - Math.abs(f.smL + f.smR) * 0.3); };
    const prof = (x: number): number => Math.pow(Math.max(0, 1 - (x / W) ** 2), 0.55 + f.rnd * 0.5);
    const NM = 24;
    // Labio superior (contorno, arco de Cupido).
    { const S = this.begin(); for (let i = 0; i < NM; i++) { const t = i / (NM - 1), x = -W + t * 2 * W, ax = Math.abs(x) / W;
      const cupid = 0.062 - 0.012 * Math.exp(-((x / 0.022) ** 2)) + 0.004 * Math.exp(-(((ax - 0.25) / 0.14) ** 2));
      const y = mid(x) + cupid * Math.pow(Math.max(0, 1 - ax * ax), 0.7) + open * 0.012 * prof(x);
      this.P(S, x, y, 2.1 * (0.35 + 0.65 * sin(PI * t)), 0.62, du, 0.012); } }
    // Línea de la boca: superior e inferior (coinciden cerrada; se separan al hablar).
    const upperIn = this.begin(), lowerIn = this.begin();
    for (let i = 0; i < NM; i++) {
      const t = i / (NM - 1), x = -W + t * 2 * W, pr = prof(x), y = mid(x);
      this.P(upperIn, x, y + open * 0.014 * pr, 3.2 * (0.3 + 0.7 * Math.pow(sin(PI * t), 0.5)), 1, du, 0.014);
      this.P(lowerIn, x, y - open * 0.07 * pr, 2.4 * (0.3 + 0.7 * Math.pow(sin(PI * t), 0.5)), open > 0.04 ? 0.9 : 0, du, 0.014);
    }
    // Dientes (insinuados) al abrir.
    { const S = this.begin(); for (let i = 0; i < 12; i++) { const t = i / 11, x = (-0.7 + t * 1.4) * W * 0.8, pr = prof(x); this.P(S, x, mid(x) + open * 0.014 * pr - 0.016 * pr, 1.4, clamp((open - 0.25) * 1.6, 0, 0.55) * pr, du, 0.004); } }
    // Labio inferior: sombra bajo el bermellón (más lleno al centro).
    { const S = this.begin(); for (let i = 0; i < 16; i++) { const t = i / 15, x = (-0.68 + t * 1.36) * W, ax = Math.abs(x) / W;
      this.P(S, x, mid(x) - 0.062 * Math.pow(Math.max(0, 1 - ax * ax), 0.6) - open * 0.072 * prof(x) - 0.004, 2.4 * sin(PI * t), 0.55, du, 0.012); } }
    // Mentón: hoyuelo y contorno.
    { const S = this.begin(); for (let i = 0; i < 12; i++) { const t = i / 11, x = -0.14 + t * 0.28; this.P(S, x, -0.9 - 0.035 * sin(PI * t), 1.6 * sin(PI * t), 0.38, du, 0.012); } }
    this.strokes.length = this.k;
    void ss;
    return this.strokes;
  }
}
