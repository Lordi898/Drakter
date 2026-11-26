// Cerebro de Holo-busto: (estado, voz, mirada, eventos) → pose. Independiente del render.
// Capas: expresión base (7 preajustes) → particularidades del estado → gestos → hover → muelles.

export const STATES = ['idle', 'listening', 'thinking', 'speaking', 'executing', 'success', 'error', 'interrupted', 'offline'] as const;
export type AvatarState = (typeof STATES)[number];
export const EXPRESSIONS = ['serenidad', 'atencion', 'curiosidad', 'ironia', 'satisfaccion', 'preocupacion', 'sorpresa'] as const;
export type Expr = (typeof EXPRESSIONS)[number];
export type Zone = 'eye' | 'brow' | 'nose' | 'mouth' | 'ear' | 'core' | 'head';
export type RGB = [number, number, number];
export type Viseme = 'A' | 'E' | 'I' | 'O' | 'U' | 'M';

export interface Pose {
  state: AvatarState; t: number; reduced: boolean;
  yaw: number; pitch: number; roll: number; lean: number; breath: number;
  gx: number; gy: number;
  lidL: number; lidR: number; lowL: number; lowR: number;
  browL: number; browR: number; browTilt: number;
  jaw: number; wide: number; round: number;
  cornerL: number; cornerR: number; lipL: number; lipR: number; // comisuras (−1..1) y labio superior (0..1); L = izquierda del personaje
  frill: number; flick: number; nostril: number;
  drop: number; swing: number;
  glow: number; fire: number; eye: number; throat: number; mouthGlow: number; pupil: number; cold: number; heat: number;
  accent: RGB; fire3: RGB;
  smoke: number; embers: number;
  puff: number; soot: number; sparks: number; sniff: number; ring: number;
  ripple: number; glint: number; halo: number; haloSpin: number; level: number;
}

interface Face { bL: number; bR: number; tilt: number; lidL: number; lidR: number; lowL: number; lowR: number; cL: number; cR: number; lipL: number; lipR: number; frill: number; pupil: number; pitch: number; roll: number; yaw: number; lean: number; jaw: number }
const KEYS = ['bL', 'bR', 'tilt', 'lidL', 'lidR', 'lowL', 'lowR', 'cL', 'cR', 'lipL', 'lipR', 'frill', 'pupil', 'pitch', 'roll', 'yaw', 'lean', 'jaw'] as const;
const NEUTRAL: Face = { bL: 0.05, bR: 0.08, tilt: 0, lidL: 0.92, lidR: 0.92, lowL: 0.16, lowR: 0.16, cL: 0.08, cR: 0.16, lipL: 0, lipR: 0, frill: 0, pupil: 0.35, pitch: 0, roll: 0, yaw: 0, lean: 0, jaw: 0 };
/** Las siete expresiones. La derecha del personaje (R) es el lado del monóculo, el más cercano a la cámara. */
export const EXPR: Record<Expr, Partial<Face>> = {
  serenidad: {},
  atencion: { bL: 0.5, bR: 0.45, lidL: 1.08, lidR: 1.08, lowL: 0, lowR: 0, cL: 0, cR: 0.05, frill: 1, pupil: 0.75, lean: 0.5, roll: 0.06, pitch: -0.03 },
  curiosidad: { bL: 0.95, bR: 0.2, tilt: -0.15, lidL: 1.06, lidR: 0.96, lowL: 0.04, lowR: 0.14, cL: 0.05, cR: 0.22, frill: 0.6, pupil: 0.62, roll: 0.17, yaw: 0.05, lean: 0.25 },
  ironia: { bR: 1.15, bL: -0.35, tilt: 0.05, lidR: 1.0, lidL: 0.8, lowL: 0.5, lowR: 0.08, cR: 1, cL: -0.12, lipR: 0.4, frill: 0.15, pupil: 0.3, pitch: -0.05, roll: -0.1, yaw: -0.04 },
  satisfaccion: { bL: 0.25, bR: 0.28, lidL: 0.64, lidR: 0.64, lowL: 0.5, lowR: 0.5, cL: 0.6, cR: 0.68, frill: 0.45, pitch: 0.1, pupil: 0.4 },
  preocupacion: { bL: 0.6, bR: 0.62, tilt: -0.9, lidL: 1.0, lidR: 1.0, lowL: 0.14, lowR: 0.14, cL: -0.7, cR: -0.65, frill: -0.5, pupil: 0.68, pitch: 0.06, lean: -0.15 },
  sorpresa: { bL: 1.2, bR: 1.2, tilt: -0.1, lidL: 1.26, lidR: 1.26, lowL: 0, lowR: 0, cL: 0, cR: 0, jaw: 0.3, frill: 1.25, pupil: 0.95, lean: -0.35, pitch: -0.07 },
};

// Luz principal del holograma y del núcleo por estado: azul siempre, con acentos (error ámbar, éxito blanco cálido, sin conexión apagado).
const ACCENT: Record<AvatarState, RGB> = {
  idle: [92, 196, 255], listening: [120, 222, 255], thinking: [130, 160, 255], speaking: [100, 208, 255],
  executing: [80, 186, 255], success: [215, 238, 255], error: [255, 168, 80], interrupted: [190, 226, 255], offline: [70, 96, 130],
};
const FIRE: Record<AvatarState, RGB> = {
  idle: [200, 238, 255], listening: [210, 245, 255], thinking: [190, 190, 255], speaking: [215, 245, 255],
  executing: [170, 225, 255], success: [255, 244, 222], error: [255, 120, 60], interrupted: [225, 240, 255], offline: [90, 110, 140],
};

class Ch {
  v = 0;
  constructor(public x = 0, private k = 90, private d = 17) {}
  step(target: number, dt: number): number { this.v += ((target - this.x) * this.k - this.v * this.d) * dt; this.x += this.v * dt; return this.x; }
}

type Gesture = 'glance' | 'snort' | 'monocle' | 'smirk' | 'frill' | 'read' | 'slowblink' | 'brow' | 'yawn' | 'blink2' | 'tilt' | 'rumble' | 'attend' | 'indignant' | 'ring' | 'greet' | 'eyeroll' | 'curious';
const IDLE: Gesture[] = ['glance', 'smirk', 'snort', 'monocle', 'curious', 'read', 'frill', 'slowblink', 'glance', 'brow', 'snort', 'yawn', 'smirk'];
const DUR: Record<Gesture, number> = { glance: 1.9, snort: 1.1, monocle: 2.2, smirk: 2.6, frill: 0.9, read: 3.6, slowblink: 1.6, brow: 1.8, yawn: 3.0, blink2: 0.7, tilt: 1.8, rumble: 1.8, attend: 1.1, indignant: 1.6, ring: 5.2, greet: 1.9, eyeroll: 3.0, curious: 2.4 };
// Visema: [apertura, ancho, redondez, labio superior (dientes)]. M/B/P = labios apretados.
const VIS: Record<Viseme, [number, number, number, number]> = { A: [1, 0.45, 0, 0.05], E: [0.45, 0.9, 0, 0.5], I: [0.22, 1, 0, 0.7], O: [0.7, 0.05, 0.85, 0], U: [0.3, 0, 1, 0], M: [0, 0.25, 0.3, 0] };
const VOWELS: Viseme[] = ['E', 'A', 'O', 'E', 'A', 'I', 'O', 'E', 'A', 'U', 'E', 'O', 'A', 'I', 'E', 'A'];

function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => { a = (a + 0x6d2b79f5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const clamp = (v: number, a: number, b: number): number => Math.min(b, Math.max(a, v));
const bell = (u: number): number => Math.sin(Math.PI * clamp(u, 0, 1));
const plateau = (u: number, e = 0.2): number => clamp(Math.min(u / e, (1 - u) / e), 0, 1);
const once = (u: number, prev: number, at: number): boolean => u >= at && prev < at;

export class Brain {
  state: AvatarState = 'idle';
  voice = 0;
  cursor = { x: 0, y: 0, active: false };
  hover: Zone | null = null;
  microGestures = true;
  reduced = false;
  viseme: Viseme | null = null;
  /** Expresión impuesta (hoja de expresiones / depuración). */
  expr: Expr | null = null;
  private rand = rng(0xa5c0);
  private t = 0; private st = 0;
  private c: Record<string, Ch> = {
    yaw: new Ch(0, 38, 11), pitch: new Ch(0, 38, 11), roll: new Ch(0, 40, 11), lean: new Ch(0, 55, 13),
    gx: new Ch(0, 260, 28), gy: new Ch(0, 260, 28), lidL: new Ch(1, 320, 32), lidR: new Ch(1, 320, 32),
    lowL: new Ch(0, 140, 19), lowR: new Ch(0, 140, 19), browL: new Ch(0, 170, 17), browR: new Ch(0, 170, 17), tilt: new Ch(0, 130, 18),
    jaw: new Ch(0, 560, 36), wide: new Ch(0.3, 300, 30), round: new Ch(0, 300, 30), cL: new Ch(0, 120, 15), cR: new Ch(0, 120, 15), lipL: new Ch(0, 220, 24), lipR: new Ch(0, 220, 24),
    frill: new Ch(0, 140, 9), flick: new Ch(0, 380, 9), nostril: new Ch(0, 200, 16),
    drop: new Ch(0, 40, 9), glow: new Ch(1, 30, 11), fire: new Ch(0.5, 25, 10), eye: new Ch(1, 40, 12), throat: new Ch(0, 160, 22),
    mouthGlow: new Ch(0, 120, 20), pupil: new Ch(0.35, 60, 14), cold: new Ch(0, 12, 7), heat: new Ch(0, 18, 9), halo: new Ch(0.5, 20, 9),
  };
  private acc: RGB = [...ACCENT.idle]; private fc: RGB = [...FIRE.idle];
  private env = 0; private slow = 0; private gate = false; private vi = 0; private vis: Viseme = 'M'; private quiet = 0; private quip = -9;
  private blinkAt = 2; private blink = 0;
  private gesture: Gesture | null = null; private gt = 0; private nextGesture = 4; private gi = 0;
  private sacX = 0; private sacY = 0; private sacAt = 1;
  private hx = 0; private hy = 0; // objetivo de la cabeza: sigue a la mirada con retraso
  private swing = 0; private swingV = 0; private spin = 0; private glint = 0;
  private puff = 0; private soot = 0; private sparks = 0; private sniff = 0; private ring = 0; private ripple = -1; private hoverT = 0;
  private lastTouch = 0; private nextBored = 40; private clicks: number[] = []; private typingUntil = -9; private away = false;

  setState(s: AvatarState): void {
    if (s === this.state) return;
    const prev = this.state;
    this.state = s; this.st = 0; this.gesture = null; this.nextGesture = this.t + 4; this.touch();
    if (s === 'error') { this.swingV = 3.5; this.soot++; }
    if (s === 'success') { this.sparks++; this.ripple = 0; }
    if (s === 'interrupted') this.glint = 0.5;
    if (prev === 'offline') this.puff++;
  }
  /** Depuración: fuerza el aburrimiento ya. */
  boredNow(): void { this.nextBored = this.t; this.gesture = null; }
  /** Cualquier interacción reinicia el reloj del aburrimiento. */
  touch(): void { this.lastTouch = this.t; this.nextBored = this.t + 40; }
  notify(e: 'userTyping' | 'focus' | 'blur'): void {
    if (e === 'userTyping') { this.typingUntil = this.t + 1.6; this.touch(); }
    else if (e === 'blur') this.away = true;
    else { if (this.away && this.state === 'idle') this.play('greet'); this.away = false; this.touch(); }
  }

  click(z: Zone): void {
    this.touch();
    this.glint = Math.max(this.glint, 0.6);
    if (this.state === 'offline') { this.c.eye!.v += 4; this.c.glow!.v += 2; this.puff++; return; }
    this.clicks = this.clicks.filter((c) => this.t - c < 7); this.clicks.push(this.t);
    if (this.clicks.length >= 5) { this.clicks = []; this.play('eyeroll'); return; } // memoria: «¿ha terminado ya?»
    const g: Record<Zone, Gesture> = { eye: 'blink2', brow: 'brow', nose: 'indignant', mouth: 'smirk', ear: 'tilt', core: 'rumble', head: 'attend' };
    this.play(g[z]);
  }

  private play(g: Gesture): void { this.gesture = g; this.gt = 0; }

  update(rawDt: number): Pose {
    const dt = Math.min(rawDt, 0.05);
    this.t += dt; this.st += dt;
    const { t, st, state: s, c } = this;
    const R = this.reduced;

    // Voz: envolvente (ataque rápido, caída lenta) y visemas por sílaba.
    const v = clamp(this.voice, 0, 1);
    this.env += (v - this.env) * (1 - Math.exp(-dt * (v > this.env ? 38 : 12)));
    this.slow += (this.env - this.slow) * (1 - Math.exp(-dt * 4));
    const peak = clamp((this.env - this.slow) * 2.4, 0, 1);
    if (!this.gate && this.env > 0.18) { this.gate = true; this.vis = VOWELS[this.vi++ % VOWELS.length]!; if (this.rand() < 0.12) this.vis = VOWELS[(this.vi * 7) % VOWELS.length]!; }
    else if (this.gate && this.env < 0.09) { this.gate = false; this.vis = 'M'; }
    const vis = VIS[this.viseme ?? this.vis];
    if (s === 'speaking') { this.quiet = this.env < 0.05 ? this.quiet + dt : 0; if (this.quiet > 0.45 && this.quiet - dt <= 0.45 && this.rand() < 0.35) this.quip = t; }

    if (t > this.sacAt) { this.sacX = (this.rand() - 0.5) * 0.3; this.sacY = (this.rand() - 0.5) * 0.18; this.sacAt = t + 0.6 + this.rand() * 2.2; }
    const cx = this.cursor.active ? this.cursor.x : 0, cy = this.cursor.active ? this.cursor.y : 0;
    // Ojos primero; la cabeza llega después, con peso.
    this.hx += (cx - this.hx) * (1 - Math.exp(-dt * 2.2)); this.hy += (cy - this.hy) * (1 - Math.exp(-dt * 2.2));

    // 1) Expresión base del estado.
    const F: Face = { ...NEUTRAL };
    const apply = (e: Expr, k = 1): void => { const p = EXPR[e]; for (const key of KEYS) { const val = p[key]; if (val !== undefined) F[key] += (val - F[key]) * k; } };
    let gx = cx * 0.85 + this.sacX, gy = cy * 0.85 + this.sacY;
    let yaw = this.hx * 0.3, pitch = this.hy * 0.15, roll = -this.hx * 0.04;
    let jaw = 0, wide = 0.3, round = 0, flick = 0, nostril = 0.1 + 0.1 * Math.sin(t * 1.35);
    let drop = 0, glow = 1, fire = 0.45, eye = 1, throat = 0.08, mouthGlow = 0, cold = 0, heat = 0, halo = 0.5;
    let smoke = 0.12, embers = 0.25, spinSpeed = 0.03;
    const breath = 0.5 + 0.5 * Math.sin(t * 1.25);
    yaw += Math.sin(t * 0.29) * 0.02; roll += Math.sin(t * 0.21 + 1) * 0.012; pitch += Math.sin(t * 1.25 - 0.6) * 0.012;

    switch (s) {
      case 'idle': apply('serenidad'); break;
      case 'listening': apply('atencion'); F.frill += this.env * 0.25; F.pitch += peak * 0.03; glow = 1.05; fire = 0.55 + this.env * 0.4; smoke = 0.03; halo = 0.6 + this.env * 0.5; spinSpeed = 0.05; break;
      case 'thinking':
        apply('curiosidad', 0.6); F.bL = 1.0; F.bR = -0.2; F.lowR = 0.42; F.lidR = 0.8; F.cR = 0.25; F.cL = -0.1; F.pupil = 0.2;
        gx = 0.6 + Math.sin(t * 0.6) * 0.2; gy = -0.7 + Math.sin(t * 1.1) * 0.1; yaw = 0.18 + this.hx * 0.08; F.pitch = -0.1; F.roll = -0.08;
        heat = 1; fire = 0.75; glow = 1.08; smoke = 0.55; embers = 0.15; halo = 0.85; spinSpeed = 0.35; nostril = 0.2;
        break;
      case 'speaking': {
        apply('serenidad');
        const acc = clamp((peak - 0.3) * 1.6, 0, 1);
        jaw = vis[0] > 0 ? this.env * (0.12 + 0.88 * vis[0]) : 0; wide = 0.15 + vis[1] * 0.8; round = vis[2];
        F.lipL += vis[3] * this.env; F.lipR += vis[3] * this.env * 1.1;
        F.pitch += acc * 0.07 - jaw * 0.04; F.bL += acc * 0.5; F.bR += acc * 0.6; F.frill = 0.25 + acc * 0.4;
        const q = bell((t - this.quip) / 1.3); if (q > 0) { apply('ironia', q * 0.7); } // remate irónico en las pausas
        yaw += Math.sin(t * 0.8) * 0.04; throat = 0.25 + this.env * 0.9; mouthGlow = 0.3 + this.env * 0.9;
        fire = 0.55 + this.env * 0.45; glow = 1 + this.env * 0.15; smoke = 0.15 + peak * 0.6; embers = 0.3 + peak * 1.4; halo = 0.6 + this.env * 0.35;
        nostril = 0.15 + peak * 0.6; spinSpeed = 0.06;
        break;
      }
      case 'executing': {
        const look = Math.sin(t * 1.2) > 0.75;
        F.pitch = 0.14; yaw = -0.12; gx = look ? cx * 0.8 : -0.5; gy = look ? cy : 0.65; F.lidL = F.lidR = 0.66; F.lowL = F.lowR = 0.38; F.tilt = 0.45; F.bL = F.bR = -0.35; F.cL = F.cR = -0.05;
        const pump = 0.5 + 0.5 * Math.sin(t * 5.2);
        throat = 0.25 + pump * 0.5; fire = 0.7 + pump * 0.3; glow = 1.15; embers = 1.2; smoke = 0.25; spinSpeed = 0.9; halo = 0.9; F.pupil = 0.18; nostril = 0.25 + pump * 0.3; F.frill = -0.2;
        break;
      }
      case 'success': {
        const b = bell((st - 0.12) / 1.4);
        apply('satisfaccion', clamp(st / 0.4, 0, 1));
        F.pitch = st < 0.12 ? -0.06 : b * 0.26; F.lean = b * 0.3; if (st < 1.4) F.lidL = F.lidR = 0.28 + (1 - b) * 0.4;
        glow = 1.25; fire = 1; embers = 0.6; halo = 1.1; spinSpeed = 0.2;
        break;
      }
      case 'error': {
        const k = Math.exp(-st * 2.4);
        apply(st < 0.6 ? 'sorpresa' : 'preocupacion'); F.jaw *= 0.5;
        if (st >= 0.6) { F.bR = -0.3; F.bL = 0.95; F.tilt = -0.2; } // «¿perdone?»
        drop = 1; yaw += R ? 0 : Math.sin(st * 12) * 0.08 * k; F.lean -= 0.1; F.roll = 0.06;
        glow = 0.9 - (R ? 0 : 0.25 * (bell(st / 0.2) + bell((st - 0.38) / 0.2))); fire = 0.5; smoke = 0.1; embers = 0.05; halo = 0.35;
        break;
      }
      case 'interrupted': {
        const k = Math.exp(-st * 3);
        apply('sorpresa', k); apply('atencion', 1 - k); F.jaw = 0; F.frill = -0.7 * k + 0.5 * (1 - k); F.lean = -0.85 * k;
        fire = 0.15; glow = 0.75; smoke = 0; embers = 0; halo = 0.2; spinSpeed = 0; throat = 0;
        break;
      }
      case 'offline':
        Object.assign(F, { pitch: 0.3, yaw: 0, roll: 0.03, lidL: 0, lidR: 0, lowL: 0.3, lowR: 0.3, bL: -0.3, bR: -0.3, tilt: 0, cL: -0.1, cR: -0.1, frill: -0.6, pupil: 0.2 });
        gx = 0; gy = 0.6; yaw = 0;
        glow = 0.25; fire = 0.08 + 0.06 * bell((t % 6.5) / 2.5); eye = 0; cold = 1; smoke = 0.05; embers = 0.04; halo = 0.1; spinSpeed = 0; throat = 0.02;
        nostril = 0.15 * bell((t % 6.5) / 2.5);
        break;
    }

    // 2) Contexto: el usuario escribe → baja la vista y lee.
    const typing = this.typingUntil > t && (s === 'idle' || s === 'listening');
    if (typing) { gx = -0.15 + 0.35 * Math.sin(t * 5.5); gy = 0.75; F.pitch += 0.12; F.lidL -= 0.15; F.lidR -= 0.15; F.bL += 0.15; }
    if (this.away && s === 'idle') { F.lidL -= 0.2; F.lidR -= 0.2; gx = 0.5; gy = 0.2; }

    // 3) Hover.
    this.hoverT = this.hover ? this.hoverT + dt : 0;
    if (this.hover && s !== 'offline' && s !== 'interrupted') {
      const h = clamp(this.hoverT * 2, 0, 1);
      if (this.hover === 'nose') { nostril += 0.5 * h * (0.6 + 0.4 * Math.sin(t * 14)); F.pitch += 0.03 * h; F.bR += 0.2 * h; if (this.hoverT > 0.25 && this.hoverT - dt <= 0.25) this.sniff++; }
      else if (this.hover === 'eye' || this.hover === 'brow') { F.pupil += 0.35 * h; F.bL += 0.2 * h; F.bR += 0.3 * h; }
      else if (this.hover === 'ear') { F.roll += 0.08 * h; F.bL += 0.25 * h; F.cR += 0.15 * h; }
      else if (this.hover === 'mouth') { F.cR += 0.3 * h; F.bR += 0.2 * h; }
      else if (this.hover === 'core') { glow += 0.1 * h; gy = Math.max(gy, 0.5 * h); F.cR += 0.2 * h; }
    }

    // 4) Gestos (micro-gestos en reposo, aburrimiento, reacciones).
    if (s === 'idle' && !this.gesture && !typing && !this.away) {
      if (t > this.nextBored) { this.play('ring'); this.nextBored = t + 22; }
      else if (this.microGestures && t > this.nextGesture) this.play(IDLE[this.gi++ % IDLE.length]!);
    }
    let blinkNow = false;
    if (this.gesture) {
      const prev = this.gt / DUR[this.gesture];
      this.gt += dt;
      const g = this.gesture, u = this.gt / DUR[g];
      if (u >= 1) { this.gesture = null; this.nextGesture = t + 4 + this.rand() * 5; }
      else switch (g) {
        case 'glance': gx = (this.gi % 2 ? 1 : -1) * 0.75 * plateau(u); gy = -0.15 * plateau(u); F.bL += 0.25 * bell(u); yaw += (this.gi % 2 ? 1 : -1) * 0.06 * plateau(u); break;
        case 'snort': F.cR += 0.4 * bell(u); F.bR += 0.35 * bell(u); nostril += 0.9 * (bell(u / 0.25) + bell((u - 0.3) / 0.25)); F.pitch -= 0.04 * bell(u / 0.3);
          if (once(u, prev, 0.1) || once(u, prev, 0.4)) this.puff++; break;
        case 'monocle': F.lowR += 0.65 * bell(u); F.lidR -= 0.28 * bell(u); F.cR += 0.55 * bell(u); F.lipR += 0.3 * bell(u); F.roll -= 0.05 * bell(u); F.bR -= 0.45 * bell(u); F.bL += 0.3 * bell(u);
          if (once(u, prev, 0.55)) this.glint = 1; break;
        case 'smirk': apply('ironia', plateau(u, 0.22)); gx += 0.1 * plateau(u); if (once(u, prev, 0.5)) this.puff++; break; // gesto firma
        case 'curious': apply('curiosidad', plateau(u, 0.25)); gx = 0.3; gy = -0.1; break;
        case 'frill': flick = Math.sin(u * Math.PI * 5) * (1 - u); F.frill += 0.5 * bell(u); break;
        case 'read': gx = -0.45 + 0.25 * Math.sin(u * 18) * plateau(u, 0.1) * 0.5; gy = 0.55 * plateau(u, 0.15); F.pitch += 0.08 * plateau(u, 0.2); F.lidL -= 0.15; F.lidR -= 0.15; F.bL += 0.2 * bell(u); break;
        case 'slowblink': F.lidL = F.lidR = 0.9 - 0.85 * bell(u); F.cL += 0.3 * bell(u); F.cR += 0.35 * bell(u); break;
        case 'brow': F.bR += 1.0 * bell(u); F.tilt -= 0.2 * bell(u); F.cR += 0.3 * bell(u); break;
        case 'yawn': { const a = bell((u - 0.1) / 0.75); jaw = Math.max(jaw, 0.9 * a); round = 0.35 * a; F.lipL += 0.5 * a; F.lipR += 0.5 * a; F.lidL = F.lidR = 0.9 - 0.75 * a; F.pitch -= 0.14 * a; F.frill += 0.6 * a; F.bL += 0.4 * a; F.bR += 0.4 * a;
          mouthGlow = Math.max(mouthGlow, 0.9 * a); throat += 0.4 * a; if (once(u, prev, 0.8)) this.puff++; break; }
        case 'blink2': blinkNow = u < 0.05 || once(u, prev, 0.45); F.lean -= 0.2 * bell(u); F.bL += 0.3 * bell(u); F.bR += 0.3 * bell(u); break;
        case 'tilt': F.roll += 0.18 * bell(u); F.frill += 0.8 * bell(u); F.bL += 0.5 * bell(u); F.cL += 0.2 * bell(u); break;
        case 'rumble': throat += 0.9 * bell(u); fire += 0.4 * bell(u); apply('satisfaccion', bell(u) * 0.7); F.pitch += 0.04 * Math.sin(u * 30) * bell(u) * (R ? 0 : 1); if (once(u, prev, 0.5)) this.puff++; this.glint = Math.max(this.glint, 0.5 * bell(u)); break;
        case 'attend': apply('atencion', bell(u)); F.lidL = F.lidR = 1.15; F.pitch += 0.08 * bell(u * 1.6); break;
        case 'indignant': apply('sorpresa', bell(u) * 0.5); F.jaw = 0; F.lean -= 0.4 * bell(u); nostril += 0.9 * bell(u / 0.5); F.cL -= 0.4 * bell(u); F.cR -= 0.3 * bell(u); if (once(u, prev, 0.2)) this.puff++; break;
        case 'greet': apply('atencion', bell(u)); F.cL += 0.4 * bell(u); F.cR += 0.5 * bell(u); F.pitch += 0.12 * bell((u - 0.3) / 0.5); if (once(u, prev, 0.55)) this.puff++; break;
        case 'eyeroll': { // al quinto clic: los ojos dan la vuelta hacia el techo y suspira humo
          const a = clamp((u - 0.05) / 0.5, 0, 1), ang = a * Math.PI * 1.15 + Math.PI;
          gx = Math.cos(ang) * 0.9 * plateau(u, 0.1); gy = -Math.abs(Math.sin(ang)) * 0.9 * plateau(u, 0.1) - 0.2 * plateau(u, 0.1);
          F.lidL = F.lidR = 0.72; F.bL += 0.6 * plateau(u); F.bR += 0.2; F.tilt = -0.25 * plateau(u); F.cR += 0.5 * plateau(u, 0.3); F.cL -= 0.2;
          if (once(u, prev, 0.62)) { this.puff++; this.puff++; } F.pitch += 0.06 * bell((u - 0.55) / 0.4);
          break;
        }
        case 'ring': { // aburrido: sopla anillos de humo y los sigue con la mirada
          round = 0.9 * (bell((u - 0.05) / 0.25) + bell((u - 0.4) / 0.25)); jaw = 0.12 * round; F.lidL = F.lidR = 0.62; F.bL += 0.2; F.cR += 0.2;
          if (once(u, prev, 0.17) || once(u, prev, 0.52)) this.ring++;
          if (u > 0.2) { gx = 0.35; gy = -0.35 - 0.4 * clamp((u - 0.2) * 1.5, 0, 1); F.pitch -= 0.08 * plateau(u); }
          break;
        }
      }
    }
    if (this.expr) { Object.assign(F, NEUTRAL); apply(this.expr); if (this.expr === 'sorpresa') jaw = F.jaw; }

    if (R) { yaw = this.hx * 0.12 + (s === 'thinking' ? 0.1 : 0); F.roll *= 0.3; roll *= 0.3; F.lean *= 0.3; flick = 0; embers *= 0.3; smoke *= 0.4; spinSpeed *= 0.2; }
    if (s !== 'offline' && !this.expr && (t > this.blinkAt || blinkNow)) { this.blink = 0.15; this.blinkAt = t + (this.rand() < 0.2 ? 0.32 : 2.4 + this.rand() * 3.8); }
    this.blink = Math.max(0, this.blink - dt);
    const bk = this.blink > 0 ? 1 - bell(this.blink / 0.15) : 1;
    // Las comisuras arriba levantan la mejilla y entornan el ojo de ese lado (sonrisa sincera).
    F.lowL += Math.max(0, F.cL) * 0.25; F.lowR += Math.max(0, F.cR) * 0.25;

    const yawPrev = c.yaw!.x;
    const S = (k: string, v: number): number => c[k]!.step(v, dt);
    const P = {
      yaw: S('yaw', yaw + F.yaw), pitch: S('pitch', pitch + F.pitch), roll: S('roll', roll + F.roll), lean: S('lean', F.lean),
      gx: S('gx', clamp(gx, -1, 1)), gy: S('gy', clamp(gy, -1, 1)), lidL: S('lidL', F.lidL), lidR: S('lidR', F.lidR),
      lowL: S('lowL', clamp(F.lowL, 0, 1)), lowR: S('lowR', clamp(F.lowR, 0, 1)), browL: S('browL', clamp(F.bL, -1, 1.3)), browR: S('browR', clamp(F.bR, -1, 1.3)), tilt: S('tilt', F.tilt),
      jaw: clamp(S('jaw', Math.max(jaw, F.jaw)), 0, 1.1), wide: S('wide', wide), round: S('round', round),
      cL: S('cL', clamp(F.cL, -1, 1)), cR: S('cR', clamp(F.cR, -1, 1)), lipL: S('lipL', clamp(F.lipL, 0, 1)), lipR: S('lipR', clamp(F.lipR, 0, 1)),
      frill: S('frill', clamp(F.frill, -1, 1.3)), flick: S('flick', flick), nostril: clamp(S('nostril', clamp(nostril, 0, 1.2)), 0, 1.3),
      drop: clamp(S('drop', drop), 0, 1.05), glow: S('glow', glow), fire: S('fire', fire), eye: S('eye', eye), throat: S('throat', throat),
      mouthGlow: S('mouthGlow', mouthGlow), pupil: S('pupil', clamp(F.pupil, 0.1, 1)), cold: clamp(S('cold', cold), 0, 1), heat: clamp(S('heat', heat), 0, 1), halo: S('halo', halo),
    };
    this.swingV += (-30 * Math.sin(this.swing) - 1.0 * this.swingV - ((P.yaw - yawPrev) / dt) * 5) * dt;
    this.swing += this.swingV * dt;
    if (R) this.swing *= 0.9;
    this.spin += spinSpeed * dt;
    this.glint = Math.max(0, this.glint - dt * 1.5);
    if (this.ripple >= 0) { this.ripple += dt / 1.6; if (this.ripple > 1) this.ripple = -1; }
    const a = ACCENT[s], f = FIRE[s], m = 1 - Math.exp(-dt * 5);
    for (let i = 0; i < 3; i++) { this.acc[i] = this.acc[i]! + (a[i]! - this.acc[i]!) * m; this.fc[i] = this.fc[i]! + (f[i]! - this.fc[i]!) * m; }

    return {
      state: s, t, reduced: R, yaw: P.yaw, pitch: P.pitch, roll: P.roll, lean: P.lean, breath, gx: P.gx, gy: P.gy,
      lidL: Math.max(0, P.lidL * bk), lidR: Math.max(0, P.lidR * bk), lowL: P.lowL, lowR: P.lowR, browL: P.browL, browR: P.browR, browTilt: P.tilt,
      jaw: P.jaw, wide: P.wide, round: P.round, cornerL: P.cL, cornerR: P.cR, lipL: P.lipL, lipR: P.lipR,
      frill: P.frill, flick: P.flick, nostril: P.nostril,
      drop: P.drop, swing: this.swing, glow: Math.max(0.05, P.glow), fire: Math.max(0, P.fire), eye: clamp(P.eye, 0, 1.5), throat: Math.max(0, P.throat),
      mouthGlow: Math.max(0, P.mouthGlow), pupil: P.pupil, cold: P.cold, heat: P.heat,
      accent: [this.acc[0], this.acc[1], this.acc[2]], fire3: [this.fc[0], this.fc[1], this.fc[2]],
      smoke: s === 'interrupted' ? 0 : smoke, embers, puff: this.puff, soot: this.soot, sparks: this.sparks, sniff: this.sniff, ring: this.ring,
      ripple: this.ripple, glint: this.glint, halo: Math.max(0, P.halo), haloSpin: this.spin,
      level: s === 'listening' || s === 'speaking' ? this.env : 0,
    };
  }
}

/** Voz simulada: frases con pausas y sílabas, para probar la boca sin audio real. */
export function simVoice(t: number): number {
  const phrase = Math.sin(t * 0.8) + Math.sin(t * 0.37 + 1) * 0.6 > -0.55 ? 1 : 0;
  const syl = Math.pow(Math.abs(Math.sin(t * 7.2 + Math.sin(t * 2.3) * 2.2)), 1.4);
  const tone = 0.55 + 0.45 * Math.sin(t * 3.1 + Math.sin(t * 1.3) * 3);
  return phrase * syl * tone;
}
