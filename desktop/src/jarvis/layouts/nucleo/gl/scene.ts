/**
 * Escena de Núcleo como capa del Stage: el astrolabio (núcleo, polvo y seis anillos), la cámara con
 * paralaje que viaja entre la vista núcleo y la de sección, la selección con el ratón y el recuadro del
 * avatar (que dibuja la capa del avatar del anfitrión, debajo: los anillos se suman por encima).
 * React no corre por fotograma: el HUD llama a `setModel`, `go`, `pointer`… y recibe avisos solo
 * cuando algo cambia.
 */
import * as THREE from 'three'
import type { AvatarViewport } from '@/character/avatars/types'
import type { CharacterState } from '@/character/types'
import { readSpectrum } from '@/voice/levels'
import type { QualityProfile, QualityTier, StageFrame, StageLayer } from '../../../stage/types'
import { almacen, almState } from '../modules/almacen'
import { makeModule, pickDetail, type ClickAction, type Mod, type ModuleCtx, type ModuleId, type SceneCtx, type Tip } from '../modules/base'
import { calendario } from '../modules/calendario'
import { habitos } from '../modules/habitos'
import { hoy } from '../modules/hoy'
import { relaciones, relState } from '../modules/relaciones'
import { tareas, tareasState } from '../modules/tareas'
import type { IdMap, NucleoModel } from '../model'
import { TAU, createGfx, makeDust, type Gfx } from './kit'
import { createNucleus, type ShockKind } from './nucleus'
import { createTweens, ease } from './tween'

const lerp = (a: number, b: number, t: number) => a + (b - a) * t
const clamp = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x))
const damp = (cur: number, target: number, lambda: number, dt: number) => cur + (target - cur) * (1 - Math.exp(-lambda * dt))
const hex = (h: number): [number, number, number] => [((h >> 16) & 255) / 255, ((h >> 8) & 255) / 255, (h & 255) / 255]

/** Color y energía (velocidad de giro) de cada estado del agente. */
export const STATE_LOOK: Readonly<Record<CharacterState, { readonly hex: number; readonly energy: number }>> = {
  idle: { hex: 0x4fd8ff, energy: 1 }, listening: { hex: 0x8ffcff, energy: 0.55 }, thinking: { hex: 0x7d95ff, energy: 2.4 },
  speaking: { hex: 0xcdf0ff, energy: 1.25 }, executing: { hex: 0x2f9bff, energy: 3.2 }, success: { hex: 0xfff3d6, energy: 1.5 },
  error: { hex: 0xff4d5e, energy: 0.3 }, interrupted: { hex: 0xffb347, energy: 0.12 }, offline: { hex: 0x4a6584, energy: 0.04 }
}
export const stateCss = (s: CharacterState): string => `#${STATE_LOOK[s].hex.toString(16).padStart(6, '0')}`

const DUST: Readonly<Record<QualityTier, number>> = { cine: 5200, equilibrado: 2600, ahorro: 900 }
const HOME_CAM = { pos: new THREE.Vector3(0, 1.9, 19.8), tgt: new THREE.Vector3(0, -0.85, 0) }
const FOCUS_CAM = { pos: new THREE.Vector3(0, 1.7, 19.4), tgt: new THREE.Vector3(0, 0.2, 0) }
const FOCUS_TILT = 0.5
const AW = 400, AH = 480

export interface SceneCallbacks {
  /** Cambió lo que hay bajo el puntero (un elemento de la sección o un anillo en el núcleo). */
  hover(tip: Tip | null): void
  /** Se desplegó una sección (o se volvió al núcleo). */
  focus(id: ModuleId | null): void
  /** Clic en un elemento: selección (ya aplicada) o una acción real que ejecuta el HUD. */
  action(id: ModuleId, action: ClickAction, num: number): void
  /** Terminó el arranque. */
  booted(): void
}

export interface FocusFrame { readonly cx: number; readonly cy: number; readonly r: number; readonly ry: number }

export interface NucleoScene extends StageLayer {
  readonly modules: readonly Mod[]
  readonly ctx: ModuleCtx
  setModel(model: NucleoModel): void
  setAgentState(state: CharacterState): void
  /** Sin avatar 3D: el orbe de puntos ocupa su sitio. */
  setOrb(on: boolean): void
  go(id: ModuleId | null): void
  readonly focus: ModuleId | null
  module(id: ModuleId): Mod
  pointer(x: number, y: number, inside: boolean): void
  pointerDown(x: number, y: number): void
  /** true si el clic lo consumió el lienzo. */
  pointerUp(): boolean
  shock(kind?: ShockKind): void
  boot(instant: boolean): void
  skipBoot(): void
  /** Salida: los anillos se recogen hacia el núcleo y todo se apaga (≈ 1 s). */
  collapse(): Promise<void>
  readonly booting: boolean
  avatarViewport(frame: StageFrame): AvatarViewport
  focusFrame(): FocusFrame
  /** Cuadro de un elemento en pantalla (px CSS) para la retícula de fijación, o null. */
  target(): { x: number; y: number; r: number } | null
}

export function createNucleoScene(ids: IdMap, model: NucleoModel, cb: SceneCallbacks): NucleoScene {
  const gfx: Gfx = createGfx()
  const ctx: ModuleCtx = { gfx, ids, model }
  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(36, 1, 0.5, 90)
  const nucleus = createNucleus(gfx)
  const dust = makeDust(gfx, DUST.cine)
  const modules: Mod[] = [
    makeModule(hoy, ctx, undefined), makeModule(tareas, ctx, tareasState()), makeModule(habitos, ctx, undefined),
    makeModule(calendario, ctx, undefined), makeModule(relaciones, ctx, relState()), makeModule(almacen, ctx, almState())
  ] as Mod[]
  scene.add(nucleus.group, dust.pts)
  for (const m of modules) scene.add(m.group)
  const tw = createTweens()
  const byId = (id: ModuleId): Mod => modules.find((m) => m.id === id)!

  let w = 1, h = 1, pr = 1, reduced = false, parallax = 1
  let focus: Mod | null = null, hoverModule: Mod | null = null
  let g = 0, G = 0, zoom = 1, avatarK = 1, energy = 1, voice = 0
  let state: CharacterState = 'idle'
  const mouse = { x: -1, y: -1, nx: 0, ny: 0, dirty: false, inside: false }
  let drag: { x: number; y: number; x0: number; on: boolean } | null = null
  let booting = false
  let orb = false
  let avatar = { x: 0, y: 0, h: 0 }
  const anchor = new THREE.Vector3(0, 0.7, 0)
  const camPos = HOME_CAM.pos.clone(), camTgt = HOME_CAM.tgt.clone(), par = new THREE.Vector2()
  const v = new THREE.Vector3(), v2 = new THREE.Vector3(), qh = new THREE.Quaternion(), qt = new THREE.Quaternion(), qf = new THREE.Quaternion(), eu = new THREE.Euler()
  const ray = new THREE.Raycaster(), ndc = new THREE.Vector2(), plane = new THREE.Plane(), Z = new THREE.Vector3(0, 0, 1), inv = new THREE.Matrix4()
  const target = new THREE.Vector3(0.31, 0.85, 1)
  const labelScale = gfx.U.uLabelScale
  const sc: SceneCtx = { camera, project: (wp) => { v2.copy(wp).project(camera); return { x: (v2.x * 0.5 + 0.5) * w, y: (-v2.y * 0.5 + 0.5) * h } } }
  const pxPerUnit = (dist: number) => h / 2 / (Math.tan((camera.fov * Math.PI) / 360) * dist)
  let lastTipKey = ''
  const emitTip = (tip: Tip | null): void => {
    const k = tip ? `${tip.title}|${tip.sub}|${tip.hint ?? ''}` : ''
    if (k !== lastTipKey) { lastTipKey = k; cb.hover(tip) }
  }

  function local(m: Mod): THREE.Vector3 | null {
    plane.setFromNormalAndCoplanarPoint(v.copy(Z).applyQuaternion(m.group.quaternion), m.group.position)
    if (!ray.ray.intersectPlane(plane, v)) return null
    inv.copy(m.group.matrixWorld).invert()
    return v.applyMatrix4(inv)
  }
  function pick(): void {
    ndc.set((mouse.x / w) * 2 - 1, -(mouse.y / h) * 2 + 1)
    ray.setFromCamera(ndc, camera)
    let hm: Mod | null = null
    if (focus) {
      const m = focus
      let id = 0
      if (mouse.inside && !drag?.on) {
        if (m.def.pickScreen) id = m.def.pickScreen(m as never, mouse.x, mouse.y, sc)
        else { const p = local(m); id = p ? pickDetail(m, p.x, p.y) : 0 }
      }
      if (id !== m.hover) m.hover = id
      emitTip(id ? m.def.tip(id, ctx, m as never) : null)
    } else if (mouse.inside && G > 0.9) {
      for (const m of modules) {
        if (m.def.cloud || m.intro < 0.9) continue
        const p = local(m)
        if (!p) continue
        const r = Math.hypot(p.x, p.y)
        if (r > m.def.rIn - 0.12 && r < m.def.rOut + 0.2) { hm = m; break }
      }
      emitTip(hm ? { title: hm.def.name, sub: hm.def.kpi(ctx), hint: `clic para desplegar · tecla ${hm.def.key}` } : null)
    } else emitTip(null)
    hoverModule = hm
  }

  const go = (id: ModuleId | null): void => {
    const m = id ? byId(id) : null
    if (m === focus) return
    if (focus) focus.hover = 0
    focus = m
    hoverModule = null
    emitTip(null)
    if (m) nucleus.shock()
    cb.focus(id)
  }

  let dustCount = DUST.cine
  const setQuality = (q: QualityProfile): void => {
    dustCount = Math.min(DUST[q.tier], Math.max(0, q.particles))
    dust.setCount(dustCount)
    parallax = q.parallax ? (q.tier === 'cine' ? 1 : 0.6) : 0
  }

  const layer: NucleoScene = {
    id: 'nucleo-scene',
    order: 60,
    modules,
    ctx,
    get focus() { return focus?.id ?? null },
    get booting() { return booting },
    module: byId,
    async init(frame) {
      layer.resize?.(frame)
      setQuality(frame.quality)
      // compileAsync de Three falla si otra capa compila a la vez (p. ej. el avatar): se cae a la compilación síncrona.
      try { await frame.renderer.compileAsync(scene, camera) } catch { frame.renderer.compile(scene, camera) }
    },
    resize(frame) {
      w = frame.width
      h = frame.height
      pr = frame.renderScale
      camera.aspect = w / Math.max(1, h)
      camera.updateProjectionMatrix()
      gfx.U.uPx.value = (h * pr) / 2 / Math.tan((camera.fov * Math.PI) / 360)
      gfx.U.uView.value.set(w * pr, h * pr)
      labelScale.value = pr
    },
    setQuality,
    update(frame) {
      const dt = frame.dt, t = frame.time
      if (frame.width !== w || frame.height !== h || frame.renderScale !== pr) layer.resize?.(frame)
      reduced = frame.reducedMotion
      tw.tick(dt)
      gfx.U.uTime.value = t
      // Voz real: salida mientras habla, micrófono mientras escucha. En reposo no se toca el audio.
      const spec = nucleus.spec
      const tap = state === 'speaking' ? 'output' : state === 'listening' ? 'input' : null
      let lvl = 0
      if (tap && readSpectrum(tap, spec)) { let s = 0; for (let i = 0; i < 64; i++) s += spec[i]!; lvl = Math.min(1, (s / 64 / 255) * 2.4) }
      else if (spec[0] || spec[8] || spec[20]) spec.fill(0)
      voice = damp(voice, lvl, 12, dt)
      gfx.U.uVoice.value = voice
      energy = damp(energy, STATE_LOOK[state].energy, 3, dt)
      nucleus.tint.lerp(target, 1 - Math.exp(-dt * 5))
      dust.uniforms.uTint.value.lerp(nucleus.tint, 0.05)
      g = damp(g, focus ? 1 : 0, 4.2, dt)
      // Cámara: mezcla núcleo ↔ sección con paralaje del ratón.
      const pk = reduced ? 0 : parallax
      par.x = damp(par.x, mouse.nx * pk, 3.5, dt)
      par.y = damp(par.y, mouse.ny * pk, 3.5, dt)
      const ge = ease.inOut(g), arc = Math.sin(Math.PI * g)
      camPos.lerpVectors(HOME_CAM.pos, FOCUS_CAM.pos, ge)
      camTgt.lerpVectors(HOME_CAM.tgt, FOCUS_CAM.tgt, ge)
      camPos.z += arc * 2.6
      camPos.y += arc * 1.1
      const amp = lerp(1.25, 0.85, ge)
      camera.position.set(camPos.x + par.x * amp, camPos.y - par.y * amp * 0.6, camPos.z + (1 - zoom) * 9)
      camera.lookAt(camTgt.x + par.x * 0.12, camTgt.y, camTgt.z)
      camera.updateMatrixWorld()
      const dist = camera.position.distanceTo(camTgt)
      gfx.U.uDepth.value.set(dist - 7.5, dist + 7.5)
      anchor.set(0, lerp(0.72, 0.55, ge), 0)
      eu.set(-FOCUS_TILT + par.y * 0.1, par.x * 0.16, 0)
      qt.setFromEuler(eu)
      qf.copy(camera.quaternion).multiply(qt)
      for (const m of modules) {
        const isF = focus === m
        const f = (m.f = damp(m.f, isF ? 1 : 0, isF ? 4.2 : 6, dt)), fe = ease.inOut(f), hp = m.def.home, others = g * (1 - f)
        if (!reduced) m.spinA += dt * hp.spin * energy * TAU * (1 - fe) * (hoverModule === m ? 0.25 : 1)
        if (m.spinA > Math.PI) m.spinA -= TAU
        if (m.spinA < -Math.PI) m.spinA += TAU
        eu.set(hp.rx + (reduced ? 0 : Math.sin(t * 0.17 + hp.rz * 9) * 0.035), 0, hp.rz + (reduced ? 0 : Math.cos(t * 0.13 + hp.rx * 5) * 0.03))
        qh.setFromEuler(eu)
        m.group.quaternion.copy(qh).slerp(qf, fe)
        m.spin.rotation.z = m.def.single ? m.spinA * (1 - fe) : m.spinA
        const ik = 0.25 + 0.75 * ease.outBack(clamp(m.intro))
        const rise = Math.sin(Math.PI * f) // el anillo elegido se alza y viene hacia la cámara
        m.group.position.set(lerp(hp.pos[0], 0, fe), lerp(hp.pos[1], 0.2, fe) + rise * 1.5 - others * (m.def.cloud ? 0 : 1.1), lerp(hp.pos[2], 0, fe) + rise * 2.2 - others * 2.5)
        m.group.scale.setScalar(lerp(hp.scale, 1, fe) * (1 + 0.1 * others) * ik)
        m.group.updateMatrixWorld()
        const io = clamp(m.intro * 3) * G, dim = lerp(1, 0.2, others)
        m.homeOpacity = io * dim
        m.boost = damp(m.boost, hoverModule === m ? 0.85 : 0, 10, dt)
        const hu = m.homeMesh.material.uniforms, du = m.detailMesh.material.uniforms
        if (m.def.single) {
          du.uOpacity.value = io * lerp(lerp(0.62, 0.16, others), 1, f)
          du.uReveal.value = m.intro
          du.uMask.value = 1 - f
          du.uBoost.value = m.boost * (1 - f)
        } else {
          hu.uOpacity.value = io * dim * (1 - f)
          hu.uReveal.value = m.intro
          hu.uBoost.value = m.boost
          m.homeMesh.visible = f < 0.995
          m.detailMesh.visible = f > 0.004
          du.uOpacity.value = G * f
          du.uReveal.value = clamp(f * 1.35)
          du.uMask.value = 0
        }
        du.uHover.value = m.hover || -1
        du.uSel.value = m.sel || -1
        m.def.update?.(m as never, t, dt, f, sc)
      }
      dust.uniforms.uOpacity.value = G * lerp(1, 0.55, g)
      dust.uniforms.uSpin.value = reduced ? 0.15 : energy
      nucleus.update(t, dt, { anchor, camera, g, G, energy: reduced ? 0.2 : energy })
      // Recuadro del avatar: donde se proyecta el ancla; lo que queda detrás de él se enmascara.
      const p = sc.project(anchor), ad = camera.position.distanceTo(anchor), ppu = pxPerUnit(ad), wh = lerp(5.5, 3.5, ge) * (0.9 + 0.1 * avatarK)
      avatar = { x: p.x, y: p.y, h: wh * ppu * avatarK }
      gfx.U.uCore.value.set(p.x * pr, (h - p.y + 0.04 * wh * ppu) * pr, wh * ppu * 0.3 * pr * Math.max(0.05, avatarK), wh * ppu * 0.46 * pr * Math.max(0.05, avatarK))
      gfx.U.uCoreZ.value = ad
      if (mouse.dirty || focus?.def.pickScreen) { mouse.dirty = false; pick() }
    },
    render(frame) {
      frame.renderer.render(scene, camera)
    },
    anchors() {
      return { 'nucleo-core': { x: avatar.x, y: avatar.y, visible: G > 0.5 } }
    },
    setModel(next) {
      ctx.model = next
      for (const m of modules) m.rebuild(ctx)
      if (focus?.hover) emitTip(focus.def.tip(focus.hover, ctx, focus as never))
    },
    setAgentState(s) {
      const prev = state
      state = s
      const c = hex(STATE_LOOK[s].hex)
      target.set(c[0], c[1], c[2])
      if (prev === s) return
      if (s === 'success') nucleus.shock('success')
      else if (s === 'error') nucleus.shock('error')
      else if (s === 'interrupted' || s === 'offline') nucleus.shock('warn')
      else if (s === 'listening') nucleus.shock()
    },
    setOrb(on) {
      tw.tween({ dur: 0.5, update: (k) => { nucleus.orbK = on ? Math.max(nucleus.orbK, k) : nucleus.orbK * (1 - k) }, tag: 'orb' })
      orb = on
    },
    go,
    pointer(x, y, inside) {
      mouse.x = x
      mouse.y = y
      mouse.nx = (x / w) * 2 - 1
      mouse.ny = (y / h) * 2 - 1
      mouse.inside = inside
      mouse.dirty = true
      if (drag) {
        const m = focus
        if (m?.def.drag && (Math.abs(x - drag.x0) > 4 || drag.on)) { drag.on = true; m.dragging = true; m.def.drag(m as never, x - drag.x, y - drag.y) }
        drag.x = x
        drag.y = y
      }
    },
    pointerDown(x) { drag = { x, y: mouse.y, x0: x, on: false } },
    pointerUp() {
      if (!drag) return false
      const wasDrag = drag.on
      if (focus) focus.dragging = false
      drag = null
      if (wasDrag) return true
      if (focus) {
        const m = focus
        if (!m.hover) return false
        const num = m.hover, a = m.def.click(num, ctx, m as never)
        if (a.kind === 'select') m.sel = m.sel === num ? 0 : num
        cb.action(m.id, a, num)
        return true
      }
      if (hoverModule) { go(hoverModule.id); return true }
      return false
    },
    shock: (k) => nucleus.shock(k),
    boot(instant) {
      const T = 'boot', sp = reduced || instant ? 0.001 : 1, at = (s: number) => s * sp
      booting = true
      tw.flush(T, false)
      G = 0; zoom = 0; nucleus.intro = 0; nucleus.haloK = 0; nucleus.orbK = 0; avatarK = 0
      dust.uniforms.uGather.value = 0
      for (const m of modules) { m.intro = 0; m.f = 0 }
      tw.tween({ delay: at(0.05), dur: at(1.3), ease: ease.outCubic, update: (k) => { G = k }, tag: T })
      tw.tween({ delay: at(0.05), dur: at(3.3), ease: ease.outExpo, update: (k) => { zoom = k }, tag: T })
      tw.tween({ delay: at(0.05), dur: at(2.8), ease: ease.outCubic, update: (k) => { dust.uniforms.uGather.value = k }, tag: T })
      tw.tween({ delay: at(0.2), dur: at(1.5), ease: ease.linear, update: (k) => { byId('almacen').intro = k }, tag: T })
      tw.after(at(0.6), () => nucleus.shock(), T)
      tw.tween({ delay: at(0.6), dur: at(0.55), ease: ease.outBack, update: (k) => { nucleus.orbK = k * 0.55 }, tag: T })
      tw.tween({ delay: at(0.7), dur: at(1.1), ease: ease.linear, update: (k) => { nucleus.intro = k }, tag: T })
      ;(['hoy', 'habitos', 'tareas', 'calendario', 'relaciones'] as const).forEach((id, i) => {
        tw.tween({ delay: at(1.05 + i * 0.3), dur: at(1.2), ease: ease.linear, update: (k) => { byId(id).intro = k }, tag: T })
        tw.after(at(1.05 + i * 0.3), () => nucleus.shock(), T)
      })
      tw.tween({ delay: at(1.6), dur: at(0.9), update: (k) => { nucleus.haloK = k }, tag: T })
      tw.tween({ delay: at(2.3), dur: at(1.1), ease: ease.outCubic, update: (k) => { avatarK = k; nucleus.orbK = orb ? 0.55 + 0.45 * k : 0.55 * (1 - k) }, tag: T })
      tw.after(at(3.4), () => { booting = false; cb.booted() }, T)
      if (instant || reduced) tw.flush(T, true)
    },
    skipBoot() { if (booting) tw.flush('boot', true) },
    collapse() {
      const T = 'exit'
      tw.flush('boot', true)
      go(null)
      modules.forEach((m, i) => tw.tween({ delay: 0.05 + (modules.length - i) * 0.05, dur: 0.5, ease: ease.inCubic, update: (k) => { m.intro = 1 - k }, tag: T }))
      tw.tween({ dur: 0.45, update: (k) => { nucleus.haloK = 1 - k; avatarK = 1 - k }, tag: T })
      tw.tween({ delay: 0.15, dur: 0.55, ease: ease.inCubic, update: (k) => { nucleus.intro = 1 - k; zoom = 1 - k * 0.5; nucleus.orbK = orb ? 1 - k : Math.sin(k * Math.PI) * 0.5 }, tag: T })
      tw.tween({ delay: 0.5, dur: 0.45, update: (k) => { G = 1 - k }, tag: T })
      return new Promise((resolve) => tw.after(1.0, resolve, T))
    },
    avatarViewport() {
      const s = avatar.h / AH
      return { x: avatar.x - (AW * s) / 2, y: avatar.y - avatar.h * 0.02 - (AH * s) / 2, width: AW * s, height: AH * s }
    },
    focusFrame() {
      const ppu = pxPerUnit(FOCUS_CAM.pos.distanceTo(FOCUS_CAM.tgt))
      return { cx: w / 2, cy: h / 2, r: 5.0 * ppu, ry: 5.0 * ppu * Math.cos(FOCUS_TILT + 0.08) + 14 }
    },
    target() {
      const m = focus
      if (!m || !m.hover) return null
      if (m.id === 'tareas') { const s = (m.s as ReturnType<typeof tareasState>).sats.find((x) => x.t.num === m.hover); if (s) { const p = sc.project(v.set(s.x, s.y, 0).applyMatrix4(m.group.matrixWorld)); return { ...p, r: 18 } } }
      if (m.id === 'relaciones') {
        const s = m.s as ReturnType<typeof relState>, i = s.nodes.findIndex((n) => n.num === m.hover)
        if (i >= 0 && s.inner) { const p = sc.project(v.copy(s.P[i]!).applyMatrix4(s.inner.matrixWorld)); return { ...p, r: 20 } }
      }
      return { x: mouse.x, y: mouse.y, r: 24 }
    },
    dispose() {
      for (const m of modules) m.dispose()
      nucleus.dispose()
      gfx.dispose()
    }
  }
  return layer
}
