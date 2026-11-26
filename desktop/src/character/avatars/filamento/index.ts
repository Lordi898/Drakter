// Filamento (dorado) — módulo ES del avatar para el lienzo propio (modo Drakter). createAvatar es un envoltorio de
// la capa (layer.ts): pone el renderer, el bucle (30 fps con limitador por calendario) y la entrada de ratón.
import * as THREE from 'three';
import type { Avatar3D } from '../types';
import { createFilamentoLayer, type FilamentoOptions } from './layer';

export type { FilamentoOptions };
export type Filamento = Avatar3D & { readonly ready: Promise<void> };

export function createAvatar(canvas: HTMLCanvasElement, opts: FilamentoOptions = {}): Filamento {
  const gl = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: opts.transparent === true, premultipliedAlpha: true, depth: false, stencil: false, powerPreference: 'default' });
  if (!gl.capabilities.isWebGL2) { gl.dispose(); throw new Error('webgl2-unavailable'); }
  gl.setClearColor(0x000000, 0); gl.autoClear = false; // limpia el envoltorio; la capa nunca
  const onLost = (e: Event): void => e.preventDefault(); // sin restaurar: la app recrea el avatar
  canvas.addEventListener('webglcontextlost', onLost);

  const mq = typeof matchMedia === 'function' ? matchMedia('(prefers-reduced-motion: reduce)') : null;
  const dpr = opts.pixelRatio ?? 1;
  let size = { w: canvas.clientWidth || 500, h: canvas.clientHeight || 600 };
  const layer = createFilamentoLayer(gl, { ...opts, reducedMotion: opts.reducedMotion ?? mq?.matches ?? false, pixelRatio: dpr });
  const { brain, renderer: r } = layer;
  const fit = (): void => { gl.setPixelRatio(dpr); gl.setSize(size.w, size.h, false); layer.resize(size.w, size.h, dpr); };
  fit();
  let disposed = false, loaded = false, lost = false;

  // ---- bucle: tejiendo va a todo gas; después, 30 fps; se detiene del todo cuando la página no se ve ----
  let raf = 0, last = 0, due = 0;
  const frame = (dt: number): void => { gl.clear(); layer.render(dt, { x: 0, y: 0, width: size.w, height: size.h }); };
  const tick = (now: number): void => {
    raf = requestAnimationFrame(tick);
    if (!brain.weaving) { // limitador con fase: tras un fotograma tardío recupera el ritmo en vez de perder otro
      const iv = 1000 / 30; if (now < due - 2) return; due = now - due > iv ? now + iv : due + iv;
    }
    const dt = last ? (now - last) / 1000 : 1 / 30;
    last = now;
    frame(dt);
  };
  const start = (): void => { if (loaded && !raf && !document.hidden && !lost && !disposed) { last = 0; due = 0; raf = requestAnimationFrame(tick); } };
  const stop = (): void => { cancelAnimationFrame(raf); raf = 0; };
  const onVis = (): void => (document.hidden ? stop() : start());
  const onRestored = (): void => { lost = false; start(); };
  const onLostLoop = (): void => { lost = true; stop(); };

  // ---- entrada: mirada, tacto sobre las hebras, viento por velocidad, zonas bajo el cursor, arrastre para girar y clic ----
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
  const onMq = (): void => { if (opts.reducedMotion === undefined && mq) layer.setReducedMotion(mq.matches); };
  addEventListener('pointermove', onMove); document.documentElement.addEventListener('pointerleave', onLeave);
  canvas.addEventListener('pointerdown', onDown); canvas.addEventListener('pointerup', onUp); canvas.addEventListener('pointercancel', onUp);
  canvas.style.touchAction = 'none';
  document.addEventListener('visibilitychange', onVis); canvas.addEventListener('webglcontextlost', onLostLoop); canvas.addEventListener('webglcontextrestored', onRestored);
  mq?.addEventListener('change', onMq);

  const ready = layer.ready.then(() => { if (disposed) return; loaded = true; start(); });

  return {
    ready,
    setState: layer.setState, setAudioLevel: layer.setAudioLevel, setViseme: (v) => layer.setViseme?.(v),
    lookAt: layer.lookAt, notify: layer.notify, setReducedMotion: layer.setReducedMotion, setTheme: layer.setTheme,
    resize: (w, h) => { if (w > 0 && h > 0) { size = { w, h }; fit(); if (loaded && !raf) frame(0); } },
    dispose: () => {
      disposed = true; stop(); mq?.removeEventListener('change', onMq);
      removeEventListener('pointermove', onMove); document.documentElement.removeEventListener('pointerleave', onLeave);
      canvas.removeEventListener('pointerdown', onDown); canvas.removeEventListener('pointerup', onUp); canvas.removeEventListener('pointercancel', onUp);
      document.removeEventListener('visibilitychange', onVis); canvas.removeEventListener('webglcontextlost', onLostLoop); canvas.removeEventListener('webglcontextrestored', onRestored); canvas.removeEventListener('webglcontextlost', onLost);
      layer.dispose(); gl.dispose();
    },
  };
}
