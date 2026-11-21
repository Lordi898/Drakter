// Ascuario — módulo ES del avatar, listo para integrar (React o lo que sea). El panel de pruebas usa esta misma API.
import * as THREE from 'three';
import { Brain, type AvatarState, type Expr, type Viseme, type Zone } from './brain';
import { buildScene, type AvatarScene, type View } from './scene';
import { loadGeos } from './geos';

export type { AvatarState, Expr, Viseme, Zone };
export { STATES, EXPRESSIONS } from './brain';

export interface AvatarOptions {
  reducedMotion?: boolean; pixelRatio?: number;
  /** Límite de fotogramas (30 por defecto; 0 = sin límite). */
  fps?: number;
  /** Micro-gestos en reposo (por defecto sí, salvo con movimiento reducido). */
  microGestures?: boolean;
  /** URL de ascuario-geo.json (geometría horneada) cuando se usa como módulo ES; sin ella, se esculpe al arrancar. */
  geometryUrl?: string;
  /** Encuadre de depuración. */
  view?: View;
}
export interface Avatar {
  setState(s: AvatarState): void;
  setAudioLevel(level: number): void;
  setViseme(v: string | null): void;
  lookAt(x: number, y: number): void;
  notify(e: 'userTyping' | 'focus' | 'blur'): void;
  setReducedMotion(on: boolean): void;
  resize(w: number, h: number): void;
  dispose(): void;
  /** Se resuelve cuando la geometría está lista y los shaders compilados (el lienzo aparece con un fundido). */
  readonly ready: Promise<void>;
  /** Utilidades del panel de pruebas y de la automatización; no forman parte del contrato. */
  readonly debug: {
    stats(): { fps: number; ms: number; total: number; work: number; janks: number; maxGap: number; running: boolean; hidden: boolean; calls: number; tris: number; startMs: number };
    reset(): void; setFps(n: number): void; setMicroGestures(on: boolean): void; expression(e: Expr | null): void;
    click(z: Zone): void; hover(z: Zone | null): void; bored(): void; anchors(): Record<string, [number, number]>; state(): AvatarState; level(): number;
  };
}

export function createAvatar(canvas: HTMLCanvasElement, opts: AvatarOptions = {}): Avatar {
  const t0 = performance.now();
  const gl = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, powerPreference: 'low-power', stencil: false });
  if (!gl.capabilities.isWebGL2) { gl.dispose(); throw new Error('webgl2-unavailable'); }
  gl.toneMapping = THREE.ACESFilmicToneMapping; gl.toneMappingExposure = 1.15;
  canvas.style.opacity = '0'; canvas.style.transition = 'opacity .6s ease-out';
  const onLost = (e: Event): void => e.preventDefault(); canvas.addEventListener('webglcontextlost', onLost);

  const brain = new Brain();
  const mq = typeof matchMedia === 'function' ? matchMedia('(prefers-reduced-motion: reduce)') : null;
  brain.reduced = opts.reducedMotion ?? mq?.matches ?? false;
  brain.microGestures = opts.microGestures ?? !brain.reduced;
  let sc: AvatarScene | null = null, disposed = false, dpr = opts.pixelRatio ?? 1, size = { w: canvas.clientWidth || 500, h: canvas.clientHeight || 600 };
  let cap = opts.fps ?? 30, external = false, startMs = 0;

  // ---- bucle ----
  let raf = 0, last = 0, total = 0, work = 0, janks = 0, maxGap = 0, winStart = 0, winFrames = 0, winWork = 0, fps = 0, ms = 0;
  const tick = (now: number): void => {
    raf = requestAnimationFrame(tick);
    if (cap > 0 && now - last < 1000 / cap - 2) return;
    const dt = last ? (now - last) / 1000 : 1 / 30;
    if (last && now - last > 50) janks++; if (last) maxGap = Math.max(maxGap, now - last);
    last = now;
    const a = performance.now();
    if (brain.state !== 'speaking' && brain.state !== 'listening') brain.voice = 0;
    sc!.render(brain.update(dt), Math.min(dt, 0.05));
    const w = performance.now() - a; total++; work += w; winFrames++; winWork += w;
    if (now - winStart >= 500) { fps = (winFrames * 1000) / (now - winStart); ms = winWork / winFrames; winStart = now; winFrames = 0; winWork = 0; }
  };
  const start = (): void => { if (sc && !raf && !document.hidden && !disposed) { last = 0; winStart = performance.now(); raf = requestAnimationFrame(tick); } };
  const stop = (): void => { cancelAnimationFrame(raf); raf = 0; };
  const onVis = (): void => (document.hidden ? stop() : start());

  // ---- entrada ----
  const onMove = (e: PointerEvent): void => {
    if (!sc) return;
    const b = canvas.getBoundingClientRect(), f = sc.face(), half = Math.max(b.width, b.height) * 0.6;
    if (!external) { brain.cursor.x = Math.max(-1, Math.min(1, (e.clientX - b.left - f.x) / half)); brain.cursor.y = Math.max(-1, Math.min(1, (e.clientY - b.top - f.y) / half)); brain.cursor.active = true; }
    const inside = e.clientX >= b.left && e.clientX <= b.right && e.clientY >= b.top && e.clientY <= b.bottom;
    const z = inside ? sc.hit(e.clientX - b.left, e.clientY - b.top) : null;
    if (z !== brain.hover) { brain.hover = z; canvas.style.cursor = z ? 'pointer' : ''; }
    brain.touch();
  };
  const onLeave = (): void => { if (!external) brain.cursor.active = false; brain.hover = null; };
  const onDown = (e: PointerEvent): void => { if (!sc) return; const b = canvas.getBoundingClientRect(), z = sc.hit(e.clientX - b.left, e.clientY - b.top); if (z) brain.click(z); else brain.touch(); };
  const onFocus = (): void => brain.notify('focus'), onBlur = (): void => brain.notify('blur');
  const onMq = (): void => { if (opts.reducedMotion === undefined && mq) brain.reduced = mq.matches; };
  addEventListener('pointermove', onMove); document.documentElement.addEventListener('pointerleave', onLeave); canvas.addEventListener('pointerdown', onDown);
  addEventListener('focus', onFocus); addEventListener('blur', onBlur); document.addEventListener('visibilitychange', onVis); mq?.addEventListener('change', onMq);

  const ready = (async () => {
    performance.mark('av:start'); const geos = await loadGeos(opts.geometryUrl); performance.mark('av:geos');
    if (disposed) return;
    sc = buildScene(gl, geos, opts.view); performance.mark('av:scene');
    sc.resize(size.w, size.h, dpr);
    await sc.compile(); performance.mark('av:compiled');
    if (disposed) return;
    startMs = performance.now() - t0;
    canvas.style.opacity = '1';
    start();
  })();

  return {
    ready,
    setState: (s) => brain.setState(s),
    setAudioLevel: (l) => { brain.voice = Math.max(0, Math.min(1, l || 0)); },
    setViseme: (v) => { brain.viseme = v && 'AEIOUM'.includes(v[0]!.toUpperCase()) ? (v[0]!.toUpperCase() as Viseme) : v && 'BP'.includes(v[0]!.toUpperCase()) ? 'M' : null; },
    lookAt: (x, y) => { external = true; brain.cursor.x = Math.max(-1, Math.min(1, x)); brain.cursor.y = Math.max(-1, Math.min(1, y)); brain.cursor.active = true; },
    notify: (e) => brain.notify(e),
    setReducedMotion: (on) => { brain.reduced = on; brain.microGestures = opts.microGestures ?? !on; },
    resize: (w, h) => { size = { w, h }; sc?.resize(w, h, dpr); },
    dispose: () => {
      disposed = true; stop();
      removeEventListener('pointermove', onMove); document.documentElement.removeEventListener('pointerleave', onLeave); canvas.removeEventListener('pointerdown', onDown);
      removeEventListener('focus', onFocus); removeEventListener('blur', onBlur); document.removeEventListener('visibilitychange', onVis); mq?.removeEventListener('change', onMq);
      canvas.removeEventListener('webglcontextlost', onLost);
      sc?.dispose(); gl.dispose(); sc = null;
    },
    debug: {
      stats: () => ({ fps, ms, total, work, janks, maxGap, running: raf !== 0, hidden: document.hidden, calls: gl.info.render.calls, tris: gl.info.render.triangles, startMs }),
      reset: () => { total = 0; work = 0; janks = 0; maxGap = 0; },
      setFps: (n) => { cap = n; }, setMicroGestures: (on) => { brain.microGestures = on; }, expression: (e) => { brain.expr = e; },
      click: (z) => brain.click(z), bored: () => brain.boredNow(), hover: (z) => { brain.hover = z; }, anchors: () => sc?.anchors() ?? {}, state: () => brain.state, level: () => brain.voice,
    },
  };
}
