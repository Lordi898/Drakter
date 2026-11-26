// Holo-Orbe como capa de un renderer ajeno (AvatarLayer). Es el núcleo único: createAvatar (index.ts)
// solo le pone alrededor un renderer, un bucle y la entrada de ratón (tacto, arrastre y clics).
import * as THREE from 'three';
import type { AvatarLayer, AvatarOptions, AvatarViewport } from '../types';
import { Brain, type Vowel } from './brain';
import { createScene, type AvatarRenderer } from './render';

/** Tejido por fotograma mientras nace: nunca bloquea el hilo principal. */
const WEAVE_MS = 8;

/** La capa más lo que el envoltorio necesita para la entrada de ratón y la depuración. */
export interface HoloOrbeLayer extends AvatarLayer {
  readonly ready: Promise<void>;
  readonly brain: Brain;
  readonly scene: AvatarRenderer;
  /** `lookAt` se ha llamado: el anfitrión dirige la mirada y el ratón ya no. */
  externalGaze(): boolean;
  /** ms desde la creación hasta terminar de tejer (0 mientras teje). */
  readyMs(): number;
}

export function createHoloOrbeLayer(gl: THREE.WebGLRenderer, opts: AvatarOptions = {}): HoloOrbeLayer {
  const t0 = performance.now();
  const scene = createScene(gl, opts.transparent === true), brain = new Brain();
  const setReduced = (on: boolean): void => { brain.reduced = on; brain.microGestures = !on; };
  setReduced(opts.reducedMotion ?? false);
  scene.theme(opts.theme === 'light');
  let disposed = false, external = false, readyMs = 0, size = { w: 1, h: 1, dpr: opts.pixelRatio ?? 1 };
  scene.resize(size.w, size.h, size.dpr);

  // Estado global del renderer que se toca en render() y se deja como estaba.
  const canvasSize = new THREE.Vector2(), prevViewport = new THREE.Vector4(), prevScissor = new THREE.Vector4();

  // Búferes y shaders en tareas separadas (nada de bloqueos largos); el tejido sigue después, por tandas, en render().
  const ready = new Promise<void>((resolve, reject) => {
    setTimeout(() => {
      if (disposed) return resolve();
      try { scene.init(); } catch (reason) { return reject(reason); }
      scene.compile().then(resolve, reject);
    }, 0);
  });

  return {
    ready, brain, scene,
    externalGaze: () => external,
    readyMs: () => readyMs,
    setState: (s) => brain.setState(s),
    setAudioLevel: (level) => { brain.voice = Math.max(0, Math.min(1, level || 0)); },
    setViseme: (v) => { const k = v ? v.toLowerCase() : null; brain.viseme = k === null ? null : k.length === 1 && 'aeiou'.includes(k) ? (k as Vowel) : 'm'; },
    lookAt: (x, y) => { external = true; brain.cursor.x = Math.max(-1, Math.min(1, x)); brain.cursor.y = Math.max(-1, Math.min(1, y)); brain.cursor.active = true; },
    notify: (e) => brain.notify(e),
    setReducedMotion: setReduced,
    setTheme: (theme) => scene.theme(theme === 'light'),
    resize: (w, h, dpr) => { if (w > 0 && h > 0) { size = { w, h, dpr }; scene.resize(w, h, dpr); } },
    render: (dt: number, vp: AvatarViewport) => {
      if (disposed || vp.width <= 0 || vp.height <= 0) return;
      if (brain.weaving && scene.weave(WEAVE_MS)) { brain.weaving = false; readyMs = performance.now() - t0; }
      if (!brain.drag.active) { const k = Math.exp(-Math.min(dt, 0.05) * 3.2); brain.drag.yaw *= k; brain.drag.pitch *= k; } // al soltar, vuelve a su sitio
      const pose = brain.update(dt);
      // Viewport en px CSS con origen abajo a la izquierda (convención de Three); el recuadro llega con origen arriba.
      gl.getSize(canvasSize); gl.getViewport(prevViewport); gl.getScissor(prevScissor);
      const prevScissorTest = gl.getScissorTest(), y = canvasSize.y - vp.y - vp.height, ratio = gl.getPixelRatio();
      try {
        gl.setViewport(vp.x, y, vp.width, vp.height); gl.setScissor(vp.x, y, vp.width, vp.height); gl.setScissorTest(true);
        scene.setOrigin(vp.x * ratio, y * ratio);
        gl.clearDepth(); // solo dentro del recuadro: las capas de debajo no tapan al holograma; el color no se toca
        scene.render(pose, Math.min(dt, 0.05));
      } finally { // el renderer es compartido: aunque este fotograma falle, las demás capas lo reciben intacto
        gl.setViewport(prevViewport); gl.setScissor(prevScissor); gl.setScissorTest(prevScissorTest);
      }
    },
    dispose: () => { disposed = true; scene.dispose(); },
  };
}
