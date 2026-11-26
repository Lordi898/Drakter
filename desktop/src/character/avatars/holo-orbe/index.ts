// «Holo-Orbe» con lienzo propio: createAvatar(canvas, opts) es un envoltorio de la capa (layer.ts) que pone
// el renderer, el bucle y la entrada de ratón. No toca el DOM fuera del lienzo que recibe.
import * as THREE from 'three';
import type { Avatar3D, AvatarOptions } from '../types';
import { createHoloOrbeLayer } from './layer';

export { STATES, EXPRESSIONS } from './brain';
export type { AvatarState, Expression, Zone } from './brain';

/** Límite de fotogramas tras el tejido (el tejido va a todo lo que dé, 8 ms por fotograma). */
const CAP_FPS = 30;

export interface HoloOrbeAvatar extends Avatar3D {
  readonly ready: Promise<void>;
  /** Para pruebas y medición; la app no lo necesita. */
  readonly debug: { stats(): { fps: number; ms: number; total: number; janks: number; maxGap: number; running: boolean; calls: number; strands: number; readyMs: number } };
}

export function createAvatar(canvas: HTMLCanvasElement, opts: AvatarOptions = {}): HoloOrbeAvatar {
  const transparent = opts.transparent === true;
  const gl = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: transparent, premultipliedAlpha: true, depth: true, stencil: false, powerPreference: 'default' });
  if (!gl.capabilities.isWebGL2) { gl.dispose(); throw new Error('webgl2-unavailable'); }
  gl.setClearColor(0x000000, transparent ? 0 : 1); gl.autoClear = false; // limpia el envoltorio; la capa nunca
  const mq = matchMedia('(prefers-reduced-motion: reduce)');
  const dpr = opts.pixelRatio ?? 1;
  let cw = canvas.clientWidth || 500, ch = canvas.clientHeight || 600, disposed = false, lost = false, compiled = false;
  const layer = createHoloOrbeLayer(gl, { ...opts, reducedMotion: opts.reducedMotion ?? mq.matches, pixelRatio: dpr });
  const { brain, scene: r } = layer;
  const fit = (): void => { gl.setPixelRatio(dpr); gl.setSize(cw, ch, false); layer.resize(cw, ch, dpr); };
  fit();
  const onRm = (): void => { if (opts.reducedMotion === undefined) layer.setReducedMotion(mq.matches); };
  mq.addEventListener('change', onRm);

  // Puntero: mirada, tacto sobre las hebras, viento por velocidad, zonas bajo el cursor, arrastre para girar y clic.
  let downX = 0, downY = 0, down = false, dragged = false, lastX = 0, lastY = 0, lastMove = 0;
  const onMove = (e: PointerEvent): void => {
    const b = canvas.getBoundingClientRect(), x = e.clientX - b.left, y = e.clientY - b.top, inside = x >= 0 && y >= 0 && x <= b.width && y <= b.height;
    if (!layer.externalGaze()) { const f = r.face(), half = Math.max(b.width, b.height) * 0.6; brain.cursor.x = Math.max(-1, Math.min(1, (x - f.x) / half)); brain.cursor.y = Math.max(-1, Math.min(1, (y - f.y) / half)); brain.cursor.active = true; }
    const on = inside && r.touch(x, y); if (!inside) r.touch(null);
    brain.hover = inside ? r.hit(x, y) : null; if (inside) brain.interact();
    const now = performance.now(), sp = Math.hypot(x - lastX, y - lastY) / Math.max(8, now - lastMove); lastX = x; lastY = y; lastMove = now;
    if (on) brain.wind = Math.min(1, Math.max(brain.wind, sp * 0.45));
    if (down) {
      if (!dragged && Math.hypot(e.clientX - downX, e.clientY - downY) > 7) { dragged = true; brain.drag.active = true; canvas.style.cursor = 'grabbing'; }
      if (dragged) { brain.drag.yaw = Math.max(-1.5, Math.min(1.5, brain.drag.yaw + e.movementX * 0.009)); brain.drag.pitch = Math.max(-0.35, Math.min(0.35, brain.drag.pitch + e.movementY * 0.004)); }
    }
  };
  const onLeave = (): void => { if (!layer.externalGaze()) brain.cursor.active = false; brain.hover = null; r.touch(null); };
  const onDown = (e: PointerEvent): void => { down = true; dragged = false; downX = e.clientX; downY = e.clientY; canvas.setPointerCapture(e.pointerId); };
  const onUp = (e: PointerEvent): void => {
    if (!down) return; down = false; canvas.style.cursor = ''; brain.drag.active = false;
    if (!dragged) { const b = canvas.getBoundingClientRect(), z = r.hit(e.clientX - b.left, e.clientY - b.top); if (z) brain.click(z); }
  };
  addEventListener('pointermove', onMove); document.documentElement.addEventListener('pointerleave', onLeave);
  canvas.addEventListener('pointerdown', onDown); canvas.addEventListener('pointerup', onUp); canvas.addEventListener('pointercancel', onUp);
  canvas.style.touchAction = 'none';

  // Bucle: teje por tandas al nacer, limita fotogramas después y se detiene del todo cuando la página no se ve.
  let raf = 0, last = 0, total = 0, janks = 0, maxGap = 0, winStart = 0, winFrames = 0, winWork = 0, fps = 0, ms = 0;
  const draw = (dt: number): void => { gl.clear(); layer.render(dt, { x: 0, y: 0, width: cw, height: ch }); };
  const tick = (now: number): void => {
    raf = requestAnimationFrame(tick);
    if (!brain.weaving && now - last < 1000 / CAP_FPS - 5) return; // margen amplio: un rAF que llega 1 ms antes no debe costar un fotograma entero
    const dt = last ? (now - last) / 1000 : 1 / 30;
    if (last && now - last > 50) janks++; if (last) maxGap = Math.max(maxGap, now - last);
    last = now;
    const t0 = performance.now();
    draw(dt);
    const w = performance.now() - t0; total++; winFrames++; winWork += w;
    if (now - winStart >= 500) { fps = (winFrames * 1000) / (now - winStart); ms = winWork / winFrames; winStart = now; winFrames = 0; winWork = 0; }
  };
  const start = (): void => { if (!raf && !document.hidden && !lost && !disposed && compiled) { last = 0; winStart = performance.now(); winFrames = 0; raf = requestAnimationFrame(tick); } };
  const stop = (): void => { cancelAnimationFrame(raf); raf = 0; };
  const onVis = (): void => (document.hidden ? stop() : start());
  const onLost = (e: Event): void => { e.preventDefault(); lost = true; stop(); };
  const onRestored = (): void => { lost = false; start(); };
  document.addEventListener('visibilitychange', onVis); canvas.addEventListener('webglcontextlost', onLost); canvas.addEventListener('webglcontextrestored', onRestored);

  const ready = layer.ready.then(() => { if (!disposed) { compiled = true; start(); } });

  return {
    ready,
    setState: layer.setState,
    setAudioLevel: layer.setAudioLevel,
    setViseme: (v) => layer.setViseme?.(v),
    lookAt: layer.lookAt,
    notify: layer.notify,
    setReducedMotion: (on) => { opts = { ...opts, reducedMotion: on }; layer.setReducedMotion(on); },
    setTheme: (theme) => layer.setTheme?.(theme),
    resize: (w, h) => { if (w > 0 && h > 0) { cw = w; ch = h; fit(); if (compiled && !lost && !disposed) draw(0); } },
    dispose: () => {
      disposed = true; stop(); mq.removeEventListener('change', onRm);
      removeEventListener('pointermove', onMove); document.documentElement.removeEventListener('pointerleave', onLeave);
      canvas.removeEventListener('pointerdown', onDown); canvas.removeEventListener('pointerup', onUp); canvas.removeEventListener('pointercancel', onUp);
      document.removeEventListener('visibilitychange', onVis); canvas.removeEventListener('webglcontextlost', onLost); canvas.removeEventListener('webglcontextrestored', onRestored);
      layer.dispose(); gl.dispose();
    },
    debug: {
      stats: () => ({ fps, ms, total, janks, maxGap, running: raf !== 0, calls: r.info.calls(), strands: r.info.strands(), readyMs: layer.readyMs() }),
    },
  };
}
