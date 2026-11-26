// Voz simulada con visemas aproximados del castellano: el texto se trocea en segmentos
// (vocales, bilabiales, labiodentales y resto de consonantes) con duración y energía propias.

export type Viseme = 'A' | 'E' | 'I' | 'O' | 'U' | 'M' | 'F' | 'C' | '_';
interface Seg { v: Viseme; d: number; l: number }

const PHRASES = [
  'Buenas noches, señor. Todo está en orden, como de costumbre.',
  'Me he tomado la libertad de revisar su calendario.',
  'Mañana a las nueve tiene usted la reunión. Puntual, espero.',
  'Un momento, por favor. Estoy en ello.',
];

const VOW: Record<string, [Viseme, number]> = {
  a: ['A', 1], á: ['A', 1], e: ['E', 0.78], é: ['E', 0.8], i: ['I', 0.58], í: ['I', 0.62],
  o: ['O', 0.86], ó: ['O', 0.88], u: ['U', 0.6], ú: ['U', 0.62], y: ['I', 0.5],
};

function segment(text: string): Seg[] {
  const out: Seg[] = [];
  const s = text.toLowerCase();
  for (let i = 0; i < s.length; i++) {
    const c = s[i]!, n = s[i + 1] ?? '';
    if (c === 'h') continue; // muda
    if (c === 'q' && n === 'u') { out.push({ v: 'C', d: 0.06, l: 0.3 }); i++; continue; }
    if (VOW[c]) { const [v, l] = VOW[c]!; out.push({ v, d: 0.1 + l * 0.03, l }); continue; }
    if ('mbpv'.includes(c)) { out.push({ v: 'M', d: 0.075, l: 0.04 }); continue; }
    if (c === 'f') { out.push({ v: 'F', d: 0.075, l: 0.18 }); continue; }
    if (c === ' ') { out.push({ v: '_', d: 0.05, l: 0 }); continue; }
    if (c === ',') { out.push({ v: '_', d: 0.26, l: 0 }); continue; }
    if ('.?!'.includes(c)) { out.push({ v: '_', d: 0.5, l: 0 }); continue; }
    if (/[a-zñ]/.test(c)) out.push({ v: 'C', d: c === 'r' && n === 'r' ? 0.08 : 0.055, l: 0.28 });
  }
  return out;
}

const TIMELINE: { t0: number; seg: Seg; ph: number }[] = [];
let TOTAL = 0;
PHRASES.forEach((p, ph) => {
  for (const seg of segment(p)) { TIMELINE.push({ t0: TOTAL, seg, ph }); TOTAL += seg.d; }
  TIMELINE.push({ t0: TOTAL, seg: { v: '_', d: 1.1, l: 0 }, ph: -1 }); TOTAL += 1.1;
});

/** Devuelve el nivel 0-1 y el visema que suena en el instante t (bucle sobre las frases). */
export function simVoice(t: number): { level: number; vis: Viseme; text: string } {
  const x = ((t % TOTAL) + TOTAL) % TOTAL;
  let lo = 0, hi = TIMELINE.length - 1;
  while (lo < hi) { const m = (lo + hi + 1) >> 1; if (TIMELINE[m]!.t0 <= x) lo = m; else hi = m - 1; }
  const { t0, seg, ph } = TIMELINE[lo]!;
  const u = (x - t0) / seg.d;
  const shape = Math.sin(Math.PI * Math.min(1, Math.max(0, u))) * 0.35 + 0.65; // cada sílaba respira
  return { level: seg.l * shape * (0.9 + 0.1 * Math.sin(t * 7.3)), vis: seg.v, text: ph >= 0 ? PHRASES[ph]! : '' };
}

/** Forma de la boca de láminas por visema: apertura, anchura, redondez, sonrisa. */
export const MOUTH: Record<Viseme, [number, number, number, number]> = {
  A: [1, 0.92, 0, 0.05], E: [0.55, 1.05, 0, 0.15], I: [0.34, 1.1, 0, 0.3], O: [0.8, 0.6, 0.75, 0],
  U: [0.45, 0.42, 1, -0.05], M: [0, 0.85, 0, 0], F: [0.14, 0.95, 0, 0.05], C: [0.3, 0.88, 0.1, 0.05], _: [0, 0.9, 0, 0],
};
