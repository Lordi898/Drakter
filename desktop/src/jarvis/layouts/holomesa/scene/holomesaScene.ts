/**
 * El mundo de la Holomesa sobre el Stage único: la mesa, las 7 estaciones, el orbe de reserva, la
 * cámara que vuela entre ellas y la capa de etiquetas en pantalla. Dos `StageLayer`:
 *  - `holomesa` (orden 20): la escena 3D, bajo el avatar (orden 50).
 *  - `holomesa-overlay` (orden 80): etiquetas, tags, tooltip y retícula, sobre el avatar.
 * React no corre por fotograma: el HUD empuja datos (`setData`, `focus`…) y escucha cambios discretos.
 */
import * as THREE from 'three'
import type { AvatarViewport } from '@/character/avatars/types'
import type { CharacterState } from '@/character/types'
import { acquireAudioTaps, readWaveform, WAVEFORM_SAMPLES } from '@/voice/levels'
import type { QualityProfile, StageFrame, StageLayer } from '../../../stage/types'
import { SECTION_ORDER, type HoloSnapshot, type PickInfo, type SectionId } from '../model'
import { circlePts } from './geo'
import { createLabelRenderer, type LabelSpec } from './labels'
import { createMaterials, createSharedUniforms, disposeTree } from './materials'
import { createOrb, createStations, type Ctx, type Station } from './stations'
import { createTable, HEAD, TABLE_R } from './table'

interface Shot {
  readonly pos: THREE.Vector3
  readonly target: THREE.Vector3
  readonly fov: number
}

const OVER: Shot = { pos: new THREE.Vector3(3.6, 13.4, 18.6), target: new THREE.Vector3(3.6, 0.3, -0.9), fov: 42 }
const BOOT: Shot = { pos: new THREE.Vector3(0, 30, 6), target: new THREE.Vector3(0, 0, -0.5), fov: 50 }
const easeInOut = (x: number): number => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2)
const easeOut = (x: number): number => 1 - Math.pow(1 - x, 2)
const TIER_Q: Record<QualityProfile['tier'], number> = { cine: 1, equilibrado: 0.6, ahorro: 0 }

export interface HolomesaView {
  readonly focusId: SectionId | null
  readonly hoverId: SectionId | null
  /** Elemento seleccionado con clic en la sección abierta. */
  readonly selected: PickInfo | null
  /** Resumen de una línea por estación; cambia cuando se aplican datos nuevos (también los diferidos). */
  readonly metrics: Readonly<Record<SectionId, string>>
}

export interface HolomesaScene {
  readonly world: StageLayer
  readonly overlay: StageLayer
  readonly stations: readonly Station[]
  setData(snap: HoloSnapshot): void
  focus(id: SectionId | null, instant?: boolean): void
  setAgent(state: CharacterState): void
  setIndexing(on: boolean): void
  /** El avatar 3D ya se dibuja (el orbe propio se funde y le cede la cabecera). */
  setAvatarReady(ready: boolean): void
  /** Hueco del avatar acoplado cuando hay una sección abierta (px CSS) o `null`. */
  setDock(rect: { x: number; y: number; width: number; height: number } | null): void
  /** El puntero está sobre la escena (no sobre un panel del HUD). */
  setPointerInside(inside: boolean): void
  /** Clic sobre la escena: abre la estación bajo el cursor o selecciona el elemento. */
  click(): void
  /** Anillo que se expande desde la cabecera. */
  shock(color: number): void
  /** Secuencia de arranque (mesa que se dibuja, cámara que baja, hologramas que se imprimen). */
  boot(): Promise<void>
  /** Salida (≈1,2 s): los hologramas se desimprimen, el orbe se apaga y la mesa se borra hacia el canto. */
  unboot(): Promise<void>
  /** Recuadro del avatar para `JarvisAvatarSlot.setViewport`. */
  avatarViewport(frame: StageFrame): AvatarViewport
  getView(): HolomesaView
  subscribe(listener: () => void): () => void
  /** Conecta el `requestFrame` del Stage (bombeo de fotogramas en reposo o a demanda). */
  attach(requestFrame: (() => void) | null): void
  /** Vuelve a activar la escena tras `dispose()` (StrictMode monta, desmonta y remonta la misma instancia). */
  revive(): void
  /** Para temporizadores, animaciones y analizadores de audio. Los suscriptores se van con su propia baja. */
  dispose(): void
}

export function createHolomesaScene(initialReduced: boolean): HolomesaScene {
  const U = createSharedUniforms()
  const M = createMaterials(U)
  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 200)
  const table = createTable(U, M)
  scene.add(table.group)
  const stations = createStations(M)
  for (const s of stations) scene.add(s.group)
  table.setPads(stations.map((s) => s.pos), stations.map((s) => s.padR))
  const orb = createOrb(M)
  scene.add(orb.group)
  // Polvo de estrellas lejano: un único Points estático para que el vacío tenga profundidad.
  {
    const P: number[] = []
    for (let i = 0; i < 900; i++) {
      const a = Math.random() * Math.PI * 2, r = 30 + Math.random() * 60, y = -10 + Math.random() * 45
      P.push(Math.cos(a) * r, y, Math.sin(a) * r)
    }
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3))
    scene.add(new THREE.Points(g, new THREE.PointsMaterial({ color: 0x3a78b8, size: 1.3, sizeAttenuation: false, transparent: true, opacity: 0.55, depthWrite: false, blending: THREE.AdditiveBlending })))
  }
  const shocks = Array.from({ length: 3 }, () => {
    const l = new THREE.Line(new THREE.BufferGeometry().setFromPoints(circlePts(1, 160)), M.lineMat(0xffffff, 0))
    l.position.set(HEAD.x, 0.06, HEAD.z)
    l.visible = false
    scene.add(l)
    return { l, t: 9 }
  })

  // Retícula del cursor (en la superposición): un quad con shader propio, sin DOM.
  const reticleMat = new THREE.ShaderMaterial({
    uniforms: { uPos: { value: new THREE.Vector2() }, uView: { value: new THREE.Vector2(1, 1) }, uRot: { value: 0 }, uHot: { value: 0 }, uAlpha: { value: 0 } },
    vertexShader: /* glsl */ `uniform vec2 uPos, uView; varying vec2 vP;
      void main(){ vP = position.xy * 2.0 - 1.0; vec2 px = uPos + vP * 26.0;
        gl_Position = vec4(px.x / uView.x * 2.0 - 1.0, 1.0 - px.y / uView.y * 2.0, 0.0, 1.0); }`,
    fragmentShader: /* glsl */ `#define PI 3.14159265
      uniform float uRot, uHot, uAlpha; varying vec2 vP;
      void main(){ float r = length(vP) * 26.0; float a = atan(vP.y, vP.x) + uRot;
        float ring = 1.0 - smoothstep(0.6, 1.4, abs(r - mix(15.0, 11.0, uHot)));
        float dash = step(0.35, fract(a / (2.0 * PI) * 4.0));
        float inner = (1.0 - smoothstep(0.5, 1.2, abs(r - 5.0))) * 0.5;
        float dot = 1.0 - smoothstep(1.0, 2.0, r);
        float v = ring * dash + inner * uHot + dot * 0.8;
        vec3 c = mix(vec3(0.44, 0.84, 1.0), vec3(0.92, 0.98, 1.0), uHot);
        gl_FragColor = vec4(c, v * uAlpha * 0.85); }`,
    transparent: true,
    depthTest: false,
    depthWrite: false
  })
  const reticle = new THREE.Mesh(new THREE.PlaneGeometry(1, 1).translate(0.5, 0.5, 0), reticleMat)
  reticle.frustumCulled = false
  const overlayScene = new THREE.Scene()
  overlayScene.add(reticle)
  const overlayCam = new THREE.Camera()
  const labels = createLabelRenderer()

  // ── estado
  const ctx: { -readonly [K in keyof Ctx]: Ctx[K] } = { camera, quality: 0.6, reduced: initialReduced, agent: 'idle', voice: 0, nowHours: 12, indexing: false }
  let snap: HoloSnapshot | null = null
  let view: HolomesaView = { focusId: null, hoverId: null, selected: null, metrics: Object.fromEntries(SECTION_ORDER.map((id) => [id, ''])) as Record<SectionId, string> }
  const listeners = new Set<() => void>()
  const emit = (next: Partial<HolomesaView>): void => {
    const merged = { ...view, ...next }
    if (merged.focusId === view.focusId && merged.hoverId === view.hoverId && merged.selected === view.selected && merged.metrics === view.metrics) return
    view = merged
    for (const l of listeners) l()
  }
  let hoverPick: PickInfo | null = null
  const rc = new THREE.Raycaster()
  const mouse = new THREE.Vector2(9, 9)
  let inside = false
  let lastPointer = { x: NaN, y: NaN }
  let pointerDirty = false
  const cur: { pos: THREE.Vector3; target: THREE.Vector3; fov: number } = { pos: OVER.pos.clone(), target: OVER.target.clone(), fov: OVER.fov }
  let from: Shot = { ...OVER }
  let to: Shot = OVER
  let flyT = 1
  let flyDur = 1.5
  let hold = 0
  const par = new THREE.Vector2(), parT = new THREE.Vector2()
  const boot = { draw: 1, build: stations.map(() => 1), orb: 1 }
  let tweens: { t: number; dur: number; delay: number; fn: (k: number) => void; ez: (x: number) => number; done: () => void }[] = []
  let avatarReady = false
  let avK = 0
  let focusK = 0
  let dock: { x: number; y: number; width: number; height: number } | null = null
  const hov = stations.map(() => 0), foc = stations.map(() => 0), dimv = stations.map(() => 0)
  let time = 0
  let profile: QualityProfile | null = null
  let releaseTaps: (() => void) | null = null
  const wave = new Float32Array(WAVEFORM_SAMPLES)
  let pumpTimer = 0
  let lastDraw = 0
  let requestFrame: (() => void) | null = null
  let disposed = false
  let reticleRot = 0
  let compiling = false
  let pendingSnap: HoloSnapshot | null = null

  const shotFor = (id: SectionId | null): Shot => {
    if (!id) return OVER
    const s = stations.find((x) => x.id === id)!
    const dir = new THREE.Vector3(Math.sin(s.yaw), 0, Math.cos(s.yaw)), right = new THREE.Vector3(Math.cos(s.yaw), 0, -Math.sin(s.yaw))
    const dist = id === 'hoy' ? 10.8 : id === 'tareas' ? 9.6 : id === 'relaciones' ? 10.2 : 8.4
    return {
      pos: s.pos.clone().addScaledVector(dir, dist).add(new THREE.Vector3(0, 2.3 + s.height * 0.32, 0)),
      target: s.pos.clone().add(new THREE.Vector3(0, s.height * 0.3, 0)).addScaledVector(right, id === 'hoy' ? 1.9 : id === 'relaciones' ? 1.3 : 1.55),
      fov: 40
    }
  }
  const flyTo = (sh: Shot, dur: number): void => {
    from = { pos: cur.pos.clone(), target: cur.target.clone(), fov: cur.fov }
    to = sh
    flyT = 0
    flyDur = dur
  }
  const tween = (ms: number, fn: (k: number) => void, ez = easeOut, delay = 0): Promise<void> =>
    new Promise((resolve) => {
      if (ctx.reduced || ms <= 0) {
        fn(1)
        resolve()
        return
      }
      tweens.push({ t: 0, dur: ms / 1000, delay: delay / 1000, fn, ez, done: resolve })
      pump()
    })

  /** Pide fotogramas al ritmo máximo del nivel mientras haya animación (reposo o modo a demanda). */
  function pump(): void {
    if (pumpTimer || disposed || !requestFrame) return
    const maxFps = profile?.maxFps ?? 30
    const wait = Math.max(0, 1000 / maxFps - 10 - (performance.now() - lastDraw))
    pumpTimer = window.setTimeout(() => {
      pumpTimer = 0
      requestFrame?.()
    }, wait)
  }

  const project = (v: THREE.Vector3, w: number, h: number, out: { x: number; y: number; z: number }): void => {
    const p = v.clone().project(camera)
    out.x = (p.x * 0.5 + 0.5) * w
    out.y = (-p.y * 0.5 + 0.5) * h
    out.z = p.z
  }

  const tmpR = new THREE.Vector3(), tmpU = new THREE.Vector3(), v3 = new THREE.Vector3(), proj = { x: 0, y: 0, z: 0 }

  const world: StageLayer = {
    id: 'holomesa',
    order: 20,
    async init(frame) {
      camera.aspect = frame.width / Math.max(1, frame.height)
      camera.updateProjectionMatrix()
      // Mientras compila no se reconstruye nada (Three consulta los programas de los materiales):
      // los datos que lleguen se aplican al terminar.
      compiling = true
      try {
        await frame.renderer.compileAsync(scene, camera)
      } finally {
        compiling = false
        if (pendingSnap) {
          const next = pendingSnap
          pendingSnap = null
          api.setData(next)
        }
      }
    },
    setQuality(q) {
      profile = q
      ctx.quality = TIER_Q[q.tier]
      table.setDust(Math.round(Math.min(1800, q.particles * 0.09)))
      table.uniforms.uQuality.value = ctx.quality
      for (const s of stations)
        s.group.traverse((o) => {
          const m = (o as THREE.Mesh).material as THREE.ShaderMaterial | undefined
          if (m?.uniforms?.uScan) m.uniforms.uScan.value = ctx.quality > 0 ? 1 : 0
        })
    },
    update(frame) {
      const dt = frame.dt
      profile ??= frame.quality
      ctx.reduced = frame.reducedMotion
      if (!ctx.reduced) time += dt
      U.uTime.value = time
      if (snap) {
        const n = new Date()
        ctx.nowHours = snap.nowHours + (n.getTime() - snap.now.getTime()) / 3_600_000
      }
      // Animaciones con duración (arranque, salida).
      if (tweens.length) {
        for (const tw of tweens) {
          if (tw.delay > 0) {
            tw.delay -= dt
            continue
          }
          tw.t = Math.min(tw.dur, tw.t + dt)
          tw.fn(tw.ez(tw.t / tw.dur))
        }
        const finished = tweens.filter((tw) => tw.t >= tw.dur)
        tweens = tweens.filter((tw) => tw.t < tw.dur)
        for (const tw of finished) tw.done()
      }
      // Voz: nivel desde la onda real (salida si habla, micrófono si escucha).
      let level = 0
      if (releaseTaps && readWaveform(ctx.agent === 'listening' ? 'input' : 'output', wave)) {
        let sum = 0
        for (let i = 0; i < wave.length; i++) sum += wave[i]! * wave[i]!
        level = Math.min(1, Math.sqrt(sum / wave.length) * 6)
      }
      ctx.voice += (level - ctx.voice) * Math.min(1, dt * 18)
      // Cámara: vuelo curvo alrededor del centro de la mesa + parallax del puntero.
      if (hold > 0) hold -= dt
      else if (flyT < 1) {
        flyT = Math.min(1, flyT + dt / flyDur)
        const e = easeInOut(flyT), arc = Math.sin(Math.PI * flyT)
        const a0 = Math.atan2(from.pos.x, from.pos.z), a1 = Math.atan2(to.pos.x, to.pos.z)
        let da = a1 - a0
        if (da > Math.PI) da -= Math.PI * 2
        if (da < -Math.PI) da += Math.PI * 2
        const r0 = Math.hypot(from.pos.x, from.pos.z), r1 = Math.hypot(to.pos.x, to.pos.z)
        const a = a0 + da * e, r = r0 + (r1 - r0) * e + arc * 2.2 * Math.min(1, Math.abs(da) + 0.3)
        cur.pos.set(Math.sin(a) * r, from.pos.y + (to.pos.y - from.pos.y) * e + arc * 2.4, Math.cos(a) * r)
        cur.target.lerpVectors(from.target, to.target, easeInOut(Math.min(1, flyT * 1.15)))
        cur.fov = from.fov + (to.fov - from.fov) * e + arc * 6
      }
      const flying = flyT < 1 || hold > 0
      const parallaxOn = frame.quality.parallax && !ctx.reduced
      parT.set(parallaxOn && inside && frame.pointer.active ? frame.pointer.x : 0, parallaxOn && inside && frame.pointer.active ? frame.pointer.y : 0)
      par.lerp(parT, Math.min(1, dt * 3))
      if (par.lengthSq() < 1e-6) par.set(0, 0)
      const aspect = frame.width / Math.max(1, frame.height)
      // La vista general se encuadra para la proporción del prototipo (~2:1); en ventanas más altas o
      // estrechas la cámara se aleja para que la mesa no quede bajo el carril ni la conversación.
      const fit = 1 + (Math.min(1.7, Math.max(1, 2.05 / aspect)) - 1) * (1 - focusK)
      camera.position.copy(cur.target).addScaledVector(v3.subVectors(cur.pos, cur.target), fit)
      camera.lookAt(cur.target)
      const pk = view.focusId ? 0.55 : frame.quality.tier === 'cine' ? 0.9 : 0.6
      camera.updateMatrixWorld()
      tmpR.setFromMatrixColumn(camera.matrixWorld, 0)
      tmpU.setFromMatrixColumn(camera.matrixWorld, 1)
      camera.position.addScaledVector(tmpR, par.x * pk).addScaledVector(tmpU, -par.y * pk * 0.5)
      camera.lookAt(cur.target)
      if (camera.fov !== cur.fov || camera.aspect !== aspect) {
        camera.fov = cur.fov
        camera.aspect = aspect
        camera.updateProjectionMatrix()
      }
      camera.updateMatrixWorld()
      // Ratón: solo cuando de verdad se mueve (los pointermove sintéticos no despiertan nada).
      if (frame.pointer.x !== lastPointer.x || frame.pointer.y !== lastPointer.y) {
        lastPointer = { x: frame.pointer.x, y: frame.pointer.y }
        pointerDirty = true
      }
      if (pointerDirty && !flying) {
        pointerDirty = false
        mouse.set(frame.pointer.x, frame.pointer.y)
        rc.setFromCamera(mouse, camera)
        let hoverId: SectionId | null = null
        hoverPick = null
        if (inside && frame.pointer.active) {
          const fs = view.focusId ? stations.find((s) => s.id === view.focusId) : undefined
          if (fs) {
            hoverPick = fs.pick(rc)
            if (hoverPick) hoverId = fs.id
          }
          if (!hoverPick) {
            const hit = rc.intersectObjects(stations.filter((s) => s.id !== view.focusId).map((s) => s.proxy), false)[0]
            if (hit) hoverId = stations.find((s) => s.proxy === hit.object)!.id
          }
        } else for (const s of stations) if (s.id !== view.focusId || !view.selected) s.clearPick()
        emit({ hoverId })
      }
      // Estaciones: transiciones suaves de hover, foco y atenuación.
      let settling = false
      stations.forEach((s, i) => {
        const k = ctx.reduced ? 1 : Math.min(1, dt * 6)
        const th = view.hoverId === s.id && !hoverPick ? 1 : 0, tf = view.focusId === s.id ? 1 : 0
        const td = view.focusId && view.focusId !== s.id ? 1 : view.hoverId && view.hoverId !== s.id && !view.focusId ? 0.25 : 0
        hov[i]! += (th - hov[i]!) * k
        foc[i]! += (tf - foc[i]!) * k
        dimv[i]! += (td - dimv[i]!) * k
        if (Math.abs(th - hov[i]!) + Math.abs(tf - foc[i]!) + Math.abs(td - dimv[i]!) > 0.01) settling = true
        s.hover = hov[i]!
        s.focus = foc[i]!
        s.dim = dimv[i]!
        s.build = boot.build[i]!
        s.group.visible = s.build > 0.001
        if (s.group.visible) s.update(time, ctx.reduced ? 0 : dt, ctx)
        table.uniforms.uPadHover.value[i] = hov[i]!
        table.uniforms.uPadFocus.value[i] = foc[i]!
      })
      const fk = ctx.reduced ? 1 : Math.min(1, dt * 4)
      table.uniforms.uFocus.value += ((view.focusId ? 1 : 0) - table.uniforms.uFocus.value) * fk
      U.uFocusG.value = table.uniforms.uFocus.value
      focusK += ((view.focusId ? 1 : 0) - focusK) * fk
      table.uniforms.uDraw.value = boot.draw
      table.update(dt, ctx.voice)
      avK += ((avatarReady ? 1 : 0) - avK) * (ctx.reduced ? 1 : Math.min(1, dt * 2.5))
      orb.update(time, ctx.reduced ? 0 : dt, ctx, (1 - avK) * boot.orb * (1 - focusK * 0.6))
      let shocking = false
      for (const s of shocks)
        if (s.l.visible) {
          s.t += dt
          const p = s.t / 1.4
          if (p >= 1) {
            s.l.visible = false
            continue
          }
          shocking = true
          s.l.scale.setScalar(1.3 + p * (TABLE_R + 2))
          ;(s.l.material as THREE.ShaderMaterial).uniforms.uOpacity!.value = (1 - p) * (1 - p) * 1.6
        }
      const animating =
        flying || tweens.length > 0 || ctx.voice > 0.02 || shocking || settling || Math.abs(focusK - (view.focusId ? 1 : 0)) > 0.01 || Math.abs(avK - (avatarReady ? 1 : 0)) > 0.01
      lastDraw = performance.now()
      if (animating) pump()
    },
    render(frame) {
      frame.renderer.render(scene, camera)
    },
    dispose() {
      disposeTree(scene)
    }
  }

  let overlayFading = false
  const overlay: StageLayer = {
    id: 'holomesa-overlay',
    order: 80,
    init() {},
    update(frame) {
      const w = frame.width, h = frame.height
      const specs: LabelSpec[] = []
      const flying = flyT < 1 || hold > 0
      // Vista general: una etiqueta por estación, proyectada al canto de la mesa o sobre el holograma.
      if (!view.focusId && !flying && snap)
        stations.forEach((s) => {
          if (s.build < 0.6 || view.hoverId === s.id) return
          if (s.id === 'hoy' || s.pos.z > 4) v3.copy(s.pos).setY(s.height + 0.3)
          else {
            v3.set(s.pos.x, 0, s.pos.z).normalize().multiplyScalar(10.5)
            v3.y = 0.05
          }
          project(v3, w, h, proj)
          if (proj.z < 1) specs.push({ id: 'st:' + s.id, style: 'station', tone: '', lines: [`${s.key} · ${s.name}`, s.metric], x: proj.x, y: proj.y })
        })
      // Sección abierta: etiquetas ancladas a sus datos.
      if (view.focusId && focusK > 0.6 && !flying) {
        const fs = stations.find((s) => s.id === view.focusId)
        if (fs) {
          scene.updateMatrixWorld()
          fs.tags().forEach((tg, i) => {
            project(tg.p, w, h, proj)
            if (proj.z < 1) specs.push({ id: `tag:${fs.id}:${i}`, style: 'tag', tone: tg.k, lines: [tg.t], x: proj.x, y: proj.y })
          })
        }
      }
      // Tooltip junto al cursor.
      const px = ((frame.pointer.x + 1) / 2) * w, py = ((1 - frame.pointer.y) / 2) * h
      const hoverStation = !hoverPick && view.hoverId && !view.focusId ? stations.find((s) => s.id === view.hoverId) : undefined
      if (inside && frame.pointer.active && (hoverPick || hoverStation)) {
        const lines = hoverPick ? [hoverPick.title, hoverPick.sub, ...hoverPick.lines] : [`${hoverStation!.key} · ${hoverStation!.name}`, hoverStation!.metric, 'Clic para abrir']
        specs.push({ id: 'tip', style: 'tip', tone: 'hi', lines: lines.filter(Boolean), x: Math.min(px, w - 260), y: Math.min(py, h - 90) })
      }
      overlayFading = labels.set(specs, frame.dt, frame.reducedMotion)
      // Retícula: sigue al cursor sobre la escena; gira despacio (parada con «reducir movimiento»).
      const showReticle = inside && frame.pointer.active
      const ru = reticleMat.uniforms
      ru.uAlpha!.value += ((showReticle ? 1 : 0) - ru.uAlpha!.value) * (frame.reducedMotion ? 1 : Math.min(1, frame.dt * 10))
      ;(ru.uPos!.value as THREE.Vector2).set(px, py)
      ;(ru.uView!.value as THREE.Vector2).set(w, h)
      if (!frame.reducedMotion) reticleRot += frame.dt * 0.7
      ru.uRot!.value = reticleRot
      ru.uHot!.value += ((hoverPick || view.hoverId ? 1 : 0) - ru.uHot!.value) * Math.min(1, frame.dt * 10)
      if (overlayFading) pump()
    },
    render(frame) {
      labels.render(frame.renderer, frame.width, frame.height)
      if (reticleMat.uniforms.uAlpha!.value > 0.01) frame.renderer.render(overlayScene, overlayCam)
    },
    dispose() {
      labels.dispose()
      reticle.geometry.dispose()
      reticleMat.dispose()
    }
  }

  const api: HolomesaScene = {
    world,
    overlay,
    stations,
    setData(next) {
      if (compiling) {
        pendingSnap = next
        return
      }
      snap = next
      ctx.nowHours = next.nowHours
      for (const s of stations) s.setData(next)
      emit({ selected: null, metrics: Object.fromEntries(stations.map((s) => [s.id, s.metric])) as Record<SectionId, string> })
      hoverPick = null
      pointerDirty = true
      pump()
    },
    focus(id, instant = false) {
      if (view.focusId === id) return
      for (const s of stations) s.clearPick()
      hoverPick = null
      const sh = shotFor(id)
      if (instant || ctx.reduced) {
        cur.pos.copy(sh.pos)
        cur.target.copy(sh.target)
        cur.fov = sh.fov
        flyT = 1
        to = sh
      } else flyTo(sh, id && view.focusId ? 1.45 : 1.3)
      emit({ focusId: id, selected: null, hoverId: null })
      pump()
    },
    setAgent(state) {
      const prev = ctx.agent
      ctx.agent = state
      U.uOffline.value = state === 'offline' ? 1 : 0
      U.uWarn.value = state === 'error' ? 0.4 : 0
      if (state !== prev) {
        if (state === 'success') api.shock(0xffffff)
        else if (state === 'interrupted') api.shock(0xffb050)
        else if (state === 'error') api.shock(0xff6040)
      }
      // Solo hay analizadores de audio mientras se habla o se escucha.
      const wantTaps = state === 'speaking' || state === 'listening'
      if (wantTaps && !releaseTaps) releaseTaps = acquireAudioTaps()
      else if (!wantTaps && releaseTaps) {
        releaseTaps()
        releaseTaps = null
      }
      pump()
    },
    setIndexing(on) {
      ctx.indexing = on
    },
    setAvatarReady(ready) {
      avatarReady = ready
      pump()
    },
    setDock(rect) {
      dock = rect
    },
    setPointerInside(on) {
      if (inside === on) return
      inside = on
      pointerDirty = true
      pump()
    },
    click() {
      if (hoverPick) {
        emit({ selected: hoverPick })
        api.shock(0x9fe8ff)
      } else if (view.hoverId && view.hoverId !== view.focusId) api.focus(view.hoverId)
    },
    shock(color) {
      const s = shocks.find((x) => !x.l.visible) ?? shocks[0]!
      s.t = 0
      ;((s.l.material as THREE.ShaderMaterial).uniforms.uColor!.value as THREE.Color).set(color)
      s.l.visible = true
      pump()
    },
    async boot() {
      if (ctx.reduced) {
        boot.draw = 1
        boot.build.fill(1)
        boot.orb = 1
        api.focus(view.focusId, true)
        return
      }
      boot.draw = 0
      boot.build.fill(0)
      boot.orb = 0
      cur.pos.copy(BOOT.pos)
      cur.target.copy(BOOT.target)
      cur.fov = BOOT.fov
      const target = shotFor(view.focusId)
      flyTo(target, 3.0)
      hold = 1.1
      const drawn = tween(1700, (k) => (boot.draw = k), (x) => 1 - Math.pow(1 - x, 1.8))
      const built = Promise.all(stations.map((_, i) => tween(1300, (k) => (boot.build[i] = k), easeOut, 1100 + i * 150)))
      const orbIn = tween(1200, (k) => (boot.orb = k), easeOut, 1600)
      await Promise.all([drawn, built, orbIn])
    },
    async unboot() {
      api.focus(null)
      const b0 = [...boot.build], o0 = boot.orb
      const out = Promise.all(stations.map((_, i) => tween(650, (k) => (boot.build[i] = b0[i]! * (1 - k)))))
      const orbOut = tween(700, (k) => (boot.orb = o0 * (1 - k)))
      const erase = tween(700, (k) => (boot.draw = 1 - k), (x) => x * x, 450)
      await Promise.all([out, orbOut, erase])
    },
    avatarViewport(frame) {
      // Preside la cabecera de la mesa en la vista general; con una sección abierta se acopla al hueco del HUD.
      v3.set(HEAD.x, 0.4, HEAD.z - 0.2)
      project(v3, frame.width, frame.height, proj)
      const hh = Math.max(200, Math.min(400, proj.y - 96))
      const ww = hh * (360 / 432)
      const base = { x: proj.x - ww / 2, y: proj.y - hh, width: ww, height: hh }
      const d = dock ?? { x: 16, y: frame.height - 150, width: 110, height: 132 }
      const k = focusK
      return {
        x: Math.round(base.x + (d.x - base.x) * k),
        y: Math.round(base.y + (d.y - base.y) * k),
        width: Math.round(base.width + (d.width - base.width) * k),
        height: Math.round(base.height + (d.height - base.height) * k)
      }
    },
    getView: () => view,
    attach(rf) {
      requestFrame = rf
    },
    subscribe(listener) {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
    revive() {
      disposed = false
      api.setAgent(ctx.agent)
    },
    dispose() {
      disposed = true
      if (pumpTimer) clearTimeout(pumpTimer)
      pumpTimer = 0
      releaseTaps?.()
      releaseTaps = null
      for (const tw of tweens) tw.done()
      tweens = []
    }
  }
  return api
}

export { SECTION_ORDER }
