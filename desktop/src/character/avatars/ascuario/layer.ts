// Ascuario como capa de un renderer ajeno (AvatarLayer). Es el núcleo único: createAvatar (index.ts)
// solo le pone alrededor un renderer, un bucle y la entrada de ratón.
import * as THREE from 'three';
import type { AvatarLayer, AvatarOptions, AvatarViewport } from '../types';
import { Brain, type Viseme } from './brain';
import { loadGeos } from './geos';
import { buildScene, type AvatarScene, type View } from './scene';

export interface AscuarioLayerOptions extends AvatarOptions {
  /** Micro-gestos en reposo (por defecto sí, salvo con movimiento reducido). */
  microGestures?: boolean;
  /** URL de ascuario-geo.json (geometría horneada); sin ella, se esculpe al arrancar. */
  geometryUrl?: string;
  /** Encuadre de depuración. */
  view?: View;
}

/** La capa más lo que el envoltorio necesita para la entrada de ratón y la depuración. */
export interface AscuarioLayer extends AvatarLayer {
  readonly ready: Promise<void>;
  readonly brain: Brain;
  scene(): AvatarScene | null;
  /** `lookAt` se ha llamado: el anfitrión dirige la mirada y el ratón ya no. */
  externalGaze(): boolean;
}

const TONE_MAPPING = THREE.ACESFilmicToneMapping;
const EXPOSURE = 1.15;

export function createAscuarioLayer(gl: THREE.WebGLRenderer, opts: AscuarioLayerOptions = {}): AscuarioLayer {
  if (!gl.capabilities.isWebGL2) throw new Error('webgl2-unavailable');
  const brain = new Brain();
  brain.reduced = opts.reducedMotion ?? false;
  brain.microGestures = opts.microGestures ?? !brain.reduced;
  let sc: AvatarScene | null = null, disposed = false, external = false;
  let size = { w: 1, h: 1, dpr: opts.pixelRatio ?? 1 };

  // Estado global del renderer que se toca en render() y se deja como estaba.
  const canvasSize = new THREE.Vector2(), prevViewport = new THREE.Vector4(), prevScissor = new THREE.Vector4();

  const ready = (async () => {
    const geos = await loadGeos(opts.geometryUrl);
    if (disposed) return;
    sc = buildScene(gl, geos, opts.view, opts.transparent ?? false);
    sc.resize(size.w, size.h, size.dpr);
    // El tone mapping entra en la clave del programa: se compila con el de render() para no recompilar al aparecer.
    // compileAsync crea los programas de forma síncrona; solo se espera a que el driver termine, así que el
    // estado global vuelve enseguida y no afecta a otras capas que dibujen mientras tanto.
    let compiled: Promise<unknown>;
    const prevTone = gl.toneMapping, prevExposure = gl.toneMappingExposure;
    try { gl.toneMapping = TONE_MAPPING; gl.toneMappingExposure = EXPOSURE; compiled = sc.compile(); }
    finally { gl.toneMapping = prevTone; gl.toneMappingExposure = prevExposure; }
    await compiled;
  })();

  return {
    ready, brain,
    scene: () => sc,
    externalGaze: () => external,
    setState: (s) => brain.setState(s),
    setAudioLevel: (l) => { brain.voice = Math.max(0, Math.min(1, l || 0)); },
    setViseme: (v) => { brain.viseme = v && 'AEIOUM'.includes(v[0]!.toUpperCase()) ? (v[0]!.toUpperCase() as Viseme) : v && 'BP'.includes(v[0]!.toUpperCase()) ? 'M' : null; },
    lookAt: (x, y) => { external = true; brain.cursor.x = Math.max(-1, Math.min(1, x)); brain.cursor.y = Math.max(-1, Math.min(1, y)); brain.cursor.active = true; },
    notify: (e) => brain.notify(e),
    setReducedMotion: (on) => { brain.reduced = on; brain.microGestures = opts.microGestures ?? !on; },
    resize: (w, h, dpr) => { size = { w, h, dpr }; sc?.resize(w, h, dpr); },
    render: (dt: number, vp: AvatarViewport) => {
      if (!sc || disposed || vp.width <= 0 || vp.height <= 0) return;
      if (brain.state !== 'speaking' && brain.state !== 'listening') brain.voice = 0;
      const pose = brain.update(dt);
      // Viewport en px CSS con origen abajo a la izquierda (convención de Three); el recuadro llega con origen arriba.
      gl.getSize(canvasSize); gl.getViewport(prevViewport); gl.getScissor(prevScissor);
      const prevScissorTest = gl.getScissorTest(), prevTone = gl.toneMapping, prevExposure = gl.toneMappingExposure;
      const y = canvasSize.y - vp.y - vp.height;
      try {
        gl.setViewport(vp.x, y, vp.width, vp.height); gl.setScissor(vp.x, y, vp.width, vp.height); gl.setScissorTest(true);
        gl.toneMapping = TONE_MAPPING; gl.toneMappingExposure = EXPOSURE;
        gl.clearDepth(); // solo dentro del recuadro: las capas de debajo no tapan al avatar; el color no se toca
        sc.render(pose, Math.min(dt, 0.05));
      } finally { // el renderer es compartido: aunque este fotograma falle, las demás capas lo reciben intacto
        gl.toneMapping = prevTone; gl.toneMappingExposure = prevExposure;
        gl.setViewport(prevViewport); gl.setScissor(prevScissor); gl.setScissorTest(prevScissorTest);
      }
    },
    dispose: () => { disposed = true; sc?.dispose(); sc = null; },
  };
}
