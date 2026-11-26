// Cerebro del Relojero v2: convierte (estado, voz, visema, cursor, clics, hover, eventos) en una Pose.
// Independiente del render. Cara = expresión base del estado + gestos superpuestos, todo con muelles.
// El corazón sigue siendo un escape real: cada semioscilación del volante hace avanzar el tren un paso.

import { MOUTH, type Viseme } from './voice';

export const STATES = ['idle', 'listening', 'thinking', 'speaking', 'executing', 'success', 'error', 'interrupted', 'offline'] as const;
export type AvatarState = (typeof STATES)[number];
export type Zone = 'crown' | 'eye' | 'movement' | 'mouth' | 'chest' | 'face' | 'halo';
export type RGB = [number, number, number];
export const HALO = { sweep: 0, vu: 1, chase: 2, progress: 3, flash: 4, error: 5, hold: 6, off: 7, tut: 8 } as const;

/** Rasgos faciales. Cejas: ángulo + = extremo exterior arriba (arco/severidad), − = caído (preocupación).
 *  Párpados: cobertura 0..1 (superior desde arriba, inferior desde abajo); tilt + = ceño, − = pena. */
export interface Face {
  bAL: number; bAR: number; lL: number; lR: number; furrow: number;
  uL: number; uR: number; dL: number; dR: number; tL: number; tR: number;
  smL: number; smR: number; w: number; rnd: number; jaw: number; pupil: number; blush: number;
}
const F = (o: Partial<Face>): Face => ({ bAL: 0, bAR: 0, lL: 0, lR: 0, furrow: 0, uL: 0.4, uR: 0.38, dL: 0.08, dR: 0.08, tL: 0, tR: 0, smL: 0.1, smR: 0.18, w: 0, rnd: 0, jaw: 0, pupil: 1, blush: 0, ...o });

/** Las siete expresiones del brief, más tres de servicio. L/R = izquierda/derecha en pantalla. */
export const EXPR = {
  serenidad: F({}),
  atencion: F({ uL: 0.1, uR: 0.1, dL: 0.02, dR: 0.02, lL: 0.065, lR: 0.065, bAL: -0.04, bAR: -0.04, smL: 0.06, smR: 0.1, pupil: 1.25 }),
  curiosidad: F({ uL: 0.12, uR: 0.3, lL: 0.1, lR: 0.0, bAL: 0.2, bAR: -0.06, smL: 0.12, smR: 0.22, pupil: 1.3 }),
  ironia: F({ bAR: 0.42, lR: 0.11, bAL: -0.1, lL: -0.02, uL: 0.56, uR: 0.14, dL: 0.24, dR: 0.04, tL: 0.16, smR: 0.95, smL: -0.2, pupil: 1.05 }),
  satisfaccion: F({ uL: 0.4, uR: 0.4, dL: 0.28, dR: 0.28, lL: 0.035, lR: 0.035, bAL: -0.14, bAR: -0.14, smL: 0.75, smR: 0.8, blush: 0.8, pupil: 1.15 }),
  preocupacion: F({ bAL: -0.4, bAR: -0.4, lL: 0.04, lR: 0.04, furrow: 0.8, uL: 0.26, uR: 0.26, dL: 0, dR: 0, tL: -0.36, tR: -0.36, smL: -0.7, smR: -0.62, w: -0.25, pupil: 0.8 }),
  sorpresa: F({ lL: 0.13, lR: 0.13, bAL: 0.03, bAR: 0.03, uL: 0.02, uR: 0.02, dL: 0, dR: 0, smL: 0, smR: 0, jaw: 0.5, rnd: 0.6, pupil: 0.72 }),
  foco: F({ uL: 0.46, uR: 0.42, dL: 0.16, dR: 0.14, bAL: 0.1, bAR: 0.12, lL: -0.02, lR: -0.015, furrow: 0.35, tL: 0.12, tR: 0.12, smL: 0.02, smR: 0.08 }),
  sueno: F({ uL: 1, uR: 1, dL: 0.25, dR: 0.25, lL: -0.03, lR: -0.03, bAL: -0.15, bAR: -0.15, smL: -0.05, smR: -0.05, pupil: 0.6 }),
  hastio: F({ uL: 0.62, uR: 0.6, dL: 0.1, dR: 0.1, bAL: -0.1, bAR: -0.08, lL: -0.01, lR: -0.01, smL: -0.02, smR: 0.04 }),
};
export type ExprName = keyof typeof EXPR;
export const EXPR_LABEL: Record<string, string> = { serenidad: 'Serenidad', atencion: 'Atención', curiosidad: 'Curiosidad', ironia: 'Ironía', satisfaccion: 'Satisfacción contenida', preocupacion: 'Preocupación', sorpresa: 'Sorpresa breve' };
const KEYS = Object.keys(EXPR.serenidad) as (keyof Face)[];
const BASE_EXPR: Record<AvatarState, ExprName> = {
  idle: 'serenidad', listening: 'atencion', thinking: 'curiosidad', speaking: 'serenidad', executing: 'foco',
  success: 'satisfaccion', error: 'preocupacion', interrupted: 'sorpresa', offline: 'sueno',
};

export interface Pose {
  state: AvatarState; t: number; st: number;
  yaw: number; pitch: number; roll: number; lean: number; rise: number; breath: number; shrug: number;
  gx: number; gy: number; face: Face; pupilL: number; pupilR: number; browSpin: number;
  chime: number; balance: number; pallet: number; train: number; barrel: number; orbit: number; crown: number; beat: number;
  loupe: number; glow: number; cold: number; accent: RGB; key: RGB;
  halo: number; haloVal: number; haloSpin: number; level: number; hover: Zone | null; flash: number; moving: boolean;
}

const ACCENT: Record<AvatarState, RGB> = {
  idle: [0.32, 0.78, 1], listening: [0.46, 0.9, 1], thinking: [0.22, 0.56, 1], speaking: [0.38, 0.82, 1],
  executing: [0.3, 0.72, 1], success: [0.96, 0.92, 0.82], error: [1, 0.52, 0.18], interrupted: [0.78, 0.92, 1], offline: [0.16, 0.26, 0.5],
};
const HALO_OF: Record<AvatarState, number> = {
  idle: HALO.sweep, listening: HALO.vu, thinking: HALO.chase, speaking: HALO.vu, executing: HALO.progress,
  success: HALO.flash, error: HALO.error, interrupted: HALO.hold, offline: HALO.off,
};

/** Muelle amortiguado con subpasos (estable aunque sea rígido). */
class Ch {
  v = 0;
  constructor(public x = 0, private k = 90, private d = 17) {}
  step(target: number, dt: number): number {
    const n = Math.max(1, Math.ceil(dt * 120)), h = dt / n;
    for (let i = 0; i < n; i++) { this.v += ((target - this.x) * this.k - this.v * this.d) * h; this.x += this.v * h; }
    if (!Number.isFinite(this.x)) { this.x = target; this.v = 0; }
    return this.x;
  }
}

type Gesture = 'wind' | 'loupe' | 'glance' | 'smirk' | 'chime' | 'tilt' | 'attend' | 'spin' | 'heart' | 'halo' | 'peek' | 'greet' | 'bored' | 'tut' | 'sigh' | 'mouthpoke';
const IDLE: Gesture[] = ['glance', 'smirk', 'wind', 'loupe', 'glance', 'tilt', 'chime', 'smirk'];
const DUR: Record<Gesture, number> = { wind: 2.4, loupe: 3.2, glance: 1.8, smirk: 2.6, chime: 1.6, tilt: 2.2, attend: 1.2, spin: 1.6, heart: 1.9, halo: 1.8, peek: 1.5, greet: 2.2, bored: 6.5, tut: 3.4, sigh: 2.0, mouthpoke: 1.4 };

function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => { a = (a + 0x6d2b79f5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const clamp = (v: number, a: number, b: number): number => Math.min(b, Math.max(a, v));
const bell = (u: number): number => Math.sin(Math.PI * clamp(u, 0, 1));
const plateau = (u: number, e = 0.2): number => clamp(Math.min(u / e, (1 - u) / e), 0, 1);
const easeOut = (u: number): number => 1 - Math.pow(1 - clamp(u, 0, 1), 3);
const STEP = (Math.PI * 2) / 30;
const mixFace = (a: Face, b: Face, k: number): void => { if (k <= 0) return; for (const key of KEYS) a[key] += (b[key] - a[key]) * k; };

export class Brain {
  state: AvatarState = 'idle';
  voice = 0; viseme: Viseme | null = null;
  cursor = { x: 0, y: 0, active: false };
  hover: Zone | null = null;
  microGestures = true; reduced = false;
  /** Fuerza una expresión (hoja de expresiones y pruebas). */
  exprOverride: ExprName | null = null;
  private rand = rng(0x7e10);
  private t = 0; private st = 0; private idleFor = 0; private typingUntil = -1;
  private c = {
    yaw: new Ch(0, 40, 11), pitch: new Ch(0, 40, 11), roll: new Ch(0, 34, 10), lean: new Ch(0, 50, 10), rise: new Ch(0, 60, 12), shrug: new Ch(0, 80, 10),
    gx: new Ch(0, 280, 30), gy: new Ch(0, 280, 30), loupe: new Ch(0, 70, 10), glow: new Ch(1, 30, 11), cold: new Ch(0, 10, 7),
    amp: new Ch(4.2, 18, 9), freq: new Ch(2.5, 6, 6), haloSpin: new Ch(0, 8, 6),
  };
  private fc: Record<keyof Face, Ch> = Object.fromEntries(KEYS.map((k) => {
    const [kk, dd] = k.startsWith('u') || k.startsWith('d') ? [340, 32] : k === 'jaw' ? [900, 46] : k === 'w' || k === 'rnd' ? [520, 40] : k.startsWith('sm') ? [130, 16] : k === 'blush' ? [12, 7] : [170, 17];
    return [k, new Ch(EXPR.serenidad[k], kk, dd)];
  })) as Record<keyof Face, Ch>;
  private face: Face = F({});
  private headX = 0; private headY = 0;
  private acc: RGB = [...ACCENT.idle];
  private env = 0; private slow = 0;
  private blinkAt = 2; private blink = 0;
  private gesture: Gesture | null = null; private gt = 0; private nextGesture = 4; private gi = 0;
  private clicks = 0; private lastClick = -9;
  private phase = 0; private beats = 0; private lastBeat = -1; private boost = 0; private boostV = 0;
  private pal = new Ch(0, 2200, 70); private barrel = 0; private orbit = 0; private crown = 0; private crownV = 0;
  private spinAcc = 0; private spinCh = new Ch(0, 28, 7); private spun = false; private gestureSpun = false;
  private chimeAt = -10; private flash = 0; private shake = 0; private shakeV = 0; private loupeHeld = false; private haloSpinAcc = 0;

  /** Cualquier señal del usuario reinicia el reloj del aburrimiento. */
  poke(): void { this.idleFor = 0; if (this.gesture === 'bored') { this.gesture = 'attend'; this.gt = 0; } }

  setState(s: AvatarState): void {
    if (s === this.state) return;
    const prev = this.state;
    this.state = s; this.st = 0; this.gesture = null; this.nextGesture = this.t + 4; this.poke();
    if (s === 'success') { this.chimeAt = this.t + 0.3; this.flash = 1; this.crownV += 18; }
    if (s === 'error') { this.shakeV = 9; this.boostV -= 5; this.flash = 0.6; }
    if (s === 'interrupted') { this.c.lean.v -= 3; this.flash = 0.8; }
    if (prev === 'offline') { this.crownV += 25; this.c.amp.v += 20; }
  }

  notify(e: 'userTyping' | 'focus' | 'blur'): void {
    if (e === 'userTyping') { this.typingUntil = this.t + 1.4; this.poke(); return; }
    if (this.state === 'offline' || this.state === 'interrupted') return;
    if (e === 'focus') { this.poke(); this.play('greet'); } else this.play('sigh');
  }

  click(z: Zone): void {
    this.flash = 1; this.poke();
    if (this.state === 'offline') { this.c.glow.v += 3; this.crownV += 8; return; }
    if (this.state === 'interrupted') return;
    this.clicks = this.t - this.lastClick < 1.8 ? this.clicks + 1 : 1; this.lastClick = this.t;
    if (this.clicks >= 5) { this.clicks = 0; this.play('tut'); return; } // «¿Se divierte, señor?»
    const map: Record<Zone, Gesture> = { crown: 'wind', eye: 'peek', movement: 'spin', mouth: 'mouthpoke', chest: 'heart', face: 'attend', halo: 'halo' };
    if (z === 'eye') this.loupeHeld = !this.loupeHeld;
    this.play(map[z]);
  }

  private play(g: Gesture): void {
    this.gesture = g; this.gt = 0;
    if (g === 'chime' || g === 'greet') this.chimeAt = this.t + (g === 'greet' ? 0.5 : 0.15);
    if (g === 'wind') this.crownV += 14;
    if (g === 'spin') this.boostV += 22;
    if (g === 'halo') this.haloSpinAcc += Math.PI * 2;
    if (g === 'tut') this.haloSpinAcc -= Math.PI / 6;
  }

  update(rawDt: number): Pose {
    const dt = Math.min(rawDt, 0.05);
    this.t += dt; this.st += dt; this.idleFor += dt;
    const { t, st, state: s, c } = this;
    const R = this.reduced;

    // Voz: ataque rápido, caída lenta.
    const v = clamp(this.voice, 0, 1);
    this.env += (v - this.env) * (1 - Math.exp(-dt * (v > this.env ? 38 : 11)));
    this.slow += (this.env - this.slow) * (1 - Math.exp(-dt * 4));
    const peak = clamp((this.env - this.slow) * 2.4, 0, 1);

    // Mirada: los ojos van primero; la cabeza les sigue con retraso y peso.
    const cx = this.cursor.active ? this.cursor.x : 0, cy = this.cursor.active ? this.cursor.y : 0;
    const lag = 1 - Math.exp(-dt / 0.42);
    this.headX += (cx - this.headX) * lag; this.headY += (cy - this.headY) * lag;
    let yaw = this.headX * 0.24, pitch = this.headY * 0.13, roll = -this.headX * 0.025, lean = 0, rise = 0, shrug = 0;
    let gx = cx, gy = cy;
    let loupe = this.loupeHeld ? 1 : 0, glow = 1, cold = 0;
    let amp = 4.2, freq = 2.5, hack = false, boostTarget = 0, orbitSpeed = 0.35, barrelSpeed = 0.15, haloVal = 0, halo: number = HALO_OF[s];
    const breath = 0.5 + 0.5 * Math.sin(t * 1.2);
    yaw += Math.sin(t * 0.29) * 0.02; roll += Math.sin(t * 0.21 + 1) * 0.012; rise += breath * 0.014; pitch += Math.sin(t * 0.37 + 2) * 0.008;

    // Expresión base del estado.
    const f = this.face; Object.assign(f, EXPR[BASE_EXPR[s]]);
    switch (s) {
      case 'idle': break;
      case 'listening':
        roll += 0.09; lean = 0.55; pitch += 0.04; yaw += 0.04; f.pupil += this.env * 0.25;
        amp = 2.6; freq = 1.6; orbitSpeed = 0.2; haloVal = this.env; break;
      case 'thinking':
        gx = 0.6 + Math.sin(t * 0.7) * 0.25; gy = -0.72 + Math.sin(t * 1.1) * 0.12;
        yaw = 0.15 + this.headX * 0.08; pitch = -0.09; roll = -0.06; amp = 4.6; freq = 4; boostTarget = 1.6; orbitSpeed = 2.2; haloVal = t; break;
      case 'speaking': {
        const vis = this.viseme ? MOUTH[this.viseme] : null, lvl = this.env;
        if (vis) { f.jaw = vis[0] * clamp(lvl * 1.45, 0.2, 1); f.w = (vis[1] - 0.9) * 1.6; f.rnd = vis[2]; f.smL += vis[3] * 0.4; f.smR += vis[3] * 0.4; }
        else { f.jaw = lvl * 0.9; f.rnd = 0.15; }
        const acc = clamp((peak - 0.3) * 1.7, 0, 1);
        f.lL += acc * 0.05; f.lR += acc * 0.045; f.bAL -= acc * 0.04; f.bAR -= acc * 0.03; f.uL -= acc * 0.1; f.uR -= acc * 0.1;
        pitch += acc * 0.06 - 0.01; yaw += Math.sin(t * 0.8) * 0.035; roll += Math.sin(t * 0.55) * 0.022;
        // Entre frases, la media sonrisa de quien sabe más de lo que dice.
        if (lvl < 0.02 && Math.sin(t * 0.9) > 0.6) mixFace(f, EXPR.ironia, 0.35);
        glow = 1 + lvl * 0.15; freq = 2.5 + lvl * 1.5; orbitSpeed = 0.5 + lvl; barrelSpeed = 0.3 + lvl; haloVal = lvl; break;
      }
      case 'executing': {
        const look = Math.sin(t * 1.1) > 0.8;
        loupe = 1; pitch = 0.13; yaw = -0.06; gx = look ? cx : 0.1 + Math.sin(t * 2.3) * 0.25; gy = look ? cy : 0.75;
        if (look) mixFace(f, EXPR.atencion, 0.5);
        glow = 1.1; amp = 4.8; freq = 5; boostTarget = 3; orbitSpeed = 1.2; barrelSpeed = 0.6; haloVal = (st / 4.5) % 1; break;
      }
      case 'success': {
        const b = bell((st - 0.12) / 1.2);
        pitch = st < 0.12 ? -0.06 : b * 0.22; lean = st < 0.12 ? -0.15 : b * 0.28; rise += st < 0.12 ? 0.02 : 0; shrug = 0.3 * bell(st / 0.8);
        if (st > 1.6) mixFace(f, EXPR.ironia, 0.25 * plateau((st - 1.6) / 2.5)); // «naturalmente»
        glow = 1.25; orbitSpeed = 1.5; haloVal = st; break;
      }
      case 'error': {
        const k = Math.exp(-st * 2);
        roll = 0.06 + 0.04 * k; lean = -0.2; pitch = 0.05; amp = 0; freq = 0.0001; loupe = 0; shrug = 0.25;
        gx = cx * 0.6 - 0.3; gy = Math.max(cy, 0.25); glow = 0.85; orbitSpeed = 0.05; haloVal = st; break;
      }
      case 'interrupted':
        hack = true; lean = -0.65; pitch = -0.05; orbitSpeed = 0; barrelSpeed = 0; loupe = 0;
        if (st > 0.7) { mixFace(f, EXPR.atencion, clamp((st - 0.7) / 0.5, 0, 1)); f.jaw *= 0; }
        break;
      case 'offline':
        pitch = 0.3; roll = 0.03; gx = 0; gy = 0.6; glow = 0.12 + 0.05 * bell((t % 7) / 2.5); cold = 1; amp = 0; orbitSpeed = 0; barrelSpeed = 0.02; loupe = 0; break;
    }

    // Leer lo que escribe el usuario: mira hacia abajo y barre renglones.
    const typing = t < this.typingUntil && s !== 'offline';
    if (typing) { gy = 0.85; gx = -0.5 + ((t * 0.9) % 1) * 1.1; pitch = Math.max(pitch, 0.12); mixFace(f, EXPR.foco, 0.4); f.uL = Math.max(f.uL, 0.42); f.uR = Math.max(f.uR, 0.42); }

    // Aburrimiento tras ~40 s sin interacción.
    if (s === 'idle' && this.idleFor > 40 && !this.gesture && !R) { this.play('bored'); this.idleFor = 0; }
    if (s === 'idle' && !this.gesture && this.microGestures && !R && !typing && t > this.nextGesture) this.play(IDLE[this.gi++ % IDLE.length]!);

    let spinTarget = 0;
    if (this.gesture) {
      this.gt += dt;
      const g = this.gesture, u = this.gt / DUR[g];
      if (u >= 1) { this.gesture = null; this.nextGesture = t + 5 + this.rand() * 6; }
      else switch (g) {
        case 'wind': roll += 0.07 * plateau(u); yaw -= 0.06 * plateau(u); gx = -0.85 * plateau(u, 0.15); f.uL += 0.12 * plateau(u); f.uR += 0.12 * plateau(u);
          if (u > 0.72) mixFace(f, EXPR.satisfaccion, 0.5 * bell((u - 0.72) / 0.28));
          if (u < 0.7) this.crownV = Math.max(this.crownV, 9); amp = Math.max(amp, 4.2 + 1.2 * bell(u)); break;
        case 'loupe': loupe = plateau(u, 0.18); if (u > 0.3 && u < 0.75) { gx = cx; gy = cy; mixFace(f, EXPR.curiosidad, 0.6); } break;
        case 'peek': mixFace(f, EXPR.curiosidad, bell(u)); f.pupil += 0.3 * bell(u); break;
        case 'glance': gx = (this.gi % 2 ? 1 : -1) * 0.85 * plateau(u); gy = -0.15 * plateau(u); f.lL += 0.02 * bell(u); break;
        case 'smirk': mixFace(f, EXPR.ironia, plateau(u, 0.22)); roll += 0.03 * plateau(u, 0.3); gx = cx * 0.5 + 0.2 * plateau(u); break;
        case 'chime': mixFace(f, EXPR.satisfaccion, 0.7 * plateau(u)); pitch -= 0.03 * bell(u); break;
        case 'mouthpoke': mixFace(f, EXPR.sorpresa, 0.5 * bell(u * 2)); if (u > 0.4) mixFace(f, EXPR.ironia, 0.6 * bell((u - 0.4) / 0.6)); lean -= 0.2 * bell(u * 2); break;
        case 'tilt': roll -= 0.1 * plateau(u, 0.3); gy -= 0.4 * plateau(u, 0.3); mixFace(f, EXPR.curiosidad, 0.6 * plateau(u)); break;
        case 'attend': mixFace(f, EXPR.atencion, bell(u)); lean += 0.35 * bell(u); pitch += 0.06 * bell(u * 1.5); break;
        case 'spin': gy = -0.95 * plateau(u, 0.15); gx *= 0.3; mixFace(f, EXPR.sorpresa, 0.35 * bell(u)); f.jaw *= 0.4; pitch -= 0.06 * bell(u); spinTarget = 1; break;
        case 'heart': gy = 0.9 * plateau(u, 0.2); gx = -0.3 * plateau(u); pitch += 0.12 * plateau(u); mixFace(f, EXPR.satisfaccion, plateau(u)); barrelSpeed += 6 * bell(u); glow += 0.15 * bell(u); break;
        case 'halo': gx = 0.9 * Math.sin(u * Math.PI * 2); gy = -0.6 * bell(u); mixFace(f, EXPR.curiosidad, bell(u)); break;
        case 'greet': { // breve inclinación, cejas arriba, sonrisa
          const b = bell(u / 0.6); pitch += 0.16 * b; lean += 0.15 * b; mixFace(f, EXPR.atencion, bell(u * 1.6)); mixFace(f, EXPR.satisfaccion, 0.8 * plateau(u, 0.3)); gx = cx; gy = cy; break;
        }
        case 'sigh': rise -= 0.02 * bell(u); shrug -= 0.2 * bell(u); mixFace(f, EXPR.hastio, 0.6 * bell(u)); break;
        case 'bored': { // mira su propio anillo, se adormece, el volante se frena… y se da cuerda
          if (u < 0.35) { gy = -0.8 * plateau(u / 0.35, 0.3); gx = 0.7 * Math.sin(u * 9); mixFace(f, EXPR.hastio, plateau(u / 0.35, 0.3)); }
          else if (u < 0.65) { const k = (u - 0.35) / 0.3; mixFace(f, EXPR.hastio, 1); f.uL += 0.25 * bell(k); f.uR += 0.25 * bell(k); pitch += 0.12 * bell(k); amp = 1.2; freq = 1.2; }
          else { const k = (u - 0.65) / 0.35; this.crownV = Math.max(this.crownV, 12 * (1 - k)); amp = 5; roll += 0.06 * plateau(k); gx = -0.8 * plateau(k); if (k > 0.6) mixFace(f, EXPR.satisfaccion, bell((k - 0.6) / 0.4)); }
          break;
        }
        case 'tut': { // cinco clics: le mira con la ceja en alto y media sonrisa, y niega despacio
          gx = cx; gy = cy; mixFace(f, EXPR.ironia, plateau(u, 0.12)); yaw += 0.07 * Math.sin(u * Math.PI * 4) * plateau(u, 0.2); pitch += 0.03 * plateau(u);
          halo = HALO.tut; haloVal = u; break;
        }
      }
    }

    // Hover: se da por aludido (solo si nada más reclama la mirada).
    if (!this.gesture && !typing && s !== 'offline' && s !== 'interrupted' && s !== 'thinking') {
      if (this.hover === 'movement') { gy = Math.min(gy, -0.7); f.lL += 0.03; f.lR += 0.03; }
      else if (this.hover === 'chest') { gy = Math.max(gy, 0.8); pitch += 0.04; f.smR += 0.12; }
      else if (this.hover === 'eye') { f.pupil += 0.22; f.uL -= 0.08; f.uR -= 0.08; }
      else if (this.hover === 'mouth') { f.smL += 0.1; f.smR += 0.18; }
      else if (this.hover === 'crown') gx = -0.9;
      else if (this.hover === 'halo') mixFace(f, EXPR.curiosidad, 0.3);
    }
    if (this.exprOverride) { Object.assign(f, EXPR[this.exprOverride]); gx = cx * 0.3; gy = cy * 0.3; if (this.exprOverride === 'curiosidad') roll += 0.08; if (this.exprOverride === 'ironia') roll += 0.04; }

    // Pensar: la aguja-ceja derecha da una vuelta completa, con anticipación.
    if (s === 'thinking') { if (st < 0.3) f.bAR -= 0.3 * bell(st / 0.6); else if (!this.spun) { this.spun = true; this.spinAcc -= Math.PI * 2; } } else this.spun = false;
    if (spinTarget && !this.gestureSpun) { this.gestureSpun = true; this.spinAcc -= Math.PI * 2; }
    if (!spinTarget) this.gestureSpun = false;
    const spin = R ? 0 : this.spinCh.step(this.spinAcc, dt);

    if (R) { yaw = this.headX * 0.1; roll *= 0.3; lean *= 0.3; pitch *= 0.5; boostTarget = 0; this.shakeV = 0; this.shake = 0; }

    // Parpadeo (a veces doble), salvo dormido.
    if (s !== 'offline' && t > this.blinkAt) { this.blink = 0.15; this.blinkAt = t + (this.rand() < 0.2 ? 0.32 : 2.4 + this.rand() * 3.8); }
    this.blink = Math.max(0, this.blink - dt);
    const bk = this.blink > 0 && !this.exprOverride ? bell(1 - this.blink / 0.15) : 0; // sin parpadeo al forzar una expresión (hojas de referencia)

    // Mecanismo.
    const A = c.amp.step(amp, dt), fq = c.freq.step(freq, dt);
    if (!hack && A > 0.06) { const ph = Math.floor(this.phase / Math.PI); this.phase += Math.PI * 2 * fq * dt; if (Math.floor(this.phase / Math.PI) !== ph) { this.beats++; this.lastBeat = t; } }
    let balance = A * Math.sin(this.phase);
    if (s === 'error') balance += 0.12 * Math.sin(st * 70) * Math.exp(-st * 3.5);
    const pal = this.pal.step(this.beats % 2 ? 0.16 : -0.16, dt);
    this.boostV += ((hack ? 0 : boostTarget) - this.boostV) * Math.min(1, dt * (hack ? 40 : 2.5));
    this.boost += this.boostV * dt;
    const tick = this.lastBeat < 0 ? 0 : easeOut((t - this.lastBeat) / 0.055);
    const train = (this.beats - 1 + tick) * STEP + this.boost;
    if (!hack) { this.barrel += barrelSpeed * dt; this.orbit += orbitSpeed * dt; }
    this.crownV -= this.crownV * Math.min(1, dt * 2.2); this.crown += this.crownV * dt;
    this.shakeV += (-260 * this.shake - 9 * this.shakeV) * dt; this.shake += this.shakeV * dt;

    // Muelles de la cara.
    const out = {} as Face;
    for (const k of KEYS) out[k] = this.fc[k].step(f[k], dt);
    out.uL = clamp(out.uL + bk * (1 - out.uL), 0, 1); out.uR = clamp(out.uR + bk * (1 - out.uR), 0, 1);
    out.jaw = clamp(out.jaw, 0, 1.1);

    const P = {
      yaw: c.yaw.step(yaw, dt), pitch: c.pitch.step(pitch, dt), roll: c.roll.step(roll, dt), lean: c.lean.step(lean, dt), rise: c.rise.step(rise, dt), shrug: c.shrug.step(shrug, dt),
      gx: c.gx.step(clamp(gx, -1, 1), dt), gy: c.gy.step(clamp(gy, -1, 1), dt),
      loupe: clamp(c.loupe.step(loupe, dt), -0.05, 1.08), glow: c.glow.step(glow, dt), cold: clamp(c.cold.step(cold, dt), 0, 1),
      haloSpin: c.haloSpin.step(this.haloSpinAcc, dt),
    };
    this.flash = Math.max(0, this.flash - dt * 1.5);
    const a = ACCENT[s], m = 1 - Math.exp(-dt * 5);
    for (let i = 0; i < 3; i++) this.acc[i] = this.acc[i]! + (a[i]! - this.acc[i]!) * m;
    const chime = t - this.chimeAt, mag = 1 + 0.45 * clamp(P.loupe, 0, 1);
    const kc = P.cold, kg = clamp(P.glow, 0, 1.3);
    return {
      state: s, t, st, yaw: P.yaw + this.shake * 0.08, pitch: P.pitch, roll: P.roll + this.shake * 0.03, lean: P.lean, rise: P.rise, breath, shrug: P.shrug,
      gx: P.gx, gy: P.gy, face: out, pupilL: out.pupil * mag, pupilR: out.pupil, browSpin: spin,
      chime: chime >= 0 && chime < 2.5 ? chime : -1, balance, pallet: pal, train, barrel: this.barrel, orbit: this.orbit, crown: this.crown, beat: tick,
      loupe: P.loupe, glow: Math.max(0.05, P.glow), cold: kc, accent: [this.acc[0], this.acc[1], this.acc[2]],
      key: [(1 - 0.45 * kc) * (0.45 + 0.55 * Math.min(1, kg)), (0.9 - 0.32 * kc) * (0.45 + 0.55 * Math.min(1, kg)), (0.76 - 0.05 * kc) * (0.45 + 0.55 * Math.min(1, kg))],
      halo, haloVal, haloSpin: P.haloSpin, level: s === 'listening' || s === 'speaking' ? this.env : 0, hover: this.hover, flash: this.flash,
      moving: s === 'speaking' || this.gesture === 'mouthpoke' || chime >= 0 && chime < 2.5 || out.jaw > 0.004,
    };
  }
}
