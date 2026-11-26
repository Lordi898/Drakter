// Ascuario — módulo ES del avatar, listo para integrar (React o lo que sea). El panel de pruebas usa esta misma API.
// createAvatar es un envoltorio de la capa (layer.ts): pone el renderer, el bucle y la entrada de ratón.
import * as THREE from 'three';
import type { AvatarState, Expr, Viseme, Zone } from './brain';
import { createAscuarioLayer } from './layer';
import type { View } from './scene';

export type { AvatarState, Expr, Viseme, Zone };
export { STATES, EXPRESSIONS } from './brain';

export interface AvatarOptions {
  reducedMotion?: boolean; pixelRatio?: number;
  /** Lienzo con alfa premultiplicado y sin fondo propio (sin halo). */
  transparent?: boolean;
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
  const gl = new THREE.WebGLRenderer({ canvas, alpha: true, premultipliedAlpha: true, antialias: true, powerPreference: 'low-power', stencil: false });
  if (!gl.capabilities.isWebGL2) { gl.dispose(); throw new Error('webgl2-unavailable'); }
  gl.setClearColor(0x000000, 0); gl.autoClear = false; // limpia el envoltorio; la capa nunca
  canvas.style.opacity = '0'; canvas.style.transition = 'opacity .6s ease-out';
  const onLost = (e: Event): void => e.preventDefault(); canvas.addEventListener('webglcontextlost', onLost);

  const mq = typeof matchMedia === 'function' ? matchMedia('(prefers-reduced-motion: reduce)') : null;
  const reduced = opts.reducedMotion ?? mq?.matches ?? false;
  const dpr = opts.pixelRatio ?? 1;
  let size = { w: canvas.clientWidth || 500, h: canvas.clientHeight || 600 };
  const layer = createAscuarioLayer(gl, { ...opts, reducedMotion: reduced, pixelRatio: dpr });
  const { brain } = layer;
  const fit = (): void => { gl.setPixelRatio(dpr); gl.setSize(size.w, size.h, false); layer.resize(size.w, size.h, dpr); };
  fit();
  let disposed = false, cap = opts.fps ?? 30, startMs = 0;

  // ---- bucle ----
  let raf = 0, last = 0, total = 0, work = 0, janks = 0, maxGap = 0, winStart = 0, winFrames = 0, winWork = 0, fps = 0, ms = 0;
  const tick = (now: number): void => {
    raf = requestAnimationFrame(tick);
    if (cap > 0 && now - last < 1000 / cap - 2) return;
    const dt = last ? (now - last) / 1000 : 1 / 30;
    if (last && now - last > 50) janks++; if (last) maxGap = Math.max(maxGap, now - last);
    last = now;
    const a = performance.now();
    gl.clear();
    layer.render(dt, { x: 0, y: 0, width: size.w, height: size.h });
    const w = performance.now() - a; total++; work += w; winFrames++; winWork += w;
    if (now - winStart >= 500) { fps = (winFrames * 1000) / (now - winStart); ms = winWork / winFrames; winStart = now; winFrames = 0; winWork = 0; }
  };
  let loaded = false;
  const start = (): void => { if (loaded && !raf && !document.hidden && !disposed) { last = 0; winStart = performance.now(); raf = requestAnimationFrame(tick); } };
  const stop = (): void => { cancelAnimationFrame(raf); raf = 0; };
  const onVis = (): void => (document.hidden ? stop() : start());

  // ---- entrada ----
  const onMove = (e: PointerEvent): void => {
    const sc = layer.scene(); if (!sc) return;
    const b = canvas.getBoundingClientRect(), f = sc.face(), half = Math.max(b.width, b.height) * 0.6;
    if (!layer.externalGaze()) { brain.cursor.x = Math.max(-1, Math.min(1, (e.clientX - b.left - f.x) / half)); brain.cursor.y = Math.max(-1, Math.min(1, (e.clientY - b.top - f.y) / half)); brain.cursor.active = true; }
    const inside = e.clientX >= b.left && e.clientX <= b.right && e.clientY >= b.top && e.clientY <= b.bottom;
    const z = inside ? sc.hit(e.clientX - b.left, e.clientY - b.top) : null;
    if (z !== brain.hover) { brain.hover = z; canvas.style.cursor = z ? 'pointer' : ''; }
    brain.touch();
  };
  const onLeave = (): void => { if (!layer.externalGaze()) brain.cursor.active = false; brain.hover = null; };
  const onDown = (e: PointerEvent): void => { const sc = layer.scene(); if (!sc) return; const b = canvas.getBoundingClientRect(), z = sc.hit(e.clientX - b.left, e.clientY - b.top); if (z) brain.click(z); else brain.touch(); };
  // Foco y blur de la ventana los avisa el anfitrión con notify(); aquí no se escuchan para no duplicarlos.
  const onMq = (): void => { if (opts.reducedMotion === undefined && mq) layer.setReducedMotion(mq.matches); };
  addEventListener('pointermove', onMove); document.documentElement.addEventListener('pointerleave', onLeave); canvas.addEventListener('pointerdown', onDown);
  document.addEventListener('visibilitychange', onVis); mq?.addEventListener('change', onMq);

  const ready = layer.ready.then(() => {
    if (disposed) return;
    loaded = true; startMs = performance.now() - t0;
    canvas.style.opacity = '1';
    start();
  });

  return {
    ready,
    setState: layer.setState,
    setAudioLevel: layer.setAudioLevel,
    setViseme: (v) => layer.setViseme?.(v),
    lookAt: layer.lookAt,
    notify: layer.notify,
    setReducedMotion: layer.setReducedMotion,
    resize: (w, h) => { size = { w, h }; fit(); },
    dispose: () => {
      disposed = true; stop();
      removeEventListener('pointermove', onMove); document.documentElement.removeEventListener('pointerleave', onLeave); canvas.removeEventListener('pointerdown', onDown);
      document.removeEventListener('visibilitychange', onVis); mq?.removeEventListener('change', onMq);
      canvas.removeEventListener('webglcontextlost', onLost);
      layer.dispose(); gl.dispose();
    },
    debug: {
      stats: () => ({ fps, ms, total, work, janks, maxGap, running: raf !== 0, hidden: document.hidden, calls: gl.info.render.calls, tris: gl.info.render.triangles, startMs }),
      reset: () => { total = 0; work = 0; janks = 0; maxGap = 0; },
      setFps: (n) => { cap = n; }, setMicroGestures: (on) => { brain.microGestures = on; }, expression: (e) => { brain.expr = e; },
      click: (z) => brain.click(z), bored: () => brain.boredNow(), hover: (z) => { brain.hover = z; }, anchors: () => layer.scene()?.anchors() ?? {}, state: () => brain.state, level: () => brain.voice,
    },
  };
}
