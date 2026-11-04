/*
 * Drakter: rig parametrico SVG del personaje (sustituto del .riv de Rive).
 * Port tipado de desktop/design/character/character.js (rama identidad-personaje).
 *
 * Un estado no dibuja nada: solo declara valores objetivo para PARAMS. Un unico
 * bucle requestAnimationFrame compartido acerca los valores actuales a los
 * objetivos y redibuja. El marcado SVG es una constante local; ningun dato de
 * red entra en el.
 */
import { CHARACTER_STATES, type CharacterState } from './types'

export interface Rig {
  setState(name: CharacterState): boolean
  getState(): CharacterState
  destroy(): void
}

type ParamName = keyof typeof PARAMS
type Params = Record<ParamName, number>
interface StateDef {
  rate: number
  set: Partial<Params>
  settle?: Partial<Record<ParamName, readonly [number, number, number]>>
}
type Rgb = readonly [number, number, number]
interface Talk { o: number; w: number; c: number; to: number; tw: number; tc: number; left: number; phrase: number; rest: number; last: number }
interface Colors { color: Rgb; hot: Rgb }

const STATE_NAMES: readonly string[] = CHARACTER_STATES
const isState = (v: unknown): v is CharacterState => typeof v === 'string' && STATE_NAMES.includes(v)

/* Cada parametro corresponde a una entrada numerica de la maquina de Rive. */
const PARAMS = {
  eyeOpen: 0.84,    // apertura de ojos: 0 cerrado, 1 abierto, 1.2 desorbitado
  lidBend: 0,       // curva del ojo cerrado: -1 contento, 1 dormido
  pupil: 0.38,      // anchura de la pupila vertical: 0 rendija, 1 dilatada
  gazeX: 0,         // mirada: -1 izquierda, 1 derecha
  gazeY: 0,         // mirada: -1 arriba, 1 abajo
  browAngleL: 0,    // grados; positivo ceno, negativo preocupacion
  browAngleR: 0,
  browRaiseL: 0,    // unidades del viewBox hacia arriba
  browRaiseR: 0,
  mouthOpen: 0,     // 0 cerrada, 1 abierta del todo
  mouthCurve: 0.15, // -1 hacia abajo, 1 sonrisa
  mouthWidth: 1,    // 1 boca ancha de reposo
  mouthX: 0,        // desplazamiento lateral
  fang: 1,          // tamano del colmillo
  headTilt: 0,      // grados
  headY: 0,         // unidades del viewBox hacia abajo
  headScale: 1,
  finL: 0,          // grados; positivo levantada, negativo caida
  finR: 0,
  ember: 0.35,      // intensidad de la brasa: 0 apagada, 1 viva
  emberHue: 0,      // 0 naranja, 1 cobalto
  crackle: 0,       // chisporroteo de la brasa
  sparks: 0,        // chispas
  smoke: 0,         // humo por el orificio del hocico
  flame: 0,         // llamarada que asoma por detras de la mandibula
  sat: 1,           // saturacion global
  value: 1,         // luminosidad global
  breath: 1,        // amplitud de la respiracion
  breathRate: 0.24, // respiraciones por segundo
  blink: 1,         // frecuencia del parpadeo: 0 no parpadea
  talk: 0,          // mezcla del generador de articulacion
  scan: 0           // vaiven de trabajo: la mirada recorre algo
};

/*
 * Solo se anota lo que difiere de PARAMS.
 * rate: velocidad de aproximacion, por segundo.
 * settle: { param: [inicio, fin, ms] } objetivo que decae de inicio a fin
 *         tras entrar en el estado. Es asentamiento interno, no un cambio
 *         de estado: el estado solo cambia con setState.
 */
const PARAM_NAMES = Object.keys(PARAMS) as ParamName[]

const STATES: Record<CharacterState, StateDef> = {
  idle: { rate: 7, set: {} },
  listening: {
    rate: 9,
    set: {
      eyeOpen: 1, pupil: 0.82, gazeX: 0.15,
      browRaiseL: 7, browRaiseR: 5, browAngleL: -4, browAngleR: -4,
      mouthOpen: 0.05, mouthCurve: 0.2,
      headTilt: 8, headY: -2, headScale: 1.03,
      finL: 34, finR: 30, ember: 0.5, breathRate: 0.3, blink: 0.6
    }
  },
  thinking: {
    rate: 6,
    set: {
      eyeOpen: 0.78, pupil: 0.42, gazeX: 0.85, gazeY: -0.85,
      browRaiseL: -2, browRaiseR: 13, browAngleL: 6, browAngleR: -8,
      mouthCurve: -0.12, mouthWidth: 0.62, mouthX: 12,
      headTilt: -5, headY: -2, finL: -6, finR: 12,
      ember: 0.5, smoke: 0.9, blink: 0.5
    }
  },
  speaking: {
    rate: 8,
    set: {
      eyeOpen: 0.9, pupil: 0.48, mouthOpen: 0.07, mouthCurve: 0.2, talk: 1,
      ember: 0.6, finL: 8, finR: 8, breathRate: 0.32
    }
  },
  executing: {
    rate: 9,
    set: {
      eyeOpen: 0.7, pupil: 0.02,
      browAngleL: 18, browAngleR: 18, browRaiseL: -4, browRaiseR: -4,
      mouthCurve: -0.15, mouthWidth: 0.82, headY: 3, finL: -8, finR: -8,
      ember: 0.95, sparks: 1, crackle: 0.2, scan: 1,
      blink: 0.4, breathRate: 0.5
    }
  },
  success: {
    rate: 11,
    set: {
      eyeOpen: 0, lidBend: -1,
      browRaiseL: 8, browRaiseR: 8, browAngleL: -6, browAngleR: -6,
      mouthOpen: 0.2, mouthCurve: 1, mouthWidth: 1.08, fang: 1.3,
      finL: 20, finR: 20, ember: 1, blink: 0
    },
    settle: { flame: [0.9, 0, 900], headY: [-12, -4, 450] }
  },
  error: {
    rate: 8,
    set: {
      eyeOpen: 0.86, pupil: 0.2, gazeX: -0.35, gazeY: 0.55,
      browAngleL: -20, browAngleR: -20, browRaiseL: 4, browRaiseR: 4,
      mouthOpen: 0.1, mouthCurve: -0.85, mouthWidth: 0.8,
      headTilt: -4, headY: 5, finL: -18, finR: -18,
      ember: 0.7, emberHue: 1, crackle: 1, sparks: 0.4, blink: 0.7
    },
    settle: { smoke: [1, 0.3, 1400], crackle: [1, 0.1, 2500] }
  },
  interrupted: {
    rate: 26,
    set: {
      eyeOpen: 1.2, pupil: 0.26,
      browRaiseL: 14, browRaiseR: 14, browAngleL: -6, browAngleR: -6,
      mouthOpen: 0.3, mouthCurve: 0, mouthWidth: 0.3, fang: 0.8,
      finL: 14, finR: 14, ember: 0.5, breath: 0, blink: 0
    },
    settle: { headScale: [0.95, 1, 240] }
  },
  offline: {
    rate: 2.6,
    set: {
      eyeOpen: 0, lidBend: 1, pupil: 0.3,
      browAngleL: -3, browAngleR: -3, browRaiseL: -5, browRaiseR: -5,
      mouthCurve: 0, headTilt: -6, headY: 12, headScale: 0.98,
      finL: -30, finR: -30, ember: 0, sat: 0.16, value: 0.62,
      breath: 0.7, breathRate: 0.1, blink: 0
    }
  }
};

const PALETTE = {
  line: '#24142A',   // manganeso hondo: contorno
  head: '#3A9A8C',   // cardenillo
  pool: '#1F6E66',   // charco de esmalte
  lid: '#287A70',    // parpados y cejas
  snout: '#8FD0B8',  // hocico
  bone: '#EADFC6',   // cuernos y colmillo
  amber: '#EFA21E',  // iris
  mouth: '#2B1426',
  tongue: '#A8443F',
  gloss: '#E9FBF0',  // brillo del vidriado
  spark: '#FFF2C8',
  smoke: '#D9D2DC',
  coal: '#3B3338',   // brasa apagada
  ember: '#FF6B22',  // brasa
  emberHot: '#FFD166',
  cobalt: '#4C74FF', // brasa en error
  cobaltHot: '#CAD8FF'
};

/* Geometria fija, en el viewBox -16 -8 352 352. */
const HEAD = 'M160 72C208 72 250 94 254 146C256 172 240 184 237 202' +
  'C235 222 238 236 224 250C206 266 184 264 160 264C136 264 114 266 96 250' +
  'C82 236 85 222 83 202C80 184 64 172 66 146C70 94 112 72 160 72Z';
const SNOUT = 'M160 156C168 146 182 138 196 146C208 154 214 170 220 186' +
  'C230 212 224 236 206 246C190 254 176 254 160 254C144 254 130 254 114 246' +
  'C96 236 90 212 100 186C106 170 112 154 124 146C138 138 152 146 160 156Z';
const HORN = 'M190 90C202 72 222 58 246 50C246 72 240 92 228 110Z';
const SOCKET = 'M-38 6C-34 -26 -14 -36 6 -36C26 -36 40 -18 42 -6' +
  'C38 14 20 28 0 28C-18 28 -32 20 -38 6Z';
const FIN = 'M-8 -30Q26 -56 64 -54Q46 -44 46 -30Q52 -20 70 -16Q50 -12 46 -4' +
  'Q46 8 56 18Q24 22 -8 30Z';
const BROW = 'M-32 7Q-29 -4 -17 -6Q-10 -12 0 -9Q9 -13 19 -8Q29 -8 36 1' +
  'Q12 5 -32 7Z';
const FLAME = 'M160 306C120 312 84 298 66 270C52 266 40 256 30 238' +
  'C44 240 50 238 56 234C44 216 36 194 44 164C58 184 74 196 90 210L160 230' +
  'L230 210C246 196 262 184 276 164C284 194 276 216 264 234' +
  'C270 238 276 240 290 238C280 256 268 266 254 270' +
  'C236 298 200 312 160 306Z';
const GEM = 'M0 -18C8 -9 14 -3 14 5C14 13 8 17 0 17C-8 17 -14 13 -14 5C-14 -3 -8 -9 0 -18Z';
const CURL = 'M-12 8C-18 -6 -2 -14 6 -6C12 0 4 8 -2 3';
const SPARK = 'M0 -7L4 0L0 7L-4 0Z';

const FIN_PIVOT_X = 76;
const EYE_L = { x: 118, y: 130 };
const EYE_R = { x: 202, y: 130 };
const BROW_Y = 103;
const MOUTH_Y = 206;
const EMBER_X = 160;
const EMBER_Y = 276;
const NOSTRIL_X = 140;
const NOSTRIL_Y = 166;
const SMOKE_COUNT = 4;
const SPARK_COUNT = 10;

/* Formas de boca del generador: apertura, anchura, curva. */
const VISEMES: readonly (readonly [number, number, number])[] = [
  [0.85, 0.95, 0], [0.4, 1.1, 0.25], [0.22, 1.15, 0.3],
  [0.62, 0.62, -0.1], [0.28, 0.5, 0], [0.02, 0.85, 0.1], [0.5, 0.8, -0.2]
];

let instances = 0;

function clamp(v: number, lo: number, hi: number): number { return v < lo ? lo : v > hi ? hi : v; }
function lerp(a: number, b: number, t: number): number { return a + (b - a) * t; }
function frac(v: number): number { return v - Math.floor(v); }
function n(v: number): number { return Math.round(v * 100) / 100; }
function rand(lo: number, hi: number): number { return lo + Math.random() * (hi - lo); }

function rgb(hex: string): Rgb {
  let v = parseInt(hex.slice(1), 16);
  return [(v >> 16) & 255, (v >> 8) & 255, v & 255];
}

function mixRgb(a: Rgb, b: Rgb, t: number): Rgb {
  return [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)];
}

function tone(c: Rgb, sat: number, value: number): string {
  let gray = 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2];
  return 'rgb(' +
    Math.round((gray + (c[0] - gray) * sat) * value) + ',' +
    Math.round((gray + (c[1] - gray) * sat) * value) + ',' +
    Math.round((gray + (c[2] - gray) * sat) * value) + ')';
}

const COLORS = Object.fromEntries(
  Object.entries(PALETTE).map(([k, v]) => [k, rgb(v)])
) as Record<keyof typeof PALETTE, Rgb>;
const colorOf = (k: string): Rgb => COLORS[k as keyof typeof PALETTE] ?? COLORS.line;

function fin(key: string): string {
  return '<g data-k="' + key + '">' +
    '<path d="' + FIN + '" data-f="head" data-s="line" stroke-width="5"/>' +
    '<path d="M2 -6L52 -40M2 0L54 -15M2 6L44 12" fill="none" data-s="pool" ' +
    'stroke-width="4" stroke-linecap="round"/></g>';
}

function horn(mirror: boolean): string {
  return '<g' + (mirror ? ' transform="matrix(-1 0 0 1 320 0)"' : '') + '>' +
    '<path d="' + HORN + '" data-f="bone" data-s="line" stroke-width="5"/>' +
    '<path d="M204 80Q218 84 232 94M220 66Q230 70 239 78" fill="none" ' +
    'data-s="line" stroke-width="3" stroke-linecap="round" opacity=".35"/></g>';
}

function eye(side: 'L' | 'R', id: string): string {
  let e = side === 'L' ? EYE_L : EYE_R;
  return '<path d="' + SOCKET + '" data-f="lid" transform="translate(' + e.x + ' ' + e.y + ')' +
    (side === 'L' ? 'scale(-1 1)' : '') + '"/>' +
    '<path data-k="eye' + side + '" data-f="amber"/>' +
    '<g clip-path="url(#' + id + '-eye' + side + ')">' +
    '<ellipse data-k="pupil' + side + '" data-f="line"/>' +
    '<circle data-k="glint' + side + '" r="3.6" data-f="gloss"/></g>' +
    '<path data-k="rim' + side + '" fill="none" data-s="line" ' +
    'stroke-width="6" stroke-linejoin="round" stroke-linecap="round"/>';
}

function repeat(count: number, make: (i: number) => string): string {
  let out = '';
  for (let i = 0; i < count; i++) out += make(i);
  return out;
}

function markup(id: string): string {
  return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-16 -8 352 352" ' +
    'width="100%" height="100%" aria-hidden="true" focusable="false" ' +
    'stroke-linejoin="round">' +
    '<defs>' +
    '<clipPath id="' + id + '-head"><path d="' + HEAD + '"/></clipPath>' +
    '<clipPath id="' + id + '-eyeL"><path data-k="clipL"/></clipPath>' +
    '<clipPath id="' + id + '-eyeR"><path data-k="clipR"/></clipPath>' +
    '<clipPath id="' + id + '-mouth"><path data-k="clipMouth"/></clipPath>' +
    '<radialGradient id="' + id + '-halo"><stop data-k="haloIn" offset=".35"/>' +
    '<stop data-k="haloOut" offset="1" stop-opacity="0"/></radialGradient>' +
    '</defs>' +
    '<g data-k="root">' +
    '<g data-k="flame">' +
    '<path d="' + FLAME + '" data-k="flameOuter" data-s="line" stroke-width="5"/>' +
    '<path d="' + FLAME + '" data-k="flameInner" ' +
    'transform="matrix(.72 0 0 .72 44.8 73.4)"/></g>' +
    /* El halo va detrás de la cabeza para no manchar el hocico. */
    '<circle data-k="halo" cx="' + EMBER_X + '" cy="' + EMBER_Y + '" ' +
    'fill="url(#' + id + '-halo)"/>' +
    fin('finL') + fin('finR') + horn(false) + horn(true) +
    /* El charco de esmalte es la misma cabeza, desplazada y recortada. */
    '<path d="' + HEAD + '" data-f="pool"/>' +
    '<g clip-path="url(#' + id + '-head)">' +
    '<path d="' + HEAD + '" data-f="head" ' +
    'transform="matrix(.97 0 0 .97 4.8 -3)"/></g>' +
    '<path d="' + HEAD + '" fill="none" data-s="line" stroke-width="5"/>' +
    '<path d="M146 92q7 8 14 0q7 8 14 0M153 80q7 7 14 0" ' +
    'fill="none" data-s="pool" stroke-width="4" stroke-linecap="round"/>' +
    '<g data-k="gloss">' +
    '<path d="M92 98C104 86 120 80 138 78C122 86 110 92 100 102' +
    'C96 106 88 103 92 98Z" data-f="gloss" opacity=".7"/></g>' +
    '<path d="' + SNOUT + '" data-f="snout" data-s="pool" stroke-width="4"/>' +
    '<g data-k="glossSnout">' +
    '<path d="M110 186C112 172 118 162 128 156C122 168 120 178 120 190' +
    'C119 196 110 194 110 186Z" data-f="gloss" opacity=".8"/></g>' +
    '<ellipse cx="140" cy="168" rx="7.5" ry="4.8" transform="rotate(24 140 168)" data-f="line"/>' +
    '<ellipse cx="180" cy="168" rx="7.5" ry="4.8" transform="rotate(-24 180 168)" data-f="line"/>' +
    eye('L', id) + eye('R', id) +
    '<path data-k="browL" d="' + BROW + '" data-f="lid" data-s="line" stroke-width="4"/>' +
    '<path data-k="browR" d="' + BROW + '" data-f="lid" data-s="line" stroke-width="4"/>' +
    '<path data-k="mouth" data-f="mouth"/>' +
    '<g clip-path="url(#' + id + '-mouth)">' +
    '<ellipse data-k="tongue" data-f="tongue"/></g>' +
    '<path data-k="mouthRim" fill="none" data-s="line" stroke-width="5" stroke-linecap="round"/>' +
    '<path data-k="fang" data-f="bone" data-s="line" stroke-width="4"/>' +
    '<circle cx="' + EMBER_X + '" cy="' + EMBER_Y + '" r="21" data-f="mouth" ' +
    'data-s="line" stroke-width="5"/>' +
    '<path data-k="gem" d="' + GEM + '"/>' +
    '<path data-k="gemCore" d="' + GEM + '"/>' +
    repeat(SMOKE_COUNT, (i: number) => {
      return '<g data-k="smoke' + i + '"><path d="' + CURL + '" fill="none" ' +
        'data-s="smoke" stroke-width="7" stroke-linecap="round"/></g>';
    }) +
    repeat(SPARK_COUNT, (i: number) => {
      return '<path data-k="spark' + i + '" d="' + SPARK + '"/>';
    }) +
    '</g></svg>';
}

/* ---------- Ticker compartido por todas las instancias ---------- */

interface Stepper {
  /** Devuelve true si necesita otro fotograma. */
  step(now: number): boolean
  /** Olvida la marca de tiempo para no saltar tras una pausa. */
  resume(): void
}
const rigs: Stepper[] = [];
let frame = 0;

function tick(now: number): void {
  frame = 0;
  if (document.hidden) return;
  let more = false;
  for (const r of rigs.slice()) if (r.step(now)) more = true;
  if (more && rigs.length) frame = window.requestAnimationFrame(tick);
}

function startTicker() {
  if (frame || document.hidden || !rigs.length) return;
  for (const r of rigs) r.resume();
  frame = window.requestAnimationFrame(tick);
}

function stopTicker() {
  if (frame) window.cancelAnimationFrame(frame);
  frame = 0;
}

const motionQuery = window.matchMedia
  ? window.matchMedia('(prefers-reduced-motion: reduce)')
  : null;

function reducedMotion() { return !!(motionQuery && motionQuery.matches); }

/* Un unico juego de listeners para todas las instancias. */
let listening = false;
function wake() { startTicker(); }
function listen(on: boolean) {
  if (on === listening) return;
  listening = on;
  const op = on ? 'addEventListener' : 'removeEventListener';
  document[op]('visibilitychange', wake);
  if (motionQuery && motionQuery[op]) motionQuery[op]('change', wake);
}

/* ---------- Fabrica ---------- */

export function createCharacter(
  container: HTMLElement,
  options?: { state?: CharacterState }
): Rig {

  let id = 'drakter-' + (++instances);
  let state: CharacterState = 'idle';
  const requested = options?.state;
  if (requested !== undefined) {
    if (isState(requested)) {
      state = requested;
    } else {
      console.warn('Estado desconocido de Drakter: ' + String(requested));
    }
  }

  container.innerHTML = markup(id);
  const found = container.querySelector('svg');
  if (!found) throw new Error('Drakter: el marcado del personaje no contiene <svg>');
  const svg: SVGSVGElement = found
  const partMap = new Map<string, SVGElement>();
  svg.querySelectorAll<SVGElement>('[data-k]').forEach((el) => {
    partMap.set(el.getAttribute('data-k') ?? '', el);
  });
  const part = (name: string): SVGElement => {
    const el = partMap.get(name);
    if (!el) throw new Error('Drakter: pieza desconocida ' + name);
    return el;
  };
  const fills = Array.from(svg.querySelectorAll<SVGElement>('[data-f]'));
  const strokes = Array.from(svg.querySelectorAll<SVGElement>('[data-s]'));

  const cur = {} as Params;
  for (const k of PARAM_NAMES) cur[k] = 0;

  let last = 0;
  let time = rand(0, 30);     // desfasa respiracion y humo entre instancias
  let enteredAt = 0;
  let phase = rand(0, 6.28);
  let blinkAt = rand(1, 5);
  let blinkFrom = -1;
  let crackleValue = 1;
  let crackleLeft = 0;
  let toneKey = '';
  let alive = true;
  const talk: Talk = {
    o: 0, w: 1, c: 0,       // valores suavizados
    to: 0, tw: 1, tc: 0,    // destino actual
    left: 0, phrase: rand(1, 2.4), rest: 0, last: -1
  };

  const written = new WeakMap<Element, Map<string, string>>();
  function put(el: Element, attr: string, value: string | number): void {
    let seen = written.get(el);
    if (!seen) {
      seen = new Map<string, string>();
      written.set(el, seen);
    }
    const v = String(value);
    if (seen.get(attr) !== v) {
      seen.set(attr, v);
      el.setAttribute(attr, v);
    }
  }

  function target(key: ParamName): number {
    const def = STATES[state];
    let reduced = reducedMotion();
    let s = def.settle && def.settle[key];
    if (s) {
      if (reduced) return s[1];
      let elapsed = (time - enteredAt) * 1000;
      return s[1] + (s[0] - s[1]) * Math.exp(-elapsed / s[2]);
    }
    return def.set[key] ?? PARAMS[key];
  }

  function stepTalk(dt: number): void {
    talk.left -= dt;
    talk.phrase -= dt;
    if (talk.left <= 0) {
      if (talk.phrase <= 0) {
        /* Fin de frase: silencio con la boca casi cerrada. */
        talk.phrase = rand(1.1, 3);
        talk.to = 0.02;
        talk.tw = 0.88;
        talk.tc = 0.1;
        talk.left = rand(0.26, 0.6);
      } else if (Math.random() < 0.14) {
        /* Pausa breve entre palabras. */
        talk.to = 0.03;
        talk.tw = 0.9;
        talk.tc = 0;
        talk.left = rand(0.08, 0.18);
      } else {
        let i: number;
        do { i = Math.floor(Math.random() * VISEMES.length); } while (i === talk.last);
        talk.last = i;
        const v = VISEMES[i] as readonly [number, number, number];
        talk.to = v[0] * rand(0.75, 1.1);
        talk.tw = v[1];
        talk.tc = v[2];
        talk.left = rand(0.07, 0.2);
      }
    }
    let k = 1 - Math.exp(-dt * 24);
    talk.o += (talk.to - talk.o) * k;
    talk.w += (talk.tw - talk.w) * k;
    talk.c += (talk.tc - talk.c) * k;
  }

  function stepBlink(): number {
    if (cur.blink < 0.05) {
      blinkFrom = -1;
      return 1;
    }
    if (blinkFrom < 0 && time >= blinkAt) blinkFrom = time;
    if (blinkFrom < 0) return 1;
    let u = (time - blinkFrom) / 0.17;
    if (u >= 1) {
      blinkFrom = -1;
      let gap = Math.random() < 0.18 ? 0.24 : rand(2.4, 7);
      blinkAt = time + gap / cur.blink;
      return 1;
    }
    return 1 - Math.sin(u * Math.PI);
  }

  function stepCrackle(dt: number): number {
    crackleLeft -= dt;
    if (crackleLeft <= 0) {
      // <= 3 Hz y amplitud <= 0.3 (WCAG 2.3.1: sin destellos rapidos ni intensos).
      crackleLeft = rand(0.35, 0.8);
      crackleValue = rand(0.7, 1);
    }
    return lerp(1, crackleValue, cur.crackle);
  }

  function drawEye(side: 'L' | 'R', e: { x: number; y: number }, open: number, bend: number, gazeX: number, gazeY: number): void {
    let outer = side === 'L' ? -1 : 1;
    let ox = e.x + outer * 28;
    let ix = e.x - outer * 28;
    let oy = e.y - 2;
    let iy = e.y + 3;
    let my = e.y + bend * 20;
    let d = 'M' + ix + ' ' + iy +
      'Q' + e.x + ' ' + n(my - open * 46) + ' ' + ox + ' ' + oy +
      'Q' + e.x + ' ' + n(my + open * 30) + ' ' + ix + ' ' + iy + 'Z';
    put(part('eye' + side), 'd', d);
    put(part('clip' + side), 'd', d);
    put(part('rim' + side), 'd', d);
    let px = e.x + gazeX * 12;
    let py = e.y - 2 + gazeY * 9;
    let pupil = part('pupil' + side);
    let rx = lerp(3, 14.5, cur.pupil);
    put(pupil, 'cx', n(px));
    put(pupil, 'cy', n(py));
    put(pupil, 'rx', n(rx));
    put(pupil, 'ry', 21);
    let glint = part('glint' + side);
    put(glint, 'cx', n(px - rx * 0.35 - 1));
    put(glint, 'cy', n(py - 9));
  }

  function drawBrow(el: Element, x: number, angle: number, raise: number, mirror: boolean): void {
    put(el, 'transform',
      'translate(' + x + ' ' + n(BROW_Y - raise) + ')' +
      (mirror ? 'scale(-1 1)' : '') +
      'rotate(' + n(-angle) + ')');
  }

  function drawMouth(open: number, curve: number, width: number): void {
    let hw = 68 * width;
    let cx = 160 + cur.mouthX;
    let xl = cx - hw;
    let xr = cx + hw;
    let yc = MOUTH_Y - curve * 13;
    let yu = MOUTH_Y + curve * 13;
    let yl = yu + open * 86;
    let d = 'M' + n(xl) + ' ' + n(yc) +
      'Q' + n(cx) + ' ' + n(yu) + ' ' + n(xr) + ' ' + n(yc) +
      'Q' + n(cx) + ' ' + n(yl) + ' ' + n(xl) + ' ' + n(yc) + 'Z';
    put(part('mouth'), 'd', d);
    put(part('clipMouth'), 'd', d);
    put(part('mouthRim'), 'd', d);

    let tongue = part('tongue');
    let lowY = (yc + yl) / 2;
    put(tongue, 'cx', n(cx));
    put(tongue, 'cy', n(lowY + 5));
    put(tongue, 'rx', n(hw * 0.56));
    put(tongue, 'ry', n(6 + open * 20));

    /* El colmillo se apoya siempre sobre la curva del labio superior. */
    let t = 0.74;
    let fx = lerp(xl, xr, t);
    let fy = (1 - t) * (1 - t) * yc + 2 * t * (1 - t) * yu + t * t * yc;
    let size = cur.fang * clamp(0.55 + width * 0.45, 0.6, 1.1);
    let w = 12 * size;
    let h = 31 * size;
    put(part('fang'), 'd',
      'M' + n(fx - w) + ' ' + n(fy - 1) +
      'Q' + n(fx - w * 0.6) + ' ' + n(fy + h * 0.62) + ' ' + n(fx + 2) + ' ' + n(fy + h) +
      'Q' + n(fx + w * 0.7) + ' ' + n(fy + h * 0.5) + ' ' + n(fx + w) + ' ' + n(fy - 1) + 'Z');
  }

  function drawEmber(level: number, sat: number, value: number): Colors {
    let hue = cur.emberHue;
    let color = mixRgb(COLORS.ember, COLORS.cobalt, hue);
    let hot = mixRgb(COLORS.emberHot, COLORS.cobaltHot, hue);
    let lit = clamp(level * 1.7, 0, 1);
    let core = clamp((level - 0.2) / 0.5, 0, 1);
    let gemColor = mixRgb(COLORS.coal, color, lit);
    let size = 0.8 + level * 0.25;
    put(part('gem'), 'fill', tone(gemColor, sat, value));
    put(part('gem'), 'transform',
      'translate(' + EMBER_X + ' ' + EMBER_Y + ')scale(' + n(size) + ')');
    put(part('gemCore'), 'fill', tone(mixRgb(gemColor, hot, core), sat, value));
    put(part('gemCore'), 'transform',
      'translate(' + EMBER_X + ' ' + EMBER_Y + ')scale(' + n(size * 0.48) + ')');
    put(part('haloIn'), 'stop-color', tone(color, sat, value));
    put(part('haloOut'), 'stop-color', tone(color, sat, value));
    put(part('halo'), 'r', n(24 + level * 40));
    put(part('halo'), 'opacity', n(clamp(level * 0.9, 0, 0.75)));
    return { color: color, hot: hot };
  }

  function drawFlame(colors: Colors, sat: number, value: number, wobble: number): void {
    let f = cur.flame;
    let group = part('flame');
    if (f < 0.02) {
      put(group, 'visibility', 'hidden');
      return;
    }
    put(group, 'visibility', 'visible');
    let scale = 0.62 + 0.5 * f;
    put(group, 'transform',
      'translate(160 262)rotate(' + n(wobble * 1.6) + ')' +
      'scale(' + n(scale * (1 + wobble * 0.02)) + ' ' + n(scale) + ')' +
      'translate(-160 -262)');
    put(part('flameOuter'), 'fill', tone(colors.color, sat, value));
    put(part('flameInner'), 'fill', tone(colors.hot, sat, value));
  }

  function drawSmoke(t: number): void {
    for (let i = 0; i < SMOKE_COUNT; i++) {
      let p = frac(t * 0.21 + i / SMOKE_COUNT);
      let alpha = Math.sin(p * Math.PI) * clamp(cur.smoke * 1.3, 0, 1);
      let el = part('smoke' + i);
      if (alpha < 0.01) {
        put(el, 'visibility', 'hidden');
        continue;
      }
      /* Sube fino por el puente entre los ojos y se riza sobre las cejas. */
      let free = clamp((p - 0.42) / 0.58, 0, 1);
      let x = NOSTRIL_X + 20 * clamp(p / 0.1, 0, 1) +
        Math.sin(p * 7 + i * 2.1) * 14 * free;
      let y = NOSTRIL_Y + 2 - 158 * p;
      put(el, 'visibility', 'visible');
      put(el, 'opacity', n(alpha));
      put(el, 'transform',
        'translate(' + n(x) + ' ' + n(y) + ')' +
        'rotate(' + n(p * 70 - 20 + i * 40) + ')' +
        'scale(' + n(0.3 + free * 1.3) + ')');
    }
  }

  function drawSparks(t: number, colors: Colors, sat: number, value: number): void {
    for (let i = 0; i < SPARK_COUNT; i++) {
      let el = part('spark' + i);
      let speed = 0.9 + (i % 3) * 0.28;
      let p = frac(t * speed + i * 0.317);
      let gate = i / SPARK_COUNT < cur.sparks;
      let alpha = gate ? (1 - p * p) * clamp(cur.sparks * 2.5, 0, 1) : 0;
      if (alpha < 0.01) {
        put(el, 'visibility', 'hidden');
        continue;
      }
      let side = i % 2 ? 1 : -1;
      let angle = 0.32 + (i % 5) * 0.2;
      let reach = 96 + (i % 4) * 16;
      let x = EMBER_X + side * Math.cos(angle) * reach * p;
      let y = EMBER_Y - Math.sin(angle) * reach * p + 74 * p * p;
      put(el, 'visibility', 'visible');
      put(el, 'opacity', n(alpha));
      put(el, 'fill', tone(mixRgb(COLORS.spark, colors.color, p), sat, value));
      put(el, 'transform',
        'translate(' + n(x) + ' ' + n(y) + ')rotate(' + n(p * 200 + i * 37) + ')');
    }
  }

  function retone(sat: number, value: number): void {
    let key = n(sat) + '/' + n(value);
    if (key === toneKey) return;
    toneKey = key;
    fills.forEach(function (el) {
      put(el, 'fill', tone(colorOf(el.getAttribute('data-f') ?? ''), sat, value));
    });
    strokes.forEach(function (el) {
      put(el, 'stroke', tone(colorOf(el.getAttribute('data-s') ?? ''), sat, value));
    });
  }

  function draw(dt: number): void {
    let reduced = reducedMotion();
    let live = !reduced;
    let t = live ? time : 1.7;     // particulas congeladas con movimiento reducido

    let breath = 0;
    if (live) {
      phase += dt * cur.breathRate * Math.PI * 2;
      breath = Math.sin(phase) * cur.breath;
    }

    let blink = live ? stepBlink() : 1;
    let flicker = live ? stepCrackle(dt) : 1;
    if (live && cur.talk > 0.01) stepTalk(dt);

    let talkO = live ? talk.o : 0.45;
    let talkW = live ? talk.w : 0.95;
    let talkC = live ? talk.c : 0;
    let scan = live ? cur.scan : 0;
    let nod = scan * Math.sin(time * 9.5) * 1.3;
    let speak = cur.talk * (live ? 1 : 0);

    let tilt = cur.headTilt + speak * Math.sin(time * 1.3) * 1.6;
    let y = cur.headY + breath * 1.6 + nod;
    let scaleY = cur.headScale * (1 + breath * 0.012);
    put(part('root'), 'transform',
      'translate(160 ' + n(262 + y) + ')rotate(' + n(tilt) + ')' +
      'scale(' + n(cur.headScale) + ' ' + n(scaleY) + ')translate(-160 -262)');

    /* El brillo no gira con la pieza: se queda con la luz de la sala. */
    let glossShift = 'translate(' + n(-tilt * 0.9) + ' ' + n(tilt * 0.3) + ')';
    put(part('gloss'), 'transform', glossShift);
    put(part('glossSnout'), 'transform', glossShift);

    let lift = speak * talkO * 7;
    put(part('finR'), 'transform',
      'translate(' + (320 - FIN_PIVOT_X) + ' 130)rotate(' + n(-(cur.finR + lift)) + ')');
    put(part('finL'), 'transform',
      'translate(' + FIN_PIVOT_X + ' 130)scale(-1 1)rotate(' + n(-(cur.finL + lift)) + ')');

    let gazeX = cur.gazeX;
    if (scan) gazeX += scan * (Math.sin(time * 2.7) + 0.4 * Math.sin(time * 6.1)) * 0.6;
    let open = cur.eyeOpen * blink;
    drawEye('L', EYE_L, open, cur.lidBend, gazeX, cur.gazeY);
    drawEye('R', EYE_R, open, cur.lidBend, gazeX, cur.gazeY);

    let browLift = cur.talk * talkO * 4;
    drawBrow(part('browL'), EYE_L.x - 2, cur.browAngleL, cur.browRaiseL + browLift, true);
    drawBrow(part('browR'), EYE_R.x + 2, cur.browAngleR, cur.browRaiseR + browLift, false);

    drawMouth(
      Math.max(0, cur.mouthOpen + cur.talk * talkO),
      cur.mouthCurve + cur.talk * talkC,
      cur.mouthWidth * (1 + cur.talk * (talkW - 1))
    );

    let sat = clamp(cur.sat, 0, 1);
    let value = clamp(cur.value, 0, 1);
    retone(sat, value);

    let level = clamp((cur.ember + breath * 0.03 + speak * talkO * 0.25) * flicker, 0, 1);
    let colors = drawEmber(level, sat, value);
    drawFlame(colors, sat, value, live ? Math.sin(time * 11) + Math.sin(time * 17.3) * 0.6 : 0);
    drawSmoke(t);
    drawSparks(t, colors, sat, value);
  }

  function advance(dt: number): boolean {
    time += dt;
    let k = 1 - Math.exp(-dt * STATES[state].rate);
    let moving = false;
    for (const key of PARAM_NAMES) {
      let goal = target(key);
      cur[key] += (goal - cur[key]) * k;
      if (Math.abs(goal - cur[key]) > 0.001) moving = true;
      else if (reducedMotion()) cur[key] = goal;
    }
    draw(dt);
    return !reducedMotion() || moving;
  }

  const rig: Stepper = {
    step(now: number) {
      let dt = last ? Math.min((now - last) / 1000, 0.05) : 0;
      last = now;
      return advance(dt);
    },
    resume() { last = 0; }
  };

  function setState(name: string): boolean {
    if (!alive) return false;
    if (typeof name !== 'string' || !isState(name)) {
      console.warn('Estado desconocido de Drakter: ' + String(name));
      return false;
    }
    if (name !== state) {
      state = name;
      enteredAt = time;
      startTicker();
    }
    return true;
  }

  function destroy() {
    if (!alive) return;
    alive = false;
    rigs.splice(rigs.indexOf(rig), 1);
    if (!rigs.length) {
      stopTicker();
      listen(false);
    }
    if (svg.parentNode === container) container.removeChild(svg);
  }

  /* Primer fotograma ya en pose: nunca se ve la pieza a medio montar. */
  enteredAt = time;
  for (const k of PARAM_NAMES) cur[k] = target(k);
  draw(0);

  rigs.push(rig);
  listen(true);
  startTicker();

  return {
    setState,
    getState: () => state,
    destroy
  };
}
