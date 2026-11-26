// Cerebro de animación de «Filamento» (v2): convierte (estado, voz, mirada, clics, eventos) en una pose.
// No sabe nada del render. Muelles amortiguados, PRNG con semilla y voz simulada vienen del prototipo anterior.

export const STATES = ['idle', 'listening', 'thinking', 'speaking', 'executing', 'success', 'error', 'interrupted', 'offline'] as const;
export type AvatarState = (typeof STATES)[number];
export type Zone = 'eyeL' | 'eyeR' | 'nose' | 'mouth' | 'hair' | 'knot' | 'head' | 'body';
export type Vowel = 'a' | 'e' | 'i' | 'o' | 'u' | 'm';
export const EXPRESSIONS = ['serenidad', 'atencion', 'curiosidad', 'ironia', 'satisfaccion', 'preocupacion', 'sorpresa'] as const;
export type Expression = (typeof EXPRESSIONS)[number];
export const HIST = 16;

export interface Pose {
  state: AvatarState; t: number;
  yaw: number; pitch: number; roll: number; // cabeza (rad). +yaw = hacia la derecha de pantalla, +pitch = hacia abajo
  byaw: number; bpitch: number; // giro del busto entero
  breath: number;
  gx: number; gy: number; verge: number; // mirada local -1..1 (+y abajo) y convergencia
  lidL: number; lidR: number; // L = ojo a la izquierda de pantalla. 0 cerrado, 1 abierto, 1.3 muy abierto
  browL: number; browR: number; furrow: number; squint: number; // furrow < 0 = cejas de preocupación (interior arriba)
  jaw: number; round: number; spread: number; smile: number; smirk: number; // smirk < 0 sube la comisura izquierda de pantalla
  cond: number; think: number; loose: number; shed: number; // condensación, ovillo, soltura, hebras errantes
  heat: number; cold: number; glitch: number; sag: number; // temperatura del filamento, ceniza, fallo, caída
  flow: number; inward: number; flashY: number; flashK: number;
  spin: number; tw: number; level: number; hist: Float32Array; histPhase: number;
  ember: number; glow: number; bright: number; attract: number; stray: number;
  inertX: number; inertY: number;
  dustRing: number; dustBurst: number; dustB: number; shutX: number; shutY: number; // dustRing = intensidad de la lanzadera
  ripple: number; rippleZone: Zone | 'mouth' | null; // contador de ondas que debe lanzar el render
  accent: number; // acento de color: > 0 ámbar (error), < 0 blanco cálido (éxito)
  vowel: Vowel;
}

/** Muelle amortiguado. Con poca amortiguación da el rebote (overshoot) de los gestos secos. */
class Ch {
  v = 0;
  constructor(public x = 0, public k = 90, public d = 17) {}
  step(target: number, dt: number): number { this.v += ((target - this.x) * this.k - this.v * this.d) * dt; this.x += this.v * dt; return this.x; }
}
function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => { a = (a + 0x6d2b79f5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const clamp = (v: number, a: number, b: number): number => Math.min(b, Math.max(a, v));
const bell = (u: number): number => Math.sin(Math.PI * clamp(u, 0, 1));
const plateau = (u: number, edge = 0.2): number => clamp(Math.min(u / edge, (1 - u) / edge), 0, 1);

// Visemas aproximados del castellano: apertura, redondeo y estirado por vocal; «m» es el cierre bilabial (M/B/P).
const VIS: Record<Vowel, [number, number, number]> = { a: [1, 0, 0.15], e: [0.62, 0, 0.6], i: [0.4, 0, 0.95], o: [0.72, 0.85, 0], u: [0.45, 1, 0], m: [0, 0.1, 0] };
const pickVowel = (r: number): Vowel => (r < 0.3 ? 'a' : r < 0.58 ? 'e' : r < 0.78 ? 'o' : r < 0.92 ? 'i' : 'u'); // frecuencias del español

/** Las siete expresiones: cejas, párpados, comisuras y un poco de cabeza. */
type Face = { bL?: number; bR?: number; furrow?: number; lid?: number; squint?: number; smile?: number; smirk?: number; roll?: number; pitch?: number; yaw?: number; jaw?: number; round?: number; lean?: number; gx?: number; gy?: number };
const FACE: Record<Expression, Face> = {
  serenidad: { bL: 0.05, bR: 0.05, lid: 0.72, smile: 0.3, squint: 0.12 },
  atencion: { bL: 0.5, bR: 0.42, lid: 1.1, smile: 0.14, roll: 0.07, lean: 0.07 },
  curiosidad: { bL: 0.95, bR: 0.1, lid: 1.06, roll: -0.09, yaw: 0.1, smile: 0.12, round: 0.25, furrow: 0.15, gx: 0.45, gy: -0.3 },
  ironia: { bL: 1.1, bR: -0.2, lid: 0.78, squint: 0.4, smile: 0.32, smirk: -0.6, roll: 0.05 },
  satisfaccion: { bL: 0.25, bR: 0.25, lid: 0.84, squint: 0.45, smile: 0.95, pitch: 0.04 },
  preocupacion: { bL: 0.45, bR: 0.45, furrow: -1, lid: 1.0, smile: -0.65, pitch: 0.05, roll: -0.03 },
  sorpresa: { bL: 1.15, bR: 1.15, lid: 1.3, jaw: 0.32, round: 0.45, smile: 0, lean: -0.06 },
};

type Gesture = 'brow' | 'glance' | 'thread' | 'settle' | 'nod' | 'stache' | 'sigh' | 'wink' | 'nose' | 'ruffle' | 'knot' | 'attend' | 'weary' | 'bored' | 'greet';
const IDLE: Gesture[] = ['brow', 'glance', 'thread', 'nod', 'stache', 'settle', 'glance', 'sigh'];
const DUR: Record<Gesture, number> = { brow: 2.4, glance: 1.7, thread: 3.8, settle: 2.2, nod: 1.5, stache: 1.2, sigh: 3.2, wink: 0.9, nose: 1.8, ruffle: 2.4, knot: 2.0, attend: 1.1, weary: 3.6, bored: 6, greet: 1.9 };
const SAY: Record<Zone | 'weary' | 'bored' | 'greet', string> = {
  eyeL: 'Un guiño, por no contrariarle.', eyeR: 'Un guiño, por no contrariarle.', nose: 'La nariz no es un timbre, señor.', mouth: 'El bigote se mira, no se toca.',
  hair: 'Me ha despeinado usted. Lo recompongo.', knot: 'El nudo aguanta. Gracias por comprobarlo.', head: '¿Sí? Le escucho.', body: 'A su servicio.',
  weary: 'Cinco veces. Tomo nota, señor.', bored: 'Mientras espera usted, devano un poco.', greet: 'Bienvenido de nuevo.',
};

export class Brain {
  state: AvatarState = 'idle';
  voice = 0; // 0..1: TTS al hablar, micrófono al escuchar
  viseme: Vowel | null = null; // si el TTS da visemas reales, se imponen aquí
  cursor = { x: 0, y: 0, active: false };
  drag = { yaw: 0, pitch: 0, active: false }; // arrastre: gira el busto
  hover: Zone | null = null; // parte bajo el cursor
  wind = 0; // 0..1: velocidad del cursor cerca del busto
  weaving = true; // mientras se teje, las hebras nacen como estrellas
  microGestures = true;
  reduced = false;
  expression: Expression | null = null; // expresión impuesta (hoja de expresiones, pruebas)
  lastReaction = ''; // lo que «dice» al reaccionar; el panel lo muestra
  private rand = rng(0xf11a);
  private t = 0; private st = 0; private prev: AvatarState = 'idle';
  private c = {
    yaw: new Ch(0, 55, 11), pitch: new Ch(0, 55, 11.5), roll: new Ch(0, 45, 10), byaw: new Ch(0.16, 22, 8), bpitch: new Ch(0, 40, 9),
    gx: new Ch(0, 420, 36), gy: new Ch(0, 420, 36), verge: new Ch(0, 200, 22), lidL: new Ch(0, 420, 34), lidR: new Ch(0, 420, 34),
    browL: new Ch(0, 150, 15), browR: new Ch(0, 150, 15), furrow: new Ch(0, 100, 16), squint: new Ch(0, 100, 18),
    jaw: new Ch(0, 700, 42), round: new Ch(0, 380, 32), spread: new Ch(0, 380, 32), smile: new Ch(0, 130, 13), smirk: new Ch(0, 130, 14),
    cond: new Ch(0, 16, 6.2), think: new Ch(0, 14, 6.5), loose: new Ch(1, 30, 9), shed: new Ch(0, 10, 6),
    heat: new Ch(0.5, 40, 11), cold: new Ch(0, 8, 5.5), glitch: new Ch(0, 60, 14), sag: new Ch(0, 26, 6),
    flow: new Ch(0.1, 20, 9), inward: new Ch(0, 30, 11), ember: new Ch(0.5, 40, 9), bright: new Ch(1, 30, 11),
    accent: new Ch(0, 24, 9), attract: new Ch(0, 30, 9), stray: new Ch(0, 60, 9), ring: new Ch(0, 12, 6), dustB: new Ch(1, 14, 7), rate: new Ch(1, 60, 15),
  };
  private env = 0; private slow = 0; private lastSyl = 0; private vowel: Vowel = 'm';
  private blinkAt = 2; private blink = 0; private winkL = 0; private winkR = 0;
  private sacAt = 1; private sx = 0; private sy = 0;
  private gesture: Gesture | null = null; private gt = 0; private nextGesture = 5; private gi = 0; private gSide = 1;
  private spin = 0; private tw = 0; private flashY = 0; private flashK = 0; private flashV = 0; private burst = 0; private histAcc = 0;
  private yawPrev = 0; private pitchPrev = 0; private ix = 0; private iy = 0;
  private lastAct = 0; private typingUntil = -1; private away = false; private wakeAt = -9;
  private clickZone: Zone | null = null; private clickN = 0; private clickT = -9;
  private pose: Pose = {
    state: 'idle', t: 0, yaw: 0, pitch: 0, roll: 0, byaw: 0, bpitch: 0, breath: 0, gx: 0, gy: 0, verge: 0, lidL: 1, lidR: 1, browL: 0, browR: 0, furrow: 0, squint: 0,
    jaw: 0, round: 0, spread: 0, smile: 0, smirk: 0, cond: 0, think: 0, loose: 1, shed: 1, heat: 0.5, cold: 0, glitch: 0, sag: 0, flow: 0, inward: 0, flashY: 0, flashK: 0,
    spin: 0, tw: 0, level: 0, hist: new Float32Array(HIST), histPhase: 0, ember: 0.5, glow: 0, bright: 1, attract: 0, stray: 0, inertX: 0, inertY: 0,
    dustRing: 0, dustBurst: 0, dustB: 1, shutX: 0, shutY: -2, ripple: 0, rippleZone: null, accent: 0, vowel: 'm',
  };

  setState(s: AvatarState): void {
    if (s === this.state) return;
    this.prev = this.state; this.state = s; this.st = 0; this.gesture = null; this.nextGesture = this.t + 3.5; this.lastAct = this.t;
    const c = this.c;
    if (s === 'error' && !this.reduced) { c.yaw.v += 1.6; c.bpitch.v -= 0.9; }
    if (s === 'interrupted') { this.pose.ripple++; this.pose.rippleZone = 'mouth'; if (!this.reduced) { c.bpitch.v -= 1.3; c.pitch.v -= 1.1; } }
    if (s === 'success') c.ember.v += 6;
    if (this.prev === 'offline') { this.blinkAt = this.t + 1.4; this.wakeAt = this.t; }
  }
  /** Cualquier señal de que el usuario está ahí: aplaza el aburrimiento. */
  interact(): void { this.lastAct = this.t; }
  /** Eventos de la app: el usuario escribe, la ventana recupera o pierde el foco. */
  notify(e: 'userTyping' | 'focus' | 'blur'): void {
    if (e === 'userTyping') { this.typingUntil = this.t + 1.6; this.lastAct = this.t; }
    else if (e === 'blur') this.away = true;
    else { const was = this.away; this.away = false; this.lastAct = this.t; if (was && this.state === 'idle') { this.play('greet'); this.lastReaction = SAY.greet; } }
  }
  /** Reacción a un clic sobre una parte del personaje. A la quinta vez seguida en el mismo sitio, responde con ironía. */
  click(zone: Zone): void {
    this.pose.ripple++; this.pose.rippleZone = zone; this.lastAct = this.t;
    if (this.state === 'offline') { this.c.cond.v += 1.1; this.c.ember.v += 9; return; } // se insinúa un instante: sigue ahí
    this.clickN = zone === this.clickZone && this.t - this.clickT < 3 ? this.clickN + 1 : 1; this.clickZone = zone; this.clickT = this.t;
    if (this.clickN >= 5) { this.clickN = 0; this.play('weary'); this.lastReaction = SAY.weary; return; }
    if (zone === 'knot') this.c.ember.v += 9;
    const g: Gesture = zone === 'eyeL' || zone === 'eyeR' ? 'wink' : zone === 'nose' ? 'nose' : zone === 'mouth' ? 'stache' : zone === 'hair' ? 'ruffle' : zone === 'knot' ? 'knot' : 'attend';
    this.gSide = zone === 'eyeL' ? -1 : 1; this.play(g); this.lastReaction = SAY[zone];
    if (zone === 'hair' && !this.reduced) { this.ix += 0.5; this.c.loose.v += 14; }
  }
  private play(g: Gesture): void { this.gesture = g; this.gt = 0; }

  update(rawDt: number): Pose {
    const dt = Math.min(rawDt, 0.05), c = this.c, P = this.pose;
    this.t += dt; this.st += dt;
    const { t, st, state: s } = this, R = this.reduced;

    // Envolvente de voz: ataque rápido, caída lenta. Detecta sílabas para elegir el visema siguiente.
    const v = clamp(this.voice, 0, 1);
    this.env += (v - this.env) * (1 - Math.exp(-dt * (v > this.env ? 48 : 14)));
    this.slow += (this.env - this.slow) * (1 - Math.exp(-dt * 5));
    const peak = clamp((this.env - this.slow) * 2.4, 0, 1);
    if (this.env - this.slow > 0.1 && t - this.lastSyl > 0.13) { this.lastSyl = t; this.vowel = pickVowel(this.rand()); }
    if (this.env < 0.06) this.vowel = 'm';
    const vow = this.viseme ?? this.vowel;

    const cx = this.cursor.active ? this.cursor.x : 0, cy = this.cursor.active ? this.cursor.y : 0;
    const breathRate = s === 'offline' ? 0.7 : s === 'executing' ? 1.7 : 1.3;
    let breathAmp = 1;
    // Objetivos base: sereno, de tres cuartos, atento a usted.
    let byaw = 0.16 + cx * 0.14 + Math.sin(t * 0.21) * 0.04, bpitch = cy * 0.03;
    let yaw = cx * 0.26 - 0.05 + Math.sin(t * 0.31) * 0.018, pitch = cy * 0.14, roll = Math.sin(t * 0.23 + 1) * 0.012;
    let look = true, lx = cx, ly = cy, gx = 0, gy = 0, verge = 0;
    let lidL = 0.72, lidR = 0.72, bL = 0.05, bR = 0.05, furrow = 0, squint = 0.2, jaw = 0, round = 0, spread = 0, smile = 0.28, smirk = 0;
    let cond = 0.74, think = 0, loose = 1, shed = 1, heat = 0.5, cold = 0, glitch = 0, sag = 0, flow = 0.12, inward = 0;
    let accent = 0, ember = 0.45 + 0.12 * Math.sin(t * 1.3), bright = 1, attract = 0, stray = 0, ring = 0, dustB = 1, rate = 1, spinRate = 0.35, glow = 0;
    c.cond.k = 16; c.cond.d = 6.2;
    const face = (f: Face, k = 1): void => { // mezcla una expresión sobre la base
      if (f.bL !== undefined) bL += (f.bL - bL) * k; if (f.bR !== undefined) bR += (f.bR - bR) * k; if (f.furrow !== undefined) furrow += (f.furrow - furrow) * k;
      if (f.lid !== undefined) { lidL += (f.lid - lidL) * k; lidR += (f.lid - lidR) * k; } if (f.squint !== undefined) squint += (f.squint - squint) * k;
      if (f.smile !== undefined) smile += (f.smile - smile) * k; if (f.smirk !== undefined) smirk += (f.smirk - smirk) * k;
      if (f.jaw !== undefined) jaw += (f.jaw - jaw) * k; if (f.round !== undefined) round += (f.round - round) * k;
      roll += (f.roll ?? 0) * k; pitch += (f.pitch ?? 0) * k; yaw += (f.yaw ?? 0) * k; bpitch += (f.lean ?? 0) * k;
    };

    switch (s) {
      case 'idle': // serenidad
        if (t < this.typingUntil) { look = false; gx = Math.sin(t * 2.3) * 0.32; gy = 0.8; pitch += 0.09; lidL = lidR = 0.8; bL = bR = 0.18; smile = 0.15; } // usted escribe: baja la vista y lee
        else if (this.away) { look = false; gx = 0.35 * Math.sin(t * 0.25); gy = 0.3; lidL = lidR = 0.74; bright = 0.82; smile = 0.12; } // la ventana no tiene el foco: se abstrae
        break;
      case 'listening': // atención: se inclina, ladea la cabeza y los cabos sueltos se orientan hacia usted
        face(FACE.atencion); byaw = 0.04 + cx * 0.08; bpitch = 0.075; yaw = cx * 0.16 + 0.06; pitch = cy * 0.1 - 0.02 + this.slow * 0.05; roll = 0.1;
        if (peak > 0.5) bL += 0.2; cond = 1; loose = 0.4; shed = 0; heat = 0.63; inward = 1; attract = 1; flow = 0.06; bright = 0.9;
        break;
      case 'thinking': // curiosidad; hilar fino: la mirada se va primero, luego la cabeza, luego se devana el ovillo
        face(FACE.curiosidad); look = false; gx = 0.62 + Math.sin(t * 0.7) * 0.2; gy = -0.7 + Math.sin(t * 1.1) * 0.12;
        if (st > 0.12) { yaw = 0.24; pitch = -0.11; roll = -0.075; byaw = 0.3; }
        furrow = 0.3; lidL = lidR = 0.98; think = st > 0.3 ? 1 : 0; cond = 0.92; loose = 0.7; shed = 0.45; heat = 0.4; spinRate = 1.7; flow = 0.22; dustB = 1.2;
        break;
      case 'speaking': {
        const [vj, vr, vs] = VIS[vow], on = Math.min(1, this.env * 3.2);
        jaw = clamp(Math.pow(this.env, 0.7) * vj * 1.2, 0, 1); round = vr * on; spread = vs * on; glow = this.env;
        const acc = clamp((peak - 0.3) * 1.7, 0, 1); // acento: la cabeza y las cejas marcan la frase
        byaw = 0.1 + cx * 0.1; bpitch = 0.02 + this.slow * 0.03; yaw = cx * 0.18 + Math.sin(t * 0.9) * 0.035; pitch = cy * 0.1 + acc * 0.06 - this.slow * 0.03; roll = Math.sin(t * 0.6) * 0.025;
        bL = acc * 0.6 + 0.1; bR = acc * 0.4 + 0.1; lidL = lidR = 0.94; cond = 1; loose = 0.45; shed = 0; heat = 0.5 + this.env * 0.3; flow = 0.14; bright = 0.9; smile = 0.22 * (1 - on * 0.5);
        break;
      }
      case 'executing': { // tejer: cabeza gacha, la lanzadera en el pecho; de vez en cuando levanta la vista
        const up = Math.sin(t * 0.9) > 0.86;
        look = up; if (!up) { gx = -0.35; gy = 0.62; }
        byaw = -0.26; yaw = up ? -0.02 : -0.13; pitch = (up ? 0.04 : 0.14) + (R ? 0 : Math.sin(t * 6.2) * 0.008); bpitch = 0.03;
        lidL = lidR = 0.8; furrow = 0.45; squint = 0.4; smile = 0.05; bL = bR = -0.1; cond = 1.05; loose = 0.15; shed = 0; heat = 0.6; flow = 1; ring = 1; spinRate = 1.1; breathAmp = 0.6;
        break;
      }
      case 'success': { // satisfacción contenida; atar cabos: anticipación, reverencia breve; un destello sube desde el nudo
        const b = bell((st - 0.14) / 1.15), k = clamp((st - 1.6) / 1.5, 0, 1);
        face(FACE.satisfaccion, st < 0.14 ? 0.2 : 1 - 0.35 * k);
        pitch = st < 0.14 ? -0.07 : b * 0.34; bpitch = b * 0.07; byaw = 0.08; yaw = cx * 0.1; if (st < 1.3) lidL = lidR = lidL - 0.4 * b;
        accent = -(0.3 + 0.7 * Math.exp(-st * 0.9)); cond = 1.12; loose = 0.5; shed = 0; heat = 0.66 + 0.3 * Math.exp(-st * 1.2); flow = 0.25; bright = 1.02; ember = 1.1;
        if (st >= 0.2 && st - dt < 0.2) { this.flashK = R ? 0.3 : 1; this.flashY = -1.7; this.flashV = 4.2; if (!R) this.burst = 1; }
        break;
      }
      case 'error': { // preocupación; perder el hilo: la trama cae y algunas hebras se funden
        const k = Math.exp(-st * 2.4);
        face(FACE.preocupacion); bL += 0.35; bR -= 0.25; // una ceja algo más alta: contrariedad, no pánico
        yaw = cx * 0.12 + (R ? 0 : Math.sin(st * 14) * 0.07 * k); roll = 0.05; pitch = 0.03; bpitch = -0.035; byaw = 0.12; spread = 0.15; ly = Math.max(cy, 0.05);
        accent = 0.95; cond = 0.88; loose = 1.5; shed = 0.9; heat = 0.12; glitch = R ? 0 : 0.3 + 0.7 * k; sag = 0.85; flow = 0.03; stray = 1; ember = 0.25; bright = 0.95; dustB = 0.5;
        break;
      }
      case 'interrupted': { // sorpresa breve; cortar el hilo: calla en seco, todo queda en vilo y le cede la palabra
        const k = Math.exp(-st * 3);
        face(FACE.sorpresa, 0.35 + 0.65 * k); if (st > 0.5) face(FACE.atencion, 0.6 * (1 - k));
        bpitch = -0.05 * k; pitch = cy * 0.08 - 0.05 * k; roll = st > 0.45 ? 0.06 : 0; yaw = cx * 0.2; byaw = 0.08;
        cond = 1; loose = 0.08; shed = 0; heat = 0.74; bright = 0.82; flow = 0; rate = st < 0.7 ? 0 : 0.12; ember = 0.3; dustB = 0.8;
        break;
      }
      case 'offline': // deshilachado: constelación fría que gira despacio; solo queda la brasa del nudo
        look = false; gx = 0; gy = 0.5; byaw = R ? 0.2 : 0.45 * Math.sin(t * 0.13); yaw = 0; pitch = 0.26; roll = 0.02; bpitch = 0.02;
        lidL = lidR = 0; bL = bR = -0.2; smile = -0.1; cond = 0.1; loose = 0.6; shed = 0; heat = 0.2; cold = 1; flow = 0; bright = 0.75; dustB = 0.55; breathAmp = 0.5;
        ember = 0.55 + 0.45 * Math.pow(0.5 + 0.5 * Math.sin(t * 1.5), 3); c.cond.k = 2.6; c.cond.d = 3.3; spinRate = 0.08;
        break;
    }
    if (this.weaving) { cond = 0; lidL = lidR = 0; shed = 0; ember = 0.9; this.wakeAt = t; this.lastAct = t; this.blinkAt = t + 2; } // naciendo: estrellas alrededor de la brasa
    if (t - this.wakeAt < 2.4 && s !== 'offline') { c.cond.k = 8; c.cond.d = 4.8; } // al despertar se teje de dentro afuera
    if (this.expression) { this.blinkAt = Math.max(this.blinkAt, t + 0.6); face(FACE[this.expression]); if (FACE[this.expression].gx !== undefined) { look = false; gx = FACE[this.expression].gx!; gy = FACE[this.expression].gy ?? 0; } }

    // Pasar el cursor por encima ya provoca algo, distinto en cada parte.
    if (s !== 'offline' && !this.gesture && !this.weaving) switch (this.hover) {
      case 'eyeL': lidL -= 0.2; squint += 0.25; break;
      case 'eyeR': lidR -= 0.2; squint += 0.25; break;
      case 'nose': verge = 0.3; bL += 0.25; break;
      case 'mouth': smile += 0.2; smirk -= 0.25; break;
      case 'hair': bL += 0.2; bR += 0.2; loose += 0.5; break;
      case 'knot': ember += 0.5; break;
      default: break;
    }
    // Micro-gestos en reposo, aburrimiento a los 40 s sin nadie, y reacciones (uno a la vez).
    if (s === 'idle' && !this.gesture && !this.weaving && !this.expression && !this.away && t >= this.typingUntil) {
      if (t - this.lastAct > 40) { this.play('bored'); this.lastAct = t; this.lastReaction = SAY.bored; }
      else if (this.microGestures && t > this.nextGesture) this.play(IDLE[this.gi++ % IDLE.length]!);
    }
    if (this.gesture) {
      this.gt += dt; const g = this.gesture, u = this.gt / DUR[g], du = dt / DUR[g], at = (x: number): boolean => u >= x && u - du < x;
      if (u >= 1) { this.gesture = null; this.nextGesture = t + 4 + this.rand() * 5; }
      else switch (g) {
        case 'brow': face(FACE.ironia, bell(u)); break; // la ceja de la ironía seca, con media sonrisa
        case 'glance': look = false; gx = (this.gi % 2 ? 0.85 : -0.85) * plateau(u, 0.12); gy = -0.15 * plateau(u, 0.12); if (at(0.02)) this.blink = 0.14; break;
        case 'thread': // un hilo suelto: lo mira, y con un toque seco de cabeza lo devuelve a su sitio
          stray = u < 0.74 ? plateau(u / 0.74, 0.25) : 0;
          if (u > 0.22 && u < 0.78) { look = false; gx = -0.75; gy = -0.6; bL += 0.6; lidL = lidR = 1.08; }
          if (at(0.74) && !R) { c.yaw.v += 2.2; c.roll.v -= 0.8; this.ix += 0.25; }
          break;
        case 'settle': pitch -= 0.06 * bell(u); breathAmp = 1 + 1.6 * bell(u); cond += 0.3 * bell(u * 1.4); loose -= 0.6 * bell(u); if (at(0.15)) { this.flashK = 0.22; this.flashY = 1.4; this.flashV = -4.5; } break; // se recompone
        case 'nod': pitch += 0.11 * bell(u); lidL = lidR = lidL - 0.3 * bell(u); smile += 0.2 * bell(u); break;
        case 'stache': smile += Math.sin(u * Math.PI * 5) * 0.55 * (1 - u); round += 0.2 * bell(u * 2); break;
        case 'sigh': breathAmp = 1 + 2.2 * bell(u); lidL = lidR = lidL - 0.25 * bell(u); loose += 0.5 * bell(u); pitch += 0.03 * bell(u); break;
        case 'wink': if (this.gSide < 0) { this.winkL = bell(u * 1.6); bR += 0.7 * bell(u); smirk -= 0.5 * bell(u); } else { this.winkR = bell(u * 1.6); bL += 0.7 * bell(u); smirk += 0.5 * bell(u); } smile += 0.35 * bell(u); break;
        case 'nose': verge = plateau(u, 0.15); look = false; gx = 0; gy = 0.25 * plateau(u, 0.15); bpitch -= 0.04 * bell(u); bL += 0.9 * plateau(u, 0.2); bR += 0.3 * plateau(u, 0.2); break; // bizquea hacia el dedo
        case 'ruffle': if (u < 0.5) { look = false; gx = 0; gy = -0.85; bL += 0.5; bR += 0.5; } loose += 1.2 * (1 - u); cond += 0.25 * bell((u - 0.5) * 2); if (at(0.55)) { this.flashK = 0.2; this.flashY = 1.4; this.flashV = -4.5; } break;
        case 'knot': if (u < 0.45) { look = false; gx = 0; gy = 0.9; pitch += 0.12 * bell(u / 0.45); } else { pitch += 0.09 * bell((u - 0.45) / 0.55); smile += 0.4 * bell((u - 0.45) / 0.55); } break;
        case 'attend': face(FACE.atencion, bell(u)); pitch += 0.05 * bell(u * 1.6); break;
        case 'weary': // cinco veces seguidas: cierra los ojos, respira, y le dedica la ceja y media sonrisa
          if (u < 0.4) { lidL = lidR = 0.88 * (1 - plateau(u / 0.4, 0.3)); breathAmp = 2.4; pitch += 0.05 * bell(u / 0.4); }
          else { face(FACE.ironia, plateau((u - 0.4) / 0.6, 0.2)); if (u < 0.62) { look = false; gx = 0.8; gy = -0.2; } }
          break;
        case 'bored': // devana un ovillo pequeño para entretenerse y luego le mira de reojo: ¿sigue usted ahí?
          if (u < 0.72) { think = u > 0.06 ? 1 : 0; look = false; gx = 0.62; gy = -0.68; yaw += 0.16 * plateau(u / 0.72, 0.2); pitch -= 0.06 * plateau(u / 0.72, 0.2); spinRate = 1.5; face(FACE.curiosidad, 0.6 * plateau(u / 0.72, 0.2)); }
          else face(FACE.ironia, plateau((u - 0.72) / 0.28, 0.25));
          break;
        case 'greet': face(FACE.atencion, bell(u)); pitch += 0.13 * bell((u - 0.1) / 0.6); smile += 0.35 * bell(u); if (at(0.12)) { this.flashK = 0.3; this.flashY = -1.9; this.flashV = 4.2; } break;
      }
    }
    if (!this.gesture || this.gesture !== 'wink') { this.winkL = 0; this.winkR = 0; }
    squint += Math.max(0, smile) * 0.35; // la sonrisa llega a los ojos

    if (R) { byaw = 0.12; yaw = cx * 0.1; roll = 0; bpitch *= 0.3; pitch = s === 'offline' ? pitch : pitch * 0.5; loose *= 0.25; shed = 0; flow *= 0.3; spinRate *= 0.3; stray = 0; sag *= 0.4; breathAmp = Math.min(breathAmp, 1); }
    byaw += this.drag.yaw; bpitch += this.drag.pitch;
    if (!R) loose += this.wind * 1.3;

    // Sacadas: la mirada nunca está clavada. Parpadeo, a veces doble; ninguno si está apagado.
    if (t > this.sacAt) { this.sacAt = t + 0.7 + this.rand() * 1.9; this.sx = (this.rand() - 0.5) * 0.14; this.sy = (this.rand() - 0.5) * 0.09; }
    if (s !== 'offline' && t > this.blinkAt) { this.blink = 0.15; this.blinkAt = t + (this.rand() < 0.16 ? 0.28 : 2.4 + this.rand() * 3.8); }
    this.blink = Math.max(0, this.blink - dt);
    const blinkK = this.blink > 0 ? 1 - bell(this.blink / 0.15) : 1;

    const o = { yaw: c.yaw.step(yaw, dt), pitch: c.pitch.step(pitch, dt), roll: c.roll.step(roll, dt), byaw: c.byaw.step(byaw, dt), bpitch: c.bpitch.step(bpitch, dt) };
    if (look) { // mirar a un punto compensa el giro de cabeza y busto: los ojos llegan antes que la cabeza
      gx = clamp((lx * 0.52 - (o.yaw + o.byaw - this.drag.yaw * 0.6)) / 0.5, -1, 1) + this.sx; gy = clamp((ly * 0.4 - (o.pitch + o.bpitch)) / 0.4, -1, 1) + this.sy;
    }
    P.state = s; P.t = t; P.yaw = o.yaw; P.pitch = o.pitch; P.roll = o.roll; P.byaw = o.byaw; P.bpitch = o.bpitch;
    P.breath = (0.5 + 0.5 * Math.sin(t * breathRate)) * breathAmp;
    P.gx = c.gx.step(clamp(gx, -1.1, 1.1), dt); P.gy = c.gy.step(clamp(gy, -1.1, 1.1), dt); P.verge = c.verge.step(verge, dt);
    P.lidL = Math.max(0, c.lidL.step(lidL, dt) * blinkK * (1 - this.winkL)); P.lidR = Math.max(0, c.lidR.step(lidR, dt) * blinkK * (1 - this.winkR));
    P.browL = c.browL.step(bL, dt); P.browR = c.browR.step(bR, dt); P.furrow = c.furrow.step(furrow, dt); P.squint = clamp(c.squint.step(squint, dt), 0, 0.9);
    P.jaw = clamp(c.jaw.step(jaw, dt), 0, 1.1); P.round = c.round.step(round, dt); P.spread = c.spread.step(spread, dt); P.smile = c.smile.step(smile, dt); P.smirk = c.smirk.step(smirk, dt);
    P.cond = c.cond.step(cond + (s === 'idle' && !this.weaving ? 0.035 * Math.sin(t * breathRate) : 0), dt); P.think = clamp(c.think.step(think, dt), 0, 1.05);
    P.loose = Math.max(0, c.loose.step(loose, dt)); P.shed = clamp(c.shed.step(shed, dt), 0, 1);
    P.heat = c.heat.step(heat, dt); P.cold = clamp(c.cold.step(cold, dt), 0, 1); P.glitch = clamp(c.glitch.step(glitch, dt), 0, 1); P.sag = Math.max(0, c.sag.step(sag, dt));
    P.flow = Math.max(0, c.flow.step(flow, dt)); P.inward = clamp(c.inward.step(inward, dt), 0, 1); P.ember = Math.max(0, c.ember.step(ember, dt)); P.glow = s === 'speaking' ? glow : 0;
    P.accent = c.accent.step(accent, dt); P.bright = c.bright.step(bright, dt); P.attract = c.attract.step(attract, dt); P.stray = clamp(c.stray.step(stray, dt), 0, 1.2);
    P.dustRing = clamp(c.ring.step(ring, dt), 0, 1); P.dustB = c.dustB.step(dustB, dt);
    { // lanzadera: ida y vuelta con ease en los extremos; cada pasada baja una fila
      const ph = this.tw * 0.9, pass = Math.floor(ph), u = ph - pass, e = u * u * (3 - 2 * u);
      P.shutX = (pass % 2 ? 1 - e * 2 : e * 2 - 1) * 1.45; P.shutY = -1.8 - ((pass % 5) + e) * 0.11;
    }
    // Tiempo de onda: se detiene al interrumpir (la trama queda en vilo).
    const rt = clamp(c.rate.step(rate, dt), 0, 1.2);
    this.tw += dt * rt; this.spin += dt * spinRate * (0.3 + 0.7 * rt); P.tw = this.tw; P.spin = this.spin;
    // Inercia: el pelo y los cabos sueltos van con retraso respecto a la cabeza (acción solapada).
    const wy = (o.yaw + o.byaw - this.yawPrev) / dt, wp = (o.pitch + o.bpitch - this.pitchPrev) / dt; this.yawPrev = o.yaw + o.byaw; this.pitchPrev = o.pitch + o.bpitch;
    this.ix += (wy * 0.11 - this.ix) * (1 - Math.exp(-dt * 7)); this.iy += (wp * 0.11 - this.iy) * (1 - Math.exp(-dt * 7));
    P.inertX = R ? 0 : clamp(this.ix, -0.5, 0.5); P.inertY = R ? 0 : clamp(this.iy, -0.5, 0.5);
    // Destello que recorre la trama y ráfaga de polvo.
    this.flashY += dt * this.flashV; this.flashK = Math.max(0, this.flashK - dt * 0.75);
    P.flashY = this.flashY; P.flashK = this.flashK;
    this.burst = Math.max(0, this.burst - dt * 0.55); P.dustBurst = this.burst;
    // Historia de la voz: el shader la reparte por la trama como una onda con la forma de lo dicho.
    const lvl = s === 'speaking' || s === 'listening' ? this.env : 0; P.level = lvl;
    this.histAcc += dt * 20 * rt;
    while (this.histAcc >= 1) { this.histAcc -= 1; P.hist.copyWithin(1, 0, HIST - 1); }
    P.hist[0] = lvl; P.histPhase = this.histAcc; P.vowel = vow;
    this.wind = Math.max(0, this.wind - dt * 2.5);
    return P;
  }
}

/** Voz simulada: frases con pausas y sílabas, para probar la boca sin audio real. */
export function simVoice(t: number): number {
  const phrase = Math.sin(t * 0.8) + Math.sin(t * 0.37 + 1) * 0.6 > -0.55 ? 1 : 0;
  const syl = Math.pow(Math.abs(Math.sin(t * 8.5 + Math.sin(t * 2.3) * 2.2)), 1.4);
  const tone = 0.55 + 0.45 * Math.sin(t * 3.1 + Math.sin(t * 1.3) * 3);
  return phrase * syl * tone;
}
