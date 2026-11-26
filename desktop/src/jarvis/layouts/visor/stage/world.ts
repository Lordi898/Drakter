/**
 * Capa `visor-world` del Stage: el usuario en el centro de un cilindro de 7 sectores (rumbos).
 * Dibuja bóveda, suelo polar, horizonte, polvo, fondos de panel curvos, halo del agente y resplandor,
 * y mantiene alineado con SU cámara el DOM de los paneles (CSS3DRenderer). El CSS3D solo se reescribe
 * cuando cambia la cámara: en reposo, cero escrituras en el DOM.
 * Diseño y cifras: ~/.ao/data/artifacts/drakter-99/jarvis-visor.md · plan: ~/.local/share/drakter/plan/visor-port.md
 */
import * as THREE from 'three'
import { CSS3DObject, CSS3DRenderer } from 'three/examples/jsm/renderers/CSS3DRenderer.js'
import type { AvatarViewport } from '@/character/avatars/types'
import type { CharacterState } from '@/character/types'
import { acquireAudioTaps, readSpectrum, SPECTRUM_BANDS } from '@/voice/levels'
import type { StageAnchor, StageFrame, StageLayer } from '@/jarvis/stage/types'
import { DUST_FS, DUST_VS, FLOOR_FS, FLOOR_VS, GLOW_FS, HALO_FS, PLATE_FS, PLATE_VS, VAULT_FS } from './shaders'

export const SECTORS = 7
export const SECTOR_STEP = (Math.PI * 2) / SECTORS
const DEG = Math.PI / 180
const VFOV = 52
/** Distancia a la que 1 unidad = 1 px CSS con 1080 px de alto (la escena se diseña a 1080p y escala con la ventana). */
export const D = 1080 / 2 / Math.tan((VFOV / 2) * DEG)
export const FAR = D + 150
export const NEAR = D - 140

const ICE = new THREE.Color('#8be9ff'), CORE = new THREE.Color('#e9fcff'), AMBER = new THREE.Color('#ffb547')
const RED = new THREE.Color('#ff4b5c'), WARM = new THREE.Color('#fff1d0'), DIM = new THREE.Color('#3d5a70')
interface Look { col: THREE.Color; speed: number; dash: number; pulse: number; glitch: number; bright: number }
const LOOK: Record<CharacterState, Look> = {
  idle: { col: ICE, speed: 0.08, dash: 3, pulse: 0.25, glitch: 0, bright: 0.75 },
  listening: { col: new THREE.Color('#5fc8ff'), speed: -0.25, dash: 12, pulse: 0.5, glitch: 0, bright: 1 },
  thinking: { col: ICE, speed: 0.9, dash: 6, pulse: 0.35, glitch: 0, bright: 1 },
  speaking: { col: CORE, speed: 0.2, dash: 24, pulse: 0.7, glitch: 0, bright: 1.15 },
  executing: { col: new THREE.Color('#7fd0ff'), speed: 1.6, dash: 36, pulse: 0.4, glitch: 0, bright: 1.05 },
  success: { col: WARM, speed: 0.1, dash: 1, pulse: 1, glitch: 0, bright: 1.3 },
  error: { col: RED, speed: 0.05, dash: 9, pulse: 0.9, glitch: 1, bright: 1.1 },
  interrupted: { col: AMBER, speed: -0.6, dash: 5, pulse: 0.6, glitch: 0.5, bright: 0.95 },
  offline: { col: DIM, speed: 0.02, dash: 2, pulse: 0, glitch: 0, bright: 0.35 }
}

/** Dónde vive un panel: sector (0-6), desvío angular en grados, radio, altura y tamaño en px de diseño. */
export interface PanelSpec {
  readonly sector: number
  readonly dA?: number
  readonly R?: number
  readonly y?: number
  readonly w: number
  readonly h: number
  /** Lateral: solo se despliega en el sector enfocado (los principales se ven atenuados desde los vecinos). */
  readonly side?: boolean
  /** Opacidad del relleno (0-1); baja en paneles con 3D o avatar detrás. */
  readonly alpha?: number
  /** Panel que enmarca al avatar: su proyección es el recuadro del avatar. */
  readonly avatar?: boolean
}

interface Plate {
  readonly el: HTMLElement
  readonly obj: CSS3DObject
  readonly mesh: THREE.Mesh<THREE.BufferGeometry, THREE.ShaderMaterial>
  readonly spec: PanelSpec
  readonly angle: number
  hover: number
  hoverT: number
  flash: number
  reveal: number
  revealT: number
  dim: number
  shown: boolean
  timer: number
  readonly off: () => void
}

export interface VisorWorld extends StageLayer {
  /** Raíz DOM del CSS3D: la monta la interfaz encima del lienzo. */
  readonly cssRoot: HTMLElement
  addPanel(el: HTMLElement, spec: PanelSpec): () => void
  /** Grupo 3D anclado en un sector (para el 3D de datos de cada sector). */
  sectorGroup(sector: number, dA: number, R: number, y: number): THREE.Group
  goSector(sector: number): void
  readonly sector: number
  /** Rumbo actual de la cámara en radianes (para la cinta). */
  readonly yaw: number
  /** Parallax actual -1..1 (para la escala de elevación). */
  readonly parallax: { readonly x: number; readonly y: number }
  setAgentState(state: CharacterState): void
  /** Recuadro del avatar (proyección del panel `avatar`); vacío fuera del Núcleo. */
  avatarViewport(frame: StageFrame): AvatarViewport
  /** Despliega (o pliega) los paneles: arranque y salida. */
  setRevealed(on: boolean): void
  /** Llamada a ritmo limitado desde `update` (gráficos 2D, cinta…). Devuelve la baja. */
  onTick(fn: (frame: StageFrame) => void, hz: number): () => void
  /** Llamada en cada `update` tras mover la cámara (3D de los sectores). Devuelve la baja. */
  onFrame(fn: (frame: StageFrame) => void): () => void
  /** El rumbo actual (o el de destino, durante un giro) está a menos de `rad` del sector. */
  near(sector: number, rad?: number): boolean
  /** Proyecta un punto del mundo a px CSS; reutiliza el objeto devuelto. */
  toScreen(v: THREE.Vector3): { x: number; y: number; visible: boolean }
  /** Rayo desde la cámara por el punto de pantalla (px CSS). */
  ray(x: number, y: number): THREE.Raycaster
  /** Reposo: 8 s sin mover el puntero ni girar. El 3D de los sectores se queda quieto (cero DOM por fotograma). */
  readonly idle: boolean
  /** Escala de tamaño de los puntos (renderScale × alto / 1080). */
  readonly pointScale: number
  readonly onFirstFrame: Promise<void>
}

function plateGeometry(R: number, w: number, h: number, segs = 24): THREE.BufferGeometry {
  const half = Math.atan(w / 2 / R), pos: number[] = [], uv: number[] = [], idx: number[] = []
  for (let j = 0; j <= 1; j++)
    for (let i = 0; i <= segs; i++) {
      const t = i / segs, a = -half + t * 2 * half
      pos.push(R * Math.sin(a), (j - 0.5) * h, -R * Math.cos(a))
      uv.push(t, j)
    }
  for (let i = 0; i < segs; i++) { const a = i, b = i + 1, c = i + segs + 1, d = i + segs + 2; idx.push(a, b, d, a, d, c) }
  const g = new THREE.BufferGeometry()
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); g.setIndex(idx)
  return g
}
/** Alfa premultiplicado: el relleno oscurece, las líneas suman (brillo sin postprocesado). */
const PREMUL = { transparent: true, depthWrite: false, depthTest: false, blending: THREE.CustomBlending, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor, premultipliedAlpha: true } as const
const angDist = (a: number, b: number): number => { let d = (a - b) % (Math.PI * 2); if (d > Math.PI) d -= Math.PI * 2; if (d < -Math.PI) d += Math.PI * 2; return d }
const ease = (t: number): number => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2)

export function createVisorWorld(): VisorWorld {
  const scene = new THREE.Scene(), cssScene = new THREE.Scene()
  const cam = new THREE.PerspectiveCamera(VFOV, 16 / 9, 1, 14000); cam.rotation.order = 'YXZ'
  const css = new CSS3DRenderer()
  css.domElement.className = 'jv-visor-css'
  const cameraEl = css.domElement.firstElementChild as HTMLElement

  // ── Polvo en capas (parallax real con la traslación de la cámara)
  const NMAX = 5200, dPos = new Float32Array(NMAX * 3), dSize = new Float32Array(NMAX), dPh = new Float32Array(NMAX)
  let seed = 7
  const rnd = (): number => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646
  for (let i = 0; i < NMAX; i++) {
    const a = rnd() * Math.PI * 2, r = 1700 + Math.pow(rnd(), 0.7) * 6500, y = (rnd() - 0.5) * 4200 * (r / 5000)
    dPos.set([Math.sin(a) * r, y, -Math.cos(a) * r], i * 3); dSize[i] = 1.2 + Math.pow(rnd(), 6) * 7; dPh[i] = rnd()
  }
  const dGeo = new THREE.BufferGeometry()
  dGeo.setAttribute('position', new THREE.BufferAttribute(dPos, 3)); dGeo.setAttribute('aSize', new THREE.BufferAttribute(dSize, 1)); dGeo.setAttribute('aPh', new THREE.BufferAttribute(dPh, 1))
  const dMat = new THREE.ShaderMaterial({ vertexShader: DUST_VS, fragmentShader: DUST_FS, uniforms: { uTime: { value: 0 }, uPR: { value: 1 }, uCol: { value: new THREE.Color('#6fd6ff') }, uWarp: { value: 0 } }, ...PREMUL })
  const dust = new THREE.Points(dGeo, dMat); dust.frustumCulled = false; dust.renderOrder = 0; scene.add(dust)

  // ── Bóveda, suelo polar y horizonte
  const vaultMat = new THREE.ShaderMaterial({ vertexShader: FLOOR_VS, fragmentShader: VAULT_FS, uniforms: { uTime: { value: 0 }, uBoot: { value: 0 }, uCol: { value: new THREE.Color('#3b9cff') } }, side: THREE.BackSide, ...PREMUL })
  const vault = new THREE.Mesh(new THREE.SphereGeometry(9000, 48, 24), vaultMat); vault.renderOrder = -1; scene.add(vault)
  const fMat = new THREE.ShaderMaterial({ vertexShader: FLOOR_VS, fragmentShader: FLOOR_FS, uniforms: { uTime: { value: 0 }, uBoot: { value: 0 }, uCol: { value: new THREE.Color('#3aa6ff') } }, ...PREMUL })
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(16000, 16000), fMat); floor.rotation.x = -Math.PI / 2; floor.position.y = -760; floor.renderOrder = 1; scene.add(floor)
  const hzPts: number[] = []
  for (let i = 0; i <= 360; i++) { const a = i * DEG; hzPts.push(Math.sin(a) * 5200, -30, -Math.cos(a) * 5200) }
  const hzGeo = new THREE.BufferGeometry(); hzGeo.setAttribute('position', new THREE.Float32BufferAttribute(hzPts, 3))
  const hzMat = new THREE.LineBasicMaterial({ color: new THREE.Color('#1d6fae'), transparent: true, blending: THREE.AdditiveBlending, depthTest: false, depthWrite: false })
  const horizon = new THREE.Line(hzGeo, hzMat); horizon.renderOrder = 1; scene.add(horizon)

  const groups: { g: THREE.Group; sector: number }[] = []
  function sectorGroup(sector: number, dA: number, R: number, y: number): THREE.Group {
    const g = new THREE.Group(), a = sector * SECTOR_STEP + dA * DEG
    g.position.set(Math.sin(a) * R, y, -Math.cos(a) * R); g.rotation.y = -a; scene.add(g); groups.push({ g, sector })
    return g
  }

  // ── Halo del agente y resplandor (Núcleo)
  const spec = new Array<number>(48).fill(0)
  const haloU = { uTime: { value: 0 }, uSpeed: { value: 0.1 }, uDash: { value: 3 }, uPulse: { value: 0.3 }, uGlitch: { value: 0 }, uBright: { value: 1 }, uVoice: { value: 0 }, uProg: { value: 0 }, uFlash: { value: 0 }, uBoot: { value: 0 }, uListen: { value: 0 }, uCol: { value: ICE.clone() }, uSpec: { value: spec } }
  const haloMat = new THREE.ShaderMaterial({ vertexShader: PLATE_VS, fragmentShader: HALO_FS, uniforms: haloU, ...PREMUL })
  const halo = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), haloMat); halo.scale.setScalar(860); halo.renderOrder = 2
  const glowU = { uTime: { value: 0 }, uVoice: { value: 0 }, uBoot: { value: 0 }, uCol: { value: new THREE.Color('#2a7fe0') } }
  const glowMat = new THREE.ShaderMaterial({ vertexShader: PLATE_VS, fragmentShader: GLOW_FS, uniforms: glowU, ...PREMUL })
  const backGlow = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), glowMat); backGlow.scale.setScalar(1500); backGlow.position.z = -200; backGlow.renderOrder = 1
  const haloG = sectorGroup(0, 0, D + 140, 28); haloG.add(backGlow, halo)
  let look = LOOK.idle, state: CharacterState = 'idle'
  const haloCol = ICE.clone()

  // ── Paneles
  const plates: Plate[] = []
  function addPanel(el: HTMLElement, s: PanelSpec): () => void {
    const R = s.R ?? D, angle = s.sector * SECTOR_STEP + (s.dA ?? 0) * DEG, y = s.y ?? 0
    el.style.width = `${s.w}px`; el.style.height = `${s.h}px`
    el.classList.add('jv-visor-pnl'); if (s.side) el.classList.add('side')
    const obj = new CSS3DObject(el); cameraEl.appendChild(el) // el CSS3D lo reparentaría en el primer render; así ya existe en el DOM
    const Rc = R * Math.cos(Math.atan(s.w / 2 / R))
    obj.position.set(Math.sin(angle) * Rc, y, -Math.cos(angle) * Rc); obj.rotation.y = -angle; cssScene.add(obj)
    const u = { uSize: { value: new THREE.Vector2(s.w, s.h) }, uTime: { value: 0 }, uHover: { value: 0 }, uFlash: { value: 0 }, uReveal: { value: 0 }, uSeed: { value: (plates.length * 0.618) % 1 }, uAlpha: { value: s.alpha ?? 1 }, uFov: { value: 0 }, uDim: { value: 1 }, uSheen: { value: 0.5 }, uCol: { value: ICE.clone() }, uWarn: { value: AMBER.clone() } }
    const mesh = new THREE.Mesh(plateGeometry(R, s.w * (R / Rc), s.h), new THREE.ShaderMaterial({ vertexShader: PLATE_VS, fragmentShader: PLATE_FS, uniforms: u, ...PREMUL }))
    mesh.rotation.y = -angle; mesh.position.y = y; mesh.renderOrder = 3; scene.add(mesh)
    const enter = (): void => { p.hoverT = 1 }, leave = (): void => { p.hoverT = 0 }, down = (): void => { p.flash = 1 }
    el.addEventListener('pointerenter', enter); el.addEventListener('pointerleave', leave); el.addEventListener('pointerdown', down)
    const p: Plate = {
      el, obj, mesh, spec: s, angle, hover: 0, hoverT: 0, flash: 0, reveal: 0, revealT: 0, dim: 1, shown: false, timer: 0,
      off: () => { el.removeEventListener('pointerenter', enter); el.removeEventListener('pointerleave', leave); el.removeEventListener('pointerdown', down) }
    }
    plates.push(p); cssDirty = true; schedule()
    return () => {
      const i = plates.indexOf(p); if (i >= 0) plates.splice(i, 1)
      clearTimeout(p.timer); p.off(); cssScene.remove(obj); scene.remove(mesh); mesh.geometry.dispose(); mesh.material.dispose(); el.remove()
    }
  }

  // ── Cámara y despliegue
  const rig = { yaw: 0, from: 0, to: 0, t: 1, dur: 1.1, mx: 0, my: 0, dolly: 0, fovKick: 0, boot: 0, bootT: 0 }
  let sector = 0, revealed = false, reduced = false, time = 0, cssDirty = true,  firstFrame: (() => void) | null = null
  const onFirstFrame = new Promise<void>((r) => { firstFrame = r })

  /** Despliega los laterales del sector enfocado y los principales de todos; pliega el resto. */
  function schedule(): void {
    for (const p of plates) {
      clearTimeout(p.timer)
      const want = revealed && (!p.spec.side || p.spec.sector === sector)
      p.dim = p.spec.sector === sector || p.spec.avatar ? 1 : 0.4
      p.el.classList.toggle('peri', p.spec.sector !== sector && !p.spec.side)
      if (!want) { p.revealT = 0; p.el.classList.remove('on'); continue }
      const delay = reduced ? 0 : 120 + Math.abs(angDist(p.angle, sector * SECTOR_STEP)) * 900 + (p.spec.y !== undefined && p.spec.y < -200 ? 160 : 0)
      p.timer = window.setTimeout(() => { p.revealT = 1; p.timer = window.setTimeout(() => p.el.classList.add('on'), reduced ? 0 : 200) }, delay)
    }
  }
  function goSector(i: number): void {
    i = ((i % SECTORS) + SECTORS) % SECTORS
    if (i === sector && rig.t >= 1) return
    const d = angDist(i * SECTOR_STEP, rig.yaw)
    rig.from = rig.yaw; rig.to = rig.yaw + d; rig.t = reduced ? 1 : 0; rig.dur = 0.65 + (Math.abs(d) / Math.PI) * 0.7
    if (reduced) rig.yaw = rig.to
    sector = i; schedule()
  }

  // ── Voz real (espectro de salida al hablar, de entrada al escuchar)
  const bins = new Uint8Array(SPECTRUM_BANDS)
  let releaseTaps: (() => void) | null = null
  const ticks = new Set<{ fn: (f: StageFrame) => void; iv: number; last: number }>()
  const frames = new Set<(f: StageFrame) => void>()
  const screen = { x: 0, y: 0, visible: false }, caster = new THREE.Raycaster(), ndc = new THREE.Vector2()
  let pointScale = 1, lastMove = 0, lastPx = NaN, lastPy = NaN
  const IDLE_AFTER = 8

  const sig = new Float64Array(8).fill(NaN)
  const tv = new THREE.Vector3(), corners = [new THREE.Vector3(), new THREE.Vector3(), new THREE.Vector3(), new THREE.Vector3()]
  let W = 1, H = 1

  const layer: VisorWorld = {
    id: 'visor-world',
    order: 15,
    cssRoot: css.domElement,
    addPanel,
    sectorGroup,
    goSector,
    get sector() { return sector },
    get yaw() { return rig.yaw },
    get parallax() { return { x: rig.mx, y: rig.my } },
    setAgentState(s) {
      state = s; look = LOOK[s] ?? LOOK.idle
      if (s === 'success' || s === 'error' || s === 'interrupted') haloU.uFlash.value = 1
      haloU.uListen.value = s === 'listening' ? 1 : 0
    },
    avatarViewport(frame) {
      const av = plates.find((p) => p.spec.avatar)
      if (!av || !revealed || Math.abs(angDist(rig.yaw, av.angle)) > 0.75) return { x: 0, y: 0, width: 0, height: 0 }
      // El avatar ocupa el panel salvo la cabecera y el pie (40 px arriba, 48 abajo).
      const { w, h } = av.spec, top = h / 2 - 40, bottom = -h / 2 + 48
      corners[0]!.set(-w / 2, top, 0); corners[1]!.set(w / 2, top, 0); corners[2]!.set(-w / 2, bottom, 0); corners[3]!.set(w / 2, bottom, 0)
      av.obj.updateMatrixWorld()
      let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity
      for (const c of corners) {
        tv.copy(c).applyMatrix4(av.obj.matrixWorld).project(cam)
        const x = (tv.x * 0.5 + 0.5) * frame.width, y = (-tv.y * 0.5 + 0.5) * frame.height
        x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y)
      }
      return { x: x0, y: y0, width: Math.max(0, x1 - x0), height: Math.max(0, y1 - y0) }
    },
    setRevealed(on) { revealed = on; if (on) rig.bootT = rig.bootT || 0.0001; schedule() },
    onTick(fn, hz) { const t = { fn, iv: 1 / hz, last: -1 }; ticks.add(t); return () => { ticks.delete(t) } },
    onFrame(fn) { frames.add(fn); return () => { frames.delete(fn) } },
    near(i, rad = 1.05) { const a = i * SECTOR_STEP; return Math.abs(angDist(rig.yaw, a)) < rad || (rig.t < 1 && Math.abs(angDist(rig.to, a)) < rad) },
    toScreen(v) {
      tv.copy(v).project(cam)
      screen.x = (tv.x * 0.5 + 0.5) * W; screen.y = (-tv.y * 0.5 + 0.5) * H; screen.visible = tv.z < 1 && Math.abs(tv.x) < 1.1 && Math.abs(tv.y) < 1.1
      return screen
    },
    ray(x, y) { ndc.set((x / W) * 2 - 1, -(y / H) * 2 + 1); caster.setFromCamera(ndc, cam); return caster },
    get idle() { return time - lastMove > IDLE_AFTER },
    get pointScale() { return pointScale },
    onFirstFrame,

    async init(frame) {
      reduced = frame.reducedMotion
      releaseTaps = acquireAudioTaps()
      this.resize?.(frame)
      await frame.renderer.compileAsync(scene, cam)
    },
    resize(frame) {
      W = frame.width; H = frame.height
      cam.aspect = W / Math.max(1, H); cam.updateProjectionMatrix(); css.setSize(W, H); cssDirty = true
      const pr = frame.renderScale * (H / 1080)
      dMat.uniforms.uPR!.value = pr; pointScale = pr
    },
    setQuality(q) { dGeo.setDrawRange(0, Math.min(NMAX, q.particles)); vault.visible = q.tier !== 'ahorro' },
    update(frame) {
      const dt = Math.min(0.1, frame.dt); time = frame.time
      if (frame.reducedMotion !== reduced) { reduced = frame.reducedMotion; schedule() }
      if (W !== frame.width || H !== frame.height) this.resize?.(frame)
      // arranque: la cámara entra desde atrás y desde arriba; suelo, bóveda y halo se encienden
      if (revealed && rig.boot < 1) { rig.bootT += dt; rig.boot = reduced ? 1 : Math.min(1, rig.bootT / 2.4) }
      if (!revealed && rig.boot > 0) rig.boot = reduced ? 0 : Math.max(0, rig.boot - dt / 0.7)
      const boot = 1 - Math.pow(1 - rig.boot, 3)
      fMat.uniforms.uBoot!.value = boot; vaultMat.uniforms.uBoot!.value = boot
      haloU.uBoot.value = Math.min(1, Math.max(0, (rig.boot - 0.45) / 0.55)); glowU.uBoot.value = haloU.uBoot.value
      if (frame.pointer.x !== lastPx || frame.pointer.y !== lastPy || rig.t < 1 || !revealed) { lastPx = frame.pointer.x; lastPy = frame.pointer.y; lastMove = time }
      // viraje entre sectores con empuje de profundidad
      if (rig.t < 1) { rig.t = Math.min(1, rig.t + dt / rig.dur); const e = ease(rig.t); rig.yaw = rig.from + (rig.to - rig.from) * e; rig.dolly = Math.sin(rig.t * Math.PI) * 220; rig.fovKick = Math.sin(rig.t * Math.PI) * 7 }
      else { rig.dolly *= 0.85; rig.fovKick *= 0.85; if (Math.abs(rig.dolly) < 0.05) rig.dolly = 0; if (Math.abs(rig.fovKick) < 0.005) rig.fovKick = 0 }
      // parallax (Cine pleno, Equilibrado suave, Ahorro o reducir movimiento: quieta)
      const amp = reduced || !frame.quality.parallax ? 0 : frame.quality.tier === 'cine' ? 1 : 0.6
      const tx = frame.pointer.active ? frame.pointer.x * amp : 0, ty = frame.pointer.active ? -frame.pointer.y * amp : 0
      const k = 1 - Math.exp(-dt * 5)
      rig.mx += (tx - rig.mx) * k; rig.my += (ty - rig.my) * k
      if (Math.abs(tx - rig.mx) < 1e-4) rig.mx = tx; if (Math.abs(ty - rig.my) < 1e-4) rig.my = ty // se asienta: firma estable
      cam.position.set(rig.mx * 70, -rig.my * 42 + (1 - boot) * 120, 0)
      cam.rotation.set(-rig.my * 0.03 - (1 - boot) * 0.12, -rig.yaw - rig.mx * 0.045, 0)
      cam.translateZ(rig.dolly + (1 - boot) * 900)
      const fov = VFOV + rig.fovKick; if (Math.abs(cam.fov - fov) > 0.001) { cam.fov = fov; cam.updateProjectionMatrix() }
      // uniforms
      dMat.uniforms.uTime!.value = time; dMat.uniforms.uWarp!.value = rig.t < 1 ? Math.sin(rig.t * Math.PI) : 0
      fMat.uniforms.uTime!.value = time; vaultMat.uniforms.uTime!.value = time; glowU.uTime.value = time
      const L = (a: number, b: number): number => a + (b - a) * (1 - Math.exp(-dt * 4))
      haloCol.lerp(look.col, 1 - Math.exp(-dt * 6)); haloU.uCol.value.copy(haloCol)
      haloU.uTime.value = time; haloU.uSpeed.value = L(haloU.uSpeed.value, look.speed * (reduced ? 0.2 : 1)); haloU.uDash.value = look.dash; haloU.uPulse.value = look.pulse
      haloU.uGlitch.value = reduced ? 0 : look.glitch; haloU.uBright.value = L(haloU.uBright.value, look.bright); haloU.uFlash.value *= Math.exp(-dt * 2.2)
      haloU.uProg.value = L(haloU.uProg.value, state === 'executing' ? 0.25 + ((time * 0.35) % 0.75) : state === 'success' ? 1 : 0)
      const nearCore = Math.abs(angDist(rig.yaw, 0)) < 1.2
      if (nearCore) {
        const got = readSpectrum(state === 'listening' ? 'input' : 'output', bins)
        let sum = 0
        for (let i = 0; i < 48; i++) { const v = got ? (bins[Math.floor((i / 48) * SPECTRUM_BANDS * 0.75)] ?? 0) / 255 : 0; spec[i] = spec[i]! + (v - spec[i]!) * (1 - Math.exp(-dt * 22)); sum += spec[i]! }
        haloU.uVoice.value = sum / 48; glowU.uVoice.value = haloU.uVoice.value
      }
      // paneles
      for (const p of plates) {
        const vis = (Math.abs(angDist(p.angle, rig.yaw)) < 1.05 || (rig.t < 1 && Math.abs(angDist(p.angle, rig.to)) < 1.05)) && (p.reveal > 0.001 || p.revealT > 0)
        p.mesh.visible = vis && p.reveal > 0.001
        if (p.obj.visible !== vis) { p.obj.visible = vis; cssDirty = true }
        if (!vis && p.reveal === p.revealT) continue // fuera de vista y asentado: nada que animar
        p.hover += (p.hoverT - p.hover) * (1 - Math.exp(-dt * 12)); p.flash *= Math.exp(-dt * 4.5)
        p.reveal += (p.revealT - p.reveal) * (1 - Math.exp(-dt * (p.revealT > p.reveal ? 3.2 : 9))); if (Math.abs(p.revealT - p.reveal) < 0.002) p.reveal = p.revealT
        const u = p.mesh.material.uniforms
        u.uDim!.value += (p.dim - u.uDim!.value) * (1 - Math.exp(-dt * 5))
        u.uSheen!.value = 0.62 + angDist(p.angle, rig.yaw) * 1.6 + rig.mx * 0.45 - rig.my * 0.2
        u.uTime!.value = time; u.uHover!.value = p.hover; u.uFlash!.value = p.flash; u.uReveal!.value = p.reveal
      }
      // 3D de un sector solo si cae en el encuadre (o es el destino de un giro): los vecinos quedan fuera
      for (const { g, sector: s } of groups) g.visible = layer.near(s, 0.85)
      haloG.visible = nearCore
      cam.updateMatrixWorld()
      for (const f of frames) f(frame)
      for (const t of ticks) if (time - t.last >= t.iv) { t.last = time; t.fn(frame) }
    },
    render(frame) {
      frame.renderer.render(scene, cam)
      // CSS3D solo si cambian la cámara, la visibilidad o el tamaño: en reposo no se toca el DOM
      // sin cadenas por fotograma: se comparan los números con los del último render del CSS3D
      const p = cam.position, r = cam.rotation
      if (cssDirty || Math.abs(p.x - sig[0]!) > 0.005 || Math.abs(p.y - sig[1]!) > 0.005 || Math.abs(p.z - sig[2]!) > 0.005 || Math.abs(r.x - sig[3]!) > 0.00005 || Math.abs(r.y - sig[4]!) > 0.00005 || Math.abs(cam.fov - sig[5]!) > 0.005 || W !== sig[6] || H !== sig[7]) {
        css.render(cssScene, cam); sig[0] = p.x; sig[1] = p.y; sig[2] = p.z; sig[3] = r.x; sig[4] = r.y; sig[5] = cam.fov; sig[6] = W; sig[7] = H; cssDirty = false
      }
      if (firstFrame) { firstFrame(); firstFrame = null }
    },
    anchors(): Readonly<Record<string, StageAnchor>> {
      const av = plates.find((p) => p.spec.avatar)
      if (!av) return {}
      tv.setFromMatrixPosition(av.obj.matrixWorld).project(cam)
      return { 'visor-avatar': { x: (tv.x * 0.5 + 0.5) * W, y: (-tv.y * 0.5 + 0.5) * H, visible: tv.z < 1 && Math.abs(tv.x) < 1 } }
    },
    dispose() {
      releaseTaps?.(); releaseTaps = null; ticks.clear(); frames.clear()
      for (const p of [...plates]) { clearTimeout(p.timer); p.off() }
      scene.traverse((o) => { const m = o as THREE.Mesh; m.geometry?.dispose(); const mat = m.material as THREE.Material | THREE.Material[] | undefined; if (Array.isArray(mat)) mat.forEach((x) => x.dispose()); else mat?.dispose() })
      css.domElement.remove()
    }
  }
  return layer
}
