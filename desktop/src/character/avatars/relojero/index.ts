// El Relojero v2 — módulo ES del avatar para el lienzo propio (modo Drakter). createAvatar es un envoltorio de
// la capa (layer.ts): pone el renderer, el bucle (30 fps con limitador por calendario) y la entrada de ratón.
import * as THREE from 'three';
import type { Avatar3D } from '../types';
import { createRelojeroLayer, type RelojeroOptions } from './layer';

export type { RelojeroOptions };
export type Relojero = Avatar3D & { readonly ready: Promise<void> };

export function createAvatar(canvas: HTMLCanvasElement, opts: RelojeroOptions = {}): Relojero {
  const gl = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'low-power', alpha: opts.transparent === true, premultipliedAlpha: true, stencil: false });
  if (!gl.capabilities.isWebGL2) { gl.dispose(); throw new Error('webgl2-unavailable'); }
  gl.setClearColor(opts.transparent === true ? 0x000000 : 0x05070d, opts.transparent === true ? 0 : 1); gl.autoClear = false; // limpia el envoltorio; la capa nunca
  const onLost = (e: Event): void => e.preventDefault();
  canvas.addEventListener('webglcontextlost', onLost);

  const mq = typeof matchMedia === 'function' ? matchMedia('(prefers-reduced-motion: reduce)') : null;
  const dpr = opts.pixelRatio ?? 1;
  let size = { w: canvas.clientWidth || 500, h: canvas.clientHeight || 600 };
  const layer = createRelojeroLayer(gl, { ...opts, reducedMotion: opts.reducedMotion ?? mq?.matches ?? false, pixelRatio: dpr });
  const { brain } = layer;
  const fit = (): void => { gl.setPixelRatio(dpr); gl.setSize(size.w, size.h, false); layer.resize(size.w, size.h, dpr); };
  fit();
  let disposed = false, loaded = false;

  // ---- bucle: 30 fps con limitador por calendario; se detiene del todo cuando la página no se ve ----
  let raf = 0, last = 0, due = 0, px = -1, py = -1, hoverAt = 0;
  const frame = (dt: number): void => { gl.clear(); layer.render(dt, { x: 0, y: 0, width: size.w, height: size.h }); };
  const tick = (now: number): void => {
    raf = requestAnimationFrame(tick);
    const iv = 1000 / 30; if (now < due - 2) return; due = now - due > iv ? now + iv : due + iv;
    const dt = last ? (now - last) / 1000 : 1 / 30;
    last = now;
    if (px >= 0 && now - hoverAt > 150) { hoverAt = now; brain.hover = layer.hit(px, py); }
    frame(dt);
  };
  const start = (): void => { if (loaded && !raf && !document.hidden && !disposed) { last = 0; due = 0; raf = requestAnimationFrame(tick); } };
  const stop = (): void => { cancelAnimationFrame(raf); raf = 0; };
  const onVis = (): void => (document.hidden ? stop() : start());

  // ---- entrada: mirada, zonas bajo el cursor y clic. Foco, blur y escritura los avisa el anfitrión con notify(). ----
  const onMove = (e: PointerEvent): void => {
    const b = canvas.getBoundingClientRect();
    if (!layer.externalGaze()) { const fs = layer.faceScreen(), half = Math.max(b.width, b.height) * 0.55; brain.cursor.x = Math.max(-1, Math.min(1, (e.clientX - b.left - fs.x) / half)); brain.cursor.y = Math.max(-1, Math.min(1, (e.clientY - b.top - fs.y) / half)); brain.cursor.active = true; }
    const x = e.clientX - b.left, y = e.clientY - b.top; if (x >= 0 && y >= 0 && x <= b.width && y <= b.height) { px = x; py = y; } else { px = -1; brain.hover = null; }
    brain.poke();
  };
  const onLeave = (): void => { if (!layer.externalGaze()) brain.cursor.active = false; px = -1; brain.hover = null; };
  const onDown = (e: PointerEvent): void => { const b = canvas.getBoundingClientRect(), z = layer.hit(e.clientX - b.left, e.clientY - b.top); if (z) brain.click(z); else brain.poke(); };
  const onMq = (): void => { if (opts.reducedMotion === undefined && mq) layer.setReducedMotion(mq.matches); };
  addEventListener('pointermove', onMove); document.documentElement.addEventListener('pointerleave', onLeave); canvas.addEventListener('pointerdown', onDown);
  document.addEventListener('visibilitychange', onVis); mq?.addEventListener('change', onMq);

  const ready = layer.ready.then(() => { if (disposed) return; loaded = true; start(); });

  return {
    ready,
    setState: layer.setState, setAudioLevel: layer.setAudioLevel, setViseme: (v) => layer.setViseme?.(v),
    lookAt: layer.lookAt, notify: layer.notify, setReducedMotion: layer.setReducedMotion, setTheme: layer.setTheme,
    resize: (w, h) => { if (w > 0 && h > 0) { size = { w, h }; fit(); if (loaded && !raf) frame(0); } },
    dispose: () => {
      disposed = true; stop();
      removeEventListener('pointermove', onMove); document.documentElement.removeEventListener('pointerleave', onLeave); canvas.removeEventListener('pointerdown', onDown);
      document.removeEventListener('visibilitychange', onVis); mq?.removeEventListener('change', onMq); canvas.removeEventListener('webglcontextlost', onLost);
      layer.dispose(); gl.dispose();
    },
  };
}
