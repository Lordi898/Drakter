// Holo-Contorno con lienzo propio (modo Drakter). Envoltorio de la capa (layer.ts): pone el renderer, el
// bucle a 30 fps y la entrada de ratón. Foco, blur y escritura los avisa el anfitrión con notify().
import * as THREE from 'three';
import type { Avatar3D } from '../types';
import { createHoloLayer, type HoloLayerOptions, type HoloTheme, type Zone } from './layer';

export interface HoloAvatarOptions extends HoloLayerOptions {
  /** Límite de fotogramas (30 por defecto; 0 = sin límite). */
  readonly fps?: number;
  /** Sin MSAA por defecto: las líneas llevan su propio suavizado. */
  readonly antialias?: boolean;
}

export interface HoloAvatar extends Avatar3D {
  readonly ready: Promise<void>;
  setTheme(theme: HoloTheme): void;
  /** Utilidades de depuración y medida; no forman parte del contrato. */
  readonly debug: {
    stats(): { fps: number; ms: number; total: number; work: number; janks: number; running: boolean; calls: number; startMs: number };
    reset(): void; setFps(n: number): void; click(z: Zone): void;
  };
}

export function createHoloAvatar(canvas: HTMLCanvasElement, opts: HoloAvatarOptions = {}): HoloAvatar {
  const t0 = performance.now();
  const transparent = !!opts.transparent;
  const gl = new THREE.WebGLRenderer({ canvas, antialias: opts.antialias ?? false, alpha: transparent, premultipliedAlpha: true, powerPreference: 'low-power', stencil: false });
  if (!gl.capabilities.isWebGL2) { gl.dispose(); throw new Error('webgl2-unavailable'); }
  gl.debug.checkShaderErrors = import.meta.env.DEV; // en producción, sin lecturas síncronas del estado de los shaders
  gl.toneMapping = THREE.NoToneMapping; gl.outputColorSpace = THREE.LinearSRGBColorSpace;
  gl.setClearColor(0x01040b, transparent ? 0 : 1); gl.autoClear = false; // limpia el envoltorio; la capa nunca
  canvas.style.opacity = '0'; canvas.style.transition = 'opacity .6s ease-out';

  const dpr = opts.pixelRatio ?? 1;
  let size = { w: canvas.clientWidth || 500, h: canvas.clientHeight || 600 };
  const L = (() => { try { return createHoloLayer(gl, { ...opts, pixelRatio: dpr }); } catch (e) { gl.dispose(); throw e; } })();
  const { brain } = L;
  const fit = (): void => { gl.setPixelRatio(dpr); gl.setSize(size.w, size.h, false); L.resize(size.w, size.h, dpr); };
  fit();

  // ── Bucle (30 fps; parado con la pestaña oculta o tras dispose).
  let raf = 0, last = 0, due = 0, cap = opts.fps ?? 30, total = 0, work = 0, janks = 0, winStart = 0, winFrames = 0, winWork = 0, fps = 0, ms = 0;
  let loaded = false, disposed = false, startMs = 0, px = -1, py = -1, hoverAt = 0;
  const tick = (now: number): void => {
    raf = requestAnimationFrame(tick);
    if (cap > 0) { // limitador por calendario: tolera el temblor del compositor sin perder la media de 30
      const iv = 1000 / cap;
      if (now < due - iv * 0.45) return;
      due = now - due > iv ? now + iv : due + iv;
    }
    const dt = last ? (now - last) / 1000 : 1 / 30; if (last && now - last > 50) janks++; last = now;
    const a = performance.now();
    if (px >= 0 && now - hoverAt > 150) { hoverAt = now; const z = L.hit(px, py); if (z !== brain.hover) { brain.hover = z; canvas.style.cursor = z ? 'pointer' : ''; } }
    gl.clear();
    L.render(dt, { x: 0, y: 0, width: size.w, height: size.h });
    const w = performance.now() - a; total++; work += w; winFrames++; winWork += w;
    if (now - winStart >= 500) { fps = (winFrames * 1000) / (now - winStart); ms = winWork / winFrames; winStart = now; winFrames = 0; winWork = 0; }
  };
  const start = (): void => { if (loaded && !raf && !document.hidden && !disposed) { last = 0; due = 0; winStart = performance.now(); raf = requestAnimationFrame(tick); } };
  const stop = (): void => { cancelAnimationFrame(raf); raf = 0; };
  const onVis = (): void => (document.hidden ? stop() : start());

  // ── Entrada.
  const onMove = (e: PointerEvent): void => {
    const b = canvas.getBoundingClientRect();
    if (!L.externalGaze()) { const fs = L.faceScreen(), half = Math.max(b.width, b.height) * 0.55; brain.cursor.x = Math.max(-1, Math.min(1, (e.clientX - b.left - fs.x) / half)); brain.cursor.y = Math.max(-1, Math.min(1, (e.clientY - b.top - fs.y) / half)); brain.cursor.active = true; }
    const x = e.clientX - b.left, y = e.clientY - b.top;
    if (x >= 0 && y >= 0 && x <= b.width && y <= b.height) { px = x; py = y; } else if (px >= 0) { px = -1; brain.hover = null; canvas.style.cursor = ''; }
    brain.poke();
  };
  const onLeave = (): void => { if (!L.externalGaze()) brain.cursor.active = false; px = -1; brain.hover = null; };
  const onDown = (e: PointerEvent): void => { const b = canvas.getBoundingClientRect(), z = L.hit(e.clientX - b.left, e.clientY - b.top); if (z) brain.click(z); else brain.poke(); };
  const onLost = (e: Event): void => e.preventDefault();
  addEventListener('pointermove', onMove); document.documentElement.addEventListener('pointerleave', onLeave);
  canvas.addEventListener('pointerdown', onDown); canvas.addEventListener('webglcontextlost', onLost);
  document.addEventListener('visibilitychange', onVis);

  const ready = L.ready.then(() => {
    if (disposed) return;
    loaded = true; startMs = performance.now() - t0;
    canvas.style.opacity = '1';
    start();
  });

  return {
    ready,
    setState: L.setState,
    setAudioLevel: L.setAudioLevel,
    setViseme: (v) => L.setViseme?.(v),
    lookAt: L.lookAt,
    notify: L.notify,
    setReducedMotion: L.setReducedMotion,
    setTheme: L.setTheme,
    resize: (w, h) => { size = { w: Math.max(1, w), h: Math.max(1, h) }; fit(); },
    dispose: () => {
      disposed = true; stop();
      removeEventListener('pointermove', onMove); document.documentElement.removeEventListener('pointerleave', onLeave);
      canvas.removeEventListener('pointerdown', onDown); canvas.removeEventListener('webglcontextlost', onLost);
      document.removeEventListener('visibilitychange', onVis);
      L.dispose(); gl.dispose();
    },
    debug: {
      stats: () => ({ fps, ms, total, work, janks, running: raf !== 0, calls: gl.info.render.calls, startMs }),
      reset: () => { total = 0; work = 0; janks = 0; },
      setFps: (n) => { cap = n; }, click: (z) => brain.click(z),
    },
  };
}
