// Holo-Contorno como capa de un renderer ajeno (AvatarLayer). Es el núcleo único: createAvatar (index.ts)
// solo le pone alrededor un renderer, el bucle y la entrada de ratón. Holo-Hilo es este mismo rig con una
// `HoloVariant` que añade su trama de filamentos.
import * as THREE from 'three';
import type { AvatarLayer, AvatarOptions, AvatarViewport } from '../types';
import { Brain, type AvatarState, type ExprName, type Pose, type Zone } from './brain';
import type { DeformU } from './deform';
import { Features, HeightMap } from './features';
import { hairBuilder } from './hair';
import { LineBatch, backdrop, contourMat, depthMat, dustPoints, glowPoints, holoUniforms, setBlend, type HoloU } from './holo';
import { EYE, EYE_R, MOUTH_Y, bodySDF, frontOf, headSDF, projector, type Shell } from './sculpt';
import type { Viseme } from './voice';

export type HoloTheme = 'dark' | 'light';
export type { AvatarState, Zone };

/** Una etapa del montaje: se llama en tareas sucesivas hasta que devuelve `true`. */
export type HoloStep = () => boolean;

/** Lo que una variante recibe del rig para colgar sus piezas. */
export interface HoloRig {
  readonly U: HoloU;
  readonly head: THREE.Group;
  readonly body: THREE.Group;
  readonly scene: THREE.Scene;
  readonly brain: Brain;
}
/** Piezas que aporta una variante (Holo-Hilo: la trama de filamentos). */
export interface HoloVariantParts {
  /** Etapas de montaje que se ejecutan tras las del rig. */
  readonly steps: HoloStep[];
  /** Materiales que cambian de mezcla con el tema. */
  readonly blended: THREE.Material[];
  /** Cada fotograma, tras fijar los uniformes del rig y antes de dibujar. */
  update(pose: Pose): void;
  /** Libera lo que no cuelgue de la escena (p. ej. si se desmonta a medio montaje). */
  dispose?(): void;
}
export interface HoloVariant {
  /** Peso de las curvas de nivel (1 = contorno pleno). */
  readonly lineK?: number;
  /** Volumen de la escultura: [base, con la luz]. */
  readonly vol?: readonly [number, number];
  extend(rig: HoloRig): HoloVariantParts;
}

export interface HoloLayerOptions extends AvatarOptions {
  /** 'dark' = luz aditiva (paneles oscuros); 'light' = grabado en tinta de cobalto (paneles claros). */
  readonly theme?: HoloTheme;
  readonly variant?: HoloVariant;
}

/** La capa más lo que el envoltorio necesita para la entrada de ratón y la depuración. */
export interface HoloLayer extends AvatarLayer {
  readonly ready: Promise<void>;
  readonly brain: Brain;
  setTheme(theme: HoloTheme): void;
  /** Zona bajo (x, y) en px CSS del recuadro, o null. */
  hit(x: number, y: number): Zone | null;
  /** Centro de la cara en px CSS del recuadro. */
  faceScreen(): { x: number; y: number };
  /** `lookAt` se ha llamado: el anfitrión dirige la mirada y el ratón ya no. */
  externalGaze(): boolean;
  /** Solo depuración: fuerza una expresión (sin parpadeo). */
  expr(name: ExprName | null): void;
}

const VIS = new Set(['A', 'E', 'I', 'O', 'U', 'M', 'F', 'C', '_']);
const REST_YAW = 0.16; // tres cuartos suaves: da volumen sin perder la lectura frontal
const NECK_UP = 0.3; // el busto sube: cuello más corto, más torso de caballero
// Los shaders escriben valores de pantalla tal cual: ni tone mapping ni conversión de color.
const TONE = THREE.NoToneMapping;
const SPACE = THREE.LinearSRGBColorSpace;

function shellGeo(s: Shell): THREE.BufferGeometry {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(s.pos, 3)); g.setAttribute('normal', new THREE.BufferAttribute(s.nor, 3));
  g.setAttribute('aAO', new THREE.BufferAttribute(s.ao, 1)); g.setIndex(new THREE.BufferAttribute(s.index, 1));
  return g;
}

const nextTask = (): Promise<void> => new Promise((r) => setTimeout(r, 0));

export function createHoloLayer(gl: THREE.WebGLRenderer, opts: HoloLayerOptions = {}): HoloLayer {
  if (!gl.capabilities.isWebGL2) throw new Error('webgl2-unavailable');
  const transparent = !!opts.transparent;
  const U = holoUniforms();
  if (opts.variant?.lineK !== undefined) U.uLineK.value = opts.variant.lineK;
  if (opts.variant?.vol) U.uVol.value.set(opts.variant.vol[0], opts.variant.vol[1]);
  const scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(22, 1, 3, 20);
  const brain = new Brain(); brain.reduced = !!opts.reducedMotion; if (brain.reduced) brain.microGestures = false;
  if (!transparent) scene.add(backdrop(U));
  const root = new THREE.Group(); scene.add(root);
  const body = new THREE.Group(); root.add(body);
  const headPivot = new THREE.Group(); headPivot.position.set(0, -1.25, -0.15); root.add(headPivot);
  const head = new THREE.Group(); head.position.set(0, 1.25, 0.15); headPivot.add(head);

  const M = { headC: contourMat(U, true, 0.06, -1.64, -1.6), headD: depthMat(U, true), bodyC: contourMat(U, false, 0.065, -3.1, -1.9), bodyD: depthMat(U, false) };
  const feats = new LineBatch(U, 1.0, 2.6), hair = new LineBatch(U, 0.3, 1.1), temples = new LineBatch(U, 0.42, 1.1), beard = new LineBatch(U, 0.75, 0.35, true), suit = new LineBatch(U, 0.7, 2.0);
  hair.mat.uniforms.uTint!.value = new THREE.Color(0.85, 0.93, 1.0); hair.mat.uniforms.uTintK!.value = 0.45;
  temples.mat.uniforms.uTint!.value = new THREE.Color(1, 1, 1); temples.mat.uniforms.uTintK!.value = 0.9; temples.mesh.renderOrder = 4;
  beard.mat.uniforms.uTint!.value = new THREE.Color(0.9, 0.96, 1); beard.mat.uniforms.uTintK!.value = 0.6; beard.mesh.renderOrder = 5;
  feats.mesh.renderOrder = 5; hair.mesh.renderOrder = 4; suit.mesh.renderOrder = 4;
  const glow = glowPoints(U, 4), dust = dustPoints(U, 40);
  const extra = opts.variant?.extend({ U, head, body, scene, brain });
  const blended: THREE.Material[] = [M.headC, M.bodyC, feats.mat, hair.mat, temples.mat, beard.mat, suit.mat, glow.mat, dust.mat, ...(extra?.blended ?? [])];
  const applyTheme = (t: HoloTheme): void => { const ink = t === 'light'; U.uInk.value = ink ? 1 : 0; blended.forEach((m) => setBlend(m, ink)); };
  applyTheme(opts.theme ?? 'dark');
  const hm = new HeightMap(), features = new Features(hm);
  const pjH = projector(headSDF, [0, 0.05, 0.12], 200, 160, -1.62), pjB = projector(bodySDF, [0, -2.35, -0.1], 120, 90, -3.1);
  const hb = hairBuilder(900);
  const proxies: THREE.Mesh[] = [];

  // ── Montaje por etapas (cada una en su propia tarea: nada bloquea el hilo principal).
  const steps: HoloStep[] = [
    () => pjH.step(4),
    () => { const done = pjB.step(16); if (done) { const g = shellGeo(pjB.shell); const d = new THREE.Mesh(g, M.bodyD), c = new THREE.Mesh(g, M.bodyC); d.renderOrder = 0; c.renderOrder = 2; body.add(d, c); } return done; },
    () => { const g = shellGeo(pjH.shell); const d = new THREE.Mesh(g, M.headD), c = new THREE.Mesh(g, M.headC); d.renderOrder = 1; c.renderOrder = 3; head.add(d, c); return true; },
    () => hm.step(10),
    () => { const done = hb.step(30); if (done) { hair.set(hb.strands.filter((x) => !x.silver)); temples.set(hb.strands.filter((x) => x.silver)); head.add(hair.mesh, temples.mesh); features.seedBeard(); } return done; },
    () => { // Traje: cuello de camisa, solapas, nudo de corbata (sobre el busto, estáticos).
      const S: { pts: number[]; w: number[]; a: number[]; n: number }[] = [];
      const line = (f: (t: number) => [number, number], n: number, w: number, a: number, lift = 0.015): void => {
        const st = { pts: [] as number[], w: [] as number[], a: [] as number[], n: 0 };
        for (let i = 0; i < n; i++) { const t = i / (n - 1), [x, y] = f(t); st.pts.push(x, y, frontOf(bodySDF, x, y) + lift); st.w.push(w * (0.4 + 0.6 * Math.sin(Math.PI * (0.05 + 0.9 * t)))); st.a.push(a); st.n++; }
        S.push(st);
      };
      for (const s of [-1, 1]) {
        line((t) => [s * (0.36 - t * 0.3), -1.5 - t * 0.38], 10, 2.4, 0.85);                 // ala del cuello de camisa (borde exterior)
        line((t) => [s * (0.05 + t * 0.05), -1.86 - t * 0.04], 4, 2.0, 0.7);
        line((t) => [s * (0.1 + t * 0.26), -1.92 + t * 0.4 - t * t * 0.02], 8, 1.8, 0.6);     // ala (borde interior)
        line((t) => [s * (0.38 + t * 0.2), -1.62 - t * 0.5], 10, 2.2, 0.55);                  // cuello de la americana
        line((t) => [s * (0.58 - t * 0.1), -2.12 - t * 0.12], 5, 2.0, 0.55);                  // muesca
        line((t) => [s * (0.48 - t * 0.3), -2.24 - t * 0.8], 14, 2.6, 0.75);                  // solapa
      }
      line((t) => [-0.055 + t * 0.11, -1.86], 5, 2.6, 0.85);                                   // nudo
      line((t) => [-0.055 + t * 0.02, -1.86 - t * 0.13], 4, 2.0, 0.75); line((t) => [0.055 - t * 0.02, -1.86 - t * 0.13], 4, 2.0, 0.75);
      line((t) => [-0.035 - t * 0.06, -1.99 - t * 1.0], 12, 1.8, 0.6); line((t) => [0.035 + t * 0.06, -1.99 - t * 1.0], 12, 1.8, 0.6); // corbata
      suit.set(S); body.add(suit.mesh); return true;
    },
    () => { // Rasgos (primer cálculo) y zonas de interacción.
      head.add(feats.mesh, beard.mesh); scene.add(glow.pts, dust.pts);
      const hidden = new THREE.MeshBasicMaterial({ visible: false });
      const px = (g: THREE.BufferGeometry, parent: THREE.Object3D, pos: [number, number, number], zone: Zone): void => { const m = new THREE.Mesh(g, hidden); m.position.set(...pos); m.userData.zone = zone; parent.add(m); proxies.push(m); };
      for (const s of [-1, 1]) { px(new THREE.SphereGeometry(0.15, 8, 6), head, [s * 0.74, -0.1, -0.12], 'crown'); px(new THREE.SphereGeometry(0.13, 8, 6), head, [s * EYE[0], EYE[1], EYE[2] + 0.1], 'eye'); }
      px(new THREE.BoxGeometry(0.5, 0.2, 0.2), head, [0, MOUTH_Y, 0.95], 'mouth');
      px(new THREE.SphereGeometry(0.3, 10, 8).scale(1.4, 0.7, 0.6), head, [0, 0.45, 0.75], 'movement');
      px(new THREE.SphereGeometry(0.75, 12, 8).scale(1, 0.6, 0.7), head, [0, 0.85, -0.1], 'halo');
      px(new THREE.SphereGeometry(0.5, 10, 8).scale(1.3, 1, 0.6), body, [0, -2.25, 0.3], 'chest');
      px(new THREE.SphereGeometry(1, 16, 12).scale(0.78, 1.15, 0.95), head, [0, -0.05, 0.0], 'face');
      return true;
    },
    ...(extra?.steps ?? []),
  ];

  // ── Encuadre y fotograma.
  let W = 1, Hh = 1, pr = opts.pixelRatio ?? 1, ready = false, disposed = false, external = false;
  let lastFeat = '', lastBeard = '', lastGlow = '';
  const REST_DU: DeformU = { jaw: 0, smL: 0, smR: 0, lipW: 0, round: 0, liftL: 0, liftR: 0 };
  const du: DeformU = { jaw: 0, smL: 0, smR: 0, lipW: 0, round: 0, liftL: 0, liftR: 0 };
  const v3 = new THREE.Vector3(), headWorld = new THREE.Vector3(), accent = new THREE.Color(), tc = new THREE.Color();
  const fit = (): void => {
    const fitH = 3.95, fitW = 3.2, tan = Math.tan(THREE.MathUtils.degToRad(cam.fov / 2)), dist = Math.max(fitH / 2, fitW / 2 / (W / Hh)) / tan;
    cam.aspect = W / Hh; cam.position.set(0, -0.42, dist); cam.lookAt(0, -0.42, 0); cam.near = dist - 4; cam.far = dist + 4; cam.updateProjectionMatrix();
    U.uRes.value.set(W * pr, Hh * pr); U.uPx.value = (Hh * pr) / 600; glow.mat.uniforms.uScale!.value = dust.mat.uniforms.uScale!.value = (Hh * pr) / (2 * tan);
  };
  fit();
  const glowSet = (i: number, p: THREE.Vector3, c: THREE.Color, k: number, size: number): void => { glow.pos.set([p.x, p.y, p.z], i * 3); glow.col.set([c.r * k, c.g * k, c.b * k], i * 3); glow.size[i] = size; };

  function pose(p: Pose): void {
    const f = p.face, g = Math.min(1.3, p.glow), cold = p.cold;
    accent.setRGB(p.accent[0], p.accent[1], p.accent[2]);
    U.uT.value = p.t; U.uGlow.value = 0.75 + 0.25 * g; U.uCold.value = cold; U.uAccent.value.copy(accent);
    U.uWarm.value = p.state === 'success' ? Math.min(1, p.st * 2) * 0.6 : f.blush * 0.35;
    U.uJaw.value = f.jaw; U.uSmL.value = f.smL; U.uSmR.value = f.smR; U.uLipW.value = f.w; U.uRound.value = f.rnd; U.uLiftL.value = f.lL; U.uLiftR.value = f.lR;
    // Escáner: barrido descendente; más rápido al pensar y al ejecutar, apagado sin conexión.
    const sp = p.state === 'thinking' ? 0.55 : p.state === 'executing' ? 0.9 : p.state === 'listening' ? 0.3 : 0.2;
    U.uScan.value = 1.4 - ((p.t * sp) % 1) * 4.6; U.uScanK.value = (p.state === 'offline' ? 0 : p.state === 'thinking' || p.state === 'executing' ? 0.85 : 0.4) * (brain.reduced ? 0.3 : 1);
    body.position.set(0, NECK_UP + p.breath * 0.014 - 0.007 + p.shrug * 0.025, p.lean * 0.03); body.rotation.y = p.yaw * 0.15 + REST_YAW * 0.35; body.scale.set(1 + p.breath * 0.006, 1, 1);
    headPivot.position.set(0, -1.25 + p.rise + p.shrug * 0.015, -0.15 + p.lean * 0.12); headPivot.rotation.set(p.pitch, p.yaw + REST_YAW, p.roll, 'YXZ');
    extra?.update(p);
    // Rasgos: solo se recalcula lo que cambia (en reposo, la cara está quieta casi todo el tiempo).
    du.jaw = f.jaw; du.smL = f.smL; du.smR = f.smR; du.lipW = f.w; du.round = f.rnd; du.liftL = f.lL; du.liftR = f.lR;
    const q = (v: number): number => Math.round(v * 160); // 1/160: décimas de píxel
    let kf = `${q(f.jaw)},${q(f.smL)},${q(f.smR)},${q(f.w)},${q(f.rnd)},${q(f.lL)},${q(f.lR)}`;
    for (const k of ['bAL', 'bAR', 'furrow', 'uL', 'uR', 'dL', 'dR', 'tL', 'tR', 'pupil'] as const) kf += ',' + q(f[k]);
    kf += `,${q(p.gx)},${q(p.gy)},${q(p.pupilL)},${q(p.pupilR)}`;
    if (kf !== lastFeat) { lastFeat = kf; feats.set(features.build({ f, gx: p.gx, gy: p.gy, pupilL: p.pupilL, pupilR: p.pupilR }, du)); }
    if (!lastBeard) { lastBeard = 'rest'; beard.set(features.buildBeard(REST_DU)); } // la GPU la deforma con la piel
    root.updateMatrixWorld(true);
    // Brillos: pupilas y destellos (si el ojo está abierto); el polvo de luz se anima en la GPU.
    let gi = 0;
    for (const s of [-1, 1]) {
      const up = s < 0 ? f.uL : f.uR, open = Math.max(0, 1 - up * 1.05) * (1 - cold);
      const ix = s * EYE[0] + p.gx * 0.05, iy = EYE[1] - p.gy * 0.035 - 0.004, dx = ix - s * EYE[0], dy = iy - EYE[1];
      v3.set(ix, iy, EYE[2] + Math.sqrt(Math.max(0, (EYE_R + 0.01) ** 2 - dx * dx - dy * dy))).applyMatrix4(head.matrixWorld);
      tc.copy(accent).lerp(U.uWhite.value, 0.5); glowSet(gi++, v3, tc, 0.85 * open * g, 0.11 * (s < 0 ? p.pupilL : p.pupilR));
      v3.set(ix - 0.018, iy + 0.02, EYE[2] + EYE_R + 0.012).applyMatrix4(head.matrixWorld); glowSet(gi++, v3, U.uWhite.value, 0.9 * open, 0.035);
    }
    dust.mat.uniforms.uK!.value = brain.reduced ? 0.4 : 1;
    // Las pupilas solo se suben si se han movido de verdad.
    let gk = ''; for (let i = 0; i < 12; i++) gk += Math.round(glow.pos[i]! * 2000) + ',';
    for (let i = 0; i < 12; i++) gk += Math.round(glow.col[i]! * 200) + ',';
    if (gk !== lastGlow) { lastGlow = gk; for (const n of ['position', 'aCol', 'aSize']) (glow.pts.geometry.attributes[n] as THREE.BufferAttribute).needsUpdate = true; }
    head.getWorldPosition(headWorld);
  }

  // Estado global del renderer que se toca al dibujar y se deja como estaba (el renderer puede ser compartido).
  const canvasSize = new THREE.Vector2(), prevViewport = new THREE.Vector4(), prevScissor = new THREE.Vector4();
  function withState<T>(fn: () => T): T {
    const prevTone = gl.toneMapping, prevSpace = gl.outputColorSpace, prevAuto = gl.autoClear;
    try { gl.toneMapping = TONE; gl.outputColorSpace = SPACE; gl.autoClear = false; return fn(); }
    finally { gl.toneMapping = prevTone; gl.outputColorSpace = prevSpace; gl.autoClear = prevAuto; }
  }

  const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
  const hit = (x: number, y: number): Zone | null => {
    if (!ready) return null;
    ndc.set((x / W) * 2 - 1, -(y / Hh) * 2 + 1); ray.setFromCamera(ndc, cam);
    for (const m of proxies) if (ray.intersectObject(m, false).length) return m.userData.zone as Zone;
    return null;
  };

  const readyP = (async () => {
    await nextTask(); // el primer paso nunca en la misma tarea que la creación
    for (const s of steps) {
      let done = false;
      while (!done) { if (disposed) return; done = s(); await nextTask(); }
    }
    if (disposed) return;
    // El tone mapping y el espacio de color entran en la clave del programa: se compila con los de render().
    // compileAsync crea los programas de forma síncrona y luego solo espera al driver, así que el estado
    // global vuelve enseguida. Nada de render() antes: compilaría de forma síncrona.
    await withState(() => gl.compileAsync(scene, cam)).catch(() => undefined); // si falla, render() compila
    if (!disposed) ready = true;
  })();

  return {
    ready: readyP, brain, hit,
    externalGaze: () => external,
    faceScreen: () => { v3.copy(headWorld).project(cam); return { x: (v3.x * 0.5 + 0.5) * W, y: (-v3.y * 0.5 + 0.5) * Hh }; },
    expr: (n) => { brain.exprOverride = n; },
    setState: (s) => brain.setState(s),
    setAudioLevel: (l) => { brain.voice = Math.max(0, Math.min(1, l || 0)); },
    setViseme: (v) => { brain.viseme = v && VIS.has(v.toUpperCase()) ? (v.toUpperCase() as Viseme) : null; },
    lookAt: (x, y) => { external = true; brain.cursor.x = Math.max(-1, Math.min(1, x)); brain.cursor.y = Math.max(-1, Math.min(1, y)); brain.cursor.active = true; },
    notify: (e) => brain.notify(e),
    setReducedMotion: (on) => { brain.reduced = on; brain.microGestures = !on; },
    setTheme: (t) => applyTheme(t),
    resize: (w, h, dpr) => { W = Math.max(1, w); Hh = Math.max(1, h); pr = dpr > 0 ? dpr : 1; fit(); },
    render: (dt: number, vp: AvatarViewport) => {
      if (!ready || disposed || vp.width <= 0 || vp.height <= 0) return;
      if (brain.state !== 'speaking' && brain.state !== 'listening') brain.voice = 0;
      pose(brain.update(Math.min(dt, 0.1)));
      // Viewport en px CSS con origen abajo a la izquierda (convención de Three); el recuadro llega con origen arriba.
      gl.getSize(canvasSize); gl.getViewport(prevViewport); gl.getScissor(prevScissor);
      const prevScissorTest = gl.getScissorTest(), y = canvasSize.y - vp.y - vp.height;
      withState(() => {
        try {
          gl.setViewport(vp.x, y, vp.width, vp.height); gl.setScissor(vp.x, y, vp.width, vp.height); gl.setScissorTest(true);
          gl.clearDepth(); // solo dentro del recuadro: la prepasada de profundidad es nuestra; el color no se toca
          gl.render(scene, cam);
        } finally { gl.setViewport(prevViewport); gl.setScissor(prevScissor); gl.setScissorTest(prevScissorTest); }
      });
    },
    dispose: () => {
      disposed = true; ready = false;
      const mats = new Set<THREE.Material>();
      scene.traverse((o) => { const m = o as THREE.Mesh; if (m.geometry) m.geometry.dispose(); if (m.material) (Array.isArray(m.material) ? m.material : [m.material]).forEach((x) => mats.add(x)); });
      // Lo que aún no se había colgado de la escena (montaje a medias).
      for (const b of [feats, hair, temples, beard, suit]) { b.geo.dispose(); mats.add(b.mat); }
      glow.pts.geometry.dispose(); dust.pts.geometry.dispose(); extra?.dispose?.();
      blended.forEach((m) => mats.add(m)); Object.values(M).forEach((m) => mats.add(m));
      mats.forEach((m) => m.dispose());
    },
  };
}
