// Filamento (dorado) como capa de un renderer ajeno (AvatarLayer). Es el núcleo único: createAvatar (index.ts)
// solo le pone alrededor un renderer, un bucle y la entrada de ratón.
import * as THREE from 'three';
import type { AvatarLayer, AvatarOptions, AvatarTheme, AvatarViewport } from '../types';
import { Brain, type Vowel } from './brain';
import { createRenderer, type AvatarRenderer } from './render';


export type FilamentoOptions = AvatarOptions;

/** La capa más lo que el envoltorio necesita para la entrada de ratón. */
export interface FilamentoLayer extends AvatarLayer {
  readonly ready: Promise<void>;
  readonly brain: Brain;
  readonly renderer: AvatarRenderer;
  /** `lookAt` se ha llamado: el anfitrión dirige la mirada y el ratón ya no. */
  externalGaze(): boolean;
  setTheme(theme: AvatarTheme): void;
}

export function createFilamentoLayer(gl: THREE.WebGLRenderer, opts: FilamentoOptions = {}): FilamentoLayer {
  const transparent = opts.transparent === true;
  const r = createRenderer(gl, transparent), brain = new Brain();
  const setReduced = (on: boolean): void => { brain.reduced = on; if (on) brain.microGestures = false; };
  setReduced(opts.reducedMotion ?? false);
  const setTheme = (t: AvatarTheme): void => r.setTheme(transparent && t === 'light');
  setTheme(opts.theme ?? 'dark');
  let size = { w: 0, h: 0, dpr: opts.pixelRatio ?? 1 }, disposed = false, external = false, compiled = false;
  const fit = (w: number, h: number, dpr: number): void => { if (w > 0 && h > 0) { size = { w, h, dpr }; r.resize(w, h, dpr); } };

  // Estado global del renderer que se toca en render() y se deja como estaba.
  const canvasSize = new THREE.Vector2(), prevViewport = new THREE.Vector4(), prevScissor = new THREE.Vector4();

  // Contexto, búferes y shaders en tareas separadas; el tejido sigue por tandas dentro de render().
  const ready = new Promise<void>((resolve, reject) => {
    setTimeout(() => {
      if (disposed) return resolve();
      try { r.init(); } catch (e) { return reject(e instanceof Error ? e : new Error(String(e))); }
      r.compile().then(() => { compiled = true; resolve(); }, (e: unknown) => reject(e instanceof Error ? e : new Error(String(e))));
    }, 0);
  });

  return {
    ready, brain, renderer: r,
    externalGaze: () => external,
    setState: (s) => brain.setState(s),
    setAudioLevel: (level) => { brain.voice = Math.max(0, Math.min(1, level || 0)); },
    setViseme: (v) => { const k = v ? v.toLowerCase() : null; brain.viseme = k === null ? null : 'aeiou'.includes(k) && k.length === 1 ? (k as Vowel) : 'm'; },
    lookAt: (x, y) => { external = true; brain.cursor.x = Math.max(-1, Math.min(1, x)); brain.cursor.y = Math.max(-1, Math.min(1, y)); brain.cursor.active = true; },
    notify: (e) => brain.notify(e),
    setReducedMotion: setReduced,
    setTheme,
    resize: (w, h, dpr) => fit(w, h, dpr),
    render: (dt: number, vp: AvatarViewport) => {
      if (!compiled || disposed || vp.width <= 0 || vp.height <= 0) return;
      if (vp.width !== size.w || vp.height !== size.h) fit(vp.width, vp.height, size.dpr);
      if (brain.weaving && r.weave(8)) brain.weaving = false; // 8 ms de tejido por fotograma como máximo: nunca bloquea
      if (!brain.drag.active) { const k = Math.exp(-Math.min(dt, 0.05) * 3.2); brain.drag.yaw *= k; brain.drag.pitch *= k; } // al soltar, vuelve a su sitio
      const pose = brain.update(dt);
      // Viewport en px CSS con origen abajo a la izquierda (convención de Three); el recuadro llega con origen arriba.
      gl.getSize(canvasSize); gl.getViewport(prevViewport); gl.getScissor(prevScissor);
      const prevScissorTest = gl.getScissorTest(), prevTone = gl.toneMapping;
      const y = canvasSize.y - vp.y - vp.height;
      try {
        gl.setViewport(vp.x, y, vp.width, vp.height); gl.setScissor(vp.x, y, vp.width, vp.height); gl.setScissorTest(true);
        gl.toneMapping = THREE.NoToneMapping; // sus shaders escriben valores de pantalla
        r.render(pose, Math.min(dt, 0.05), vp.x * size.dpr, y * size.dpr);
      } finally { // el renderer es compartido: aunque este fotograma falle, las demás capas lo reciben intacto
        gl.toneMapping = prevTone;
        gl.setViewport(prevViewport); gl.setScissor(prevScissor); gl.setScissorTest(prevScissorTest);
      }
    },
    dispose: () => { disposed = true; r.dispose(); },
  };
}
