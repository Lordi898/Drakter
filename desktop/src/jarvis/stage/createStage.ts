/**
 * Motor del Stage de Jarvis (jarvis-arquitectura.md §2.4-§2.7): un único `WebGLRenderer` sobre el
 * lienzo a pantalla completa, capas ordenadas, un solo bucle y cero React por fotograma.
 *
 * Pérdida de contexto: el anfitrión escucha `webglcontextlost`/`webglcontextrestored` en su lienzo
 * para pasar a «HUD sin lienzo» y volver. El Stage se para al perderlo y, al restaurarse, Three
 * vuelve a subir geometrías, texturas y programas solo; el Stage reajusta el tamaño y sigue.
 */
import * as THREE from 'three'
import { createBloom, type Bloom } from './bloom'
import { detectGpu, type GpuInfo } from './gpu'
import { createGovernor } from './governor'
import { createLoop } from './loop'
import { PROFILES, TIERS, renderScaleFor } from './quality'
import type { CreateStage, QualityProfile, QualityTier, Stage, StageAnchor, StageFrame, StageLayer, StageStats } from './types'

const IDLE_AFTER_MS = 8000
const CLEAR = 0x02070d

/** Peldaños del regulador dentro de un nivel: primero la escala, después las partículas. */
const RUNGS: readonly { readonly scale: number; readonly particles: number }[] = [
  { scale: 1, particles: 1 },
  { scale: 0.85, particles: 1 },
  { scale: 0.7, particles: 1 },
  { scale: 0.7, particles: 0.5 }
]

interface Rung {
  readonly tier: QualityTier
  readonly scale: number
  readonly particles: number
}

/** Escalera del nivel de partida hacia abajo hasta Ahorro: nunca sube por encima de `start`. */
function ladderFrom(start: QualityTier): Rung[] {
  const out: Rung[] = []
  for (let i = TIERS.indexOf(start); i >= 0; i--) for (const r of RUNGS) out.push({ tier: TIERS[i]!, ...r })
  return out
}

interface Entry {
  readonly layer: StageLayer
  ready: boolean
}

/** Frame mutable por dentro; las capas lo ven como `StageFrame` de solo lectura. */
type MutableFrame = { -readonly [K in keyof StageFrame]: StageFrame[K] } & {
  pointer: { x: number; y: number; active: boolean }
}

export const createStage: CreateStage = (canvas, options) => {
  const gpu: GpuInfo | null = detectGpu()
  if (!gpu) throw new Error('webgl2-unavailable')

  let mode: QualityTier | 'auto' = options.quality
  const startTier = (): QualityTier => (mode === 'auto' ? gpu.tier : mode)
  let ladder = ladderFrom(startTier())
  let rung = 0

  let renderer: THREE.WebGLRenderer
  try {
    renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: startTier() === 'cine',
      alpha: false,
      stencil: false,
      depth: true,
      powerPreference: 'low-power',
      preserveDrawingBuffer: false
    })
  } catch (reason) {
    throw new Error('webgl2-unavailable', { cause: reason })
  }
  renderer.autoClear = false
  renderer.info.autoReset = false
  renderer.setClearColor(CLEAR, 1)

  canvas.setAttribute('aria-hidden', 'true')
  Object.assign(canvas.style, { position: 'fixed', inset: '0', width: '100%', height: '100%', pointerEvents: 'none', display: 'block' })

  const profileFor = (r: Rung): QualityProfile => {
    const base = PROFILES[r.tier]
    const particles = gpu.software ? 0 : Math.floor(base.particles * r.particles)
    return particles === base.particles ? base : { ...base, particles }
  }

  const frame: MutableFrame = {
    renderer,
    quality: profileFor(ladder[0]!),
    reducedMotion: options.reducedMotion,
    width: 1,
    height: 1,
    renderScale: 1,
    pointer: { x: 0, y: 0, active: false },
    time: 0,
    dt: 0
  }

  const entries: Entry[] = []
  const pendingInits: Promise<void>[] = []
  let readySettled = false
  let bloom: Bloom | null = null
  let disposed = false
  let lost = false
  let focused = document.hasFocus()
  let lastActivity = performance.now()
  let prevNow = -1
  let intervalMs = 0

  // Estadísticas
  const governor = createGovernor()
  let framesInSecond = 0
  let secondStart = performance.now()
  let fps = 0
  let lastDrawAt = -1
  let calls = 0
  let tris = 0

  const markActivity = (): void => {
    lastActivity = performance.now()
    updateInterval()
  }

  const updateInterval = (): void => {
    const q = frame.quality
    const active = performance.now() - lastActivity < IDLE_AFTER_MS
    const fpsNow = active ? q.maxFps : q.idleFps
    intervalMs = fpsNow > 0 ? (1000 / fpsNow) * (focused ? 1 : 2) : 0
    loop.setInterval(intervalMs)
  }

  const applySize = (): void => {
    const w = Math.max(1, canvas.clientWidth || window.innerWidth)
    const h = Math.max(1, canvas.clientHeight || window.innerHeight)
    const dpr = window.devicePixelRatio || 1
    const scale = renderScaleFor(frame.quality.pixelBudget, w, h, dpr) * (ladder[rung]?.scale ?? 1)
    frame.width = w
    frame.height = h
    frame.renderScale = scale
    renderer.setPixelRatio(scale)
    renderer.setSize(w, h, false)
    for (const e of entries) if (e.ready) e.layer.resize?.(frame)
    loop.request()
  }

  const applyRung = (next: number, reason: 'regulador' | 'manual'): void => {
    next = Math.max(0, Math.min(ladder.length - 1, next))
    const prevTier = frame.quality.tier
    rung = next
    frame.quality = profileFor(ladder[rung]!)
    if (reason === 'regulador' && mode !== 'auto' && frame.quality.tier !== prevTier)
      console.warn(`[drakter:jarvis] tirones sostenidos: el Stage baja de ${prevTier} a ${frame.quality.tier}`)
    const wantBloom = frame.quality.bloom === 'half'
    if (wantBloom && !bloom) bloom = createBloom()
    if (!wantBloom && bloom) {
      bloom.dispose()
      bloom = null
    }
    for (const e of entries) if (e.ready) e.layer.setQuality?.(frame.quality)
    governor.reset(performance.now())
    applySize()
    updateInterval()
  }

  const draw = (now: number, steady: boolean): void => {
    if (disposed || lost) return
    if (steady && prevNow >= 0) governor.push(now - prevNow, intervalMs)
    frame.dt = prevNow < 0 ? 0 : Math.min(0.1, (now - prevNow) / 1000)
    frame.time += frame.dt
    prevNow = now

    const verdict = governor.tick(now, mode !== 'auto')
    if (verdict && verdict.step !== 0) applyRung(rung - verdict.step, 'regulador')
    // ¿Toca pasar a reposo?
    updateInterval()

    renderer.info.reset()
    renderer.setRenderTarget(null)
    renderer.setScissorTest(false)
    renderer.setViewport(0, 0, frame.width, frame.height)
    renderer.clear(true, true, false)
    for (const e of entries) if (e.ready) e.layer.update(frame)
    for (const e of entries) {
      if (!e.ready) continue
      e.layer.render(frame)
      // Una capa que olvide restaurar el viewport no descoloca a las siguientes.
      renderer.setRenderTarget(null)
      renderer.setScissorTest(false)
      renderer.setViewport(0, 0, frame.width, frame.height)
    }
    bloom?.render(renderer)
    calls = renderer.info.render.calls
    tris = renderer.info.render.triangles

    framesInSecond++
    lastDrawAt = now
    if (now - secondStart >= 1000) {
      fps = (framesInSecond * 1000) / (now - secondStart)
      framesInSecond = 0
      secondStart = now
    }
  }

  const loop = createLoop(draw)

  // Entrada y ciclo de vida de la ventana.
  const onPointer = (e: PointerEvent): void => {
    frame.pointer.x = (e.clientX / Math.max(1, window.innerWidth)) * 2 - 1
    frame.pointer.y = 1 - (e.clientY / Math.max(1, window.innerHeight)) * 2
    frame.pointer.active = true
    if (performance.now() - lastActivity > 250) markActivity()
  }
  const onMouseOut = (e: MouseEvent): void => {
    if (e.relatedTarget === null) frame.pointer.active = false
  }
  const onVisibility = (): void => {
    if (document.hidden) {
      loop.pause()
      return
    }
    prevNow = -1 // sin salto de dt al volver
    governor.reset(performance.now())
    loop.resume()
    markActivity()
  }
  const onFocus = (): void => {
    focused = true
    markActivity()
  }
  const onBlur = (): void => {
    focused = false
    frame.pointer.active = false
    updateInterval()
  }
  const onLost = (): void => {
    lost = true
    loop.pause()
  }
  const onRestored = (): void => {
    lost = false
    prevNow = -1
    applySize()
    loop.resume()
    markActivity()
  }
  let dprQuery: MediaQueryList | null = null
  const onDpr = (): void => {
    watchDpr()
    applySize()
  }
  const watchDpr = (): void => {
    dprQuery?.removeEventListener('change', onDpr)
    dprQuery = window.matchMedia(`(resolution: ${window.devicePixelRatio || 1}dppx)`)
    dprQuery.addEventListener('change', onDpr)
  }
  const resizeObserver = new ResizeObserver(() => {
    applySize()
    markActivity()
  })

  window.addEventListener('pointermove', onPointer, { passive: true })
  window.addEventListener('mouseout', onMouseOut)
  window.addEventListener('focus', onFocus)
  window.addEventListener('blur', onBlur)
  document.addEventListener('visibilitychange', onVisibility)
  canvas.addEventListener('webglcontextlost', onLost)
  canvas.addEventListener('webglcontextrestored', onRestored)
  resizeObserver.observe(canvas)
  watchDpr()

  applyRung(0, 'manual')
  if (document.hidden) loop.pause()

  const ready = (async () => {
    // Las capas añadidas en el mismo turno que `createStage` entran en `ready`.
    await new Promise((resolve) => setTimeout(resolve, 0))
    while (pendingInits.length) await Promise.allSettled(pendingInits.splice(0))
    readySettled = true
  })()

  const removeEntry = (entry: Entry): void => {
    const i = entries.indexOf(entry)
    if (i >= 0) entries.splice(i, 1)
    entry.layer.dispose()
  }

  const stage: Stage = {
    ready,
    add(layer) {
      if (disposed) return
      stage.remove(layer.id)
      const entry: Entry = { layer, ready: false }
      // Orden ascendente estable: a igual `order`, la que entró antes se dibuja antes.
      let i = entries.length
      while (i > 0 && entries[i - 1]!.layer.order > layer.order) i--
      entries.splice(i, 0, entry)
      const init = Promise.resolve()
        .then(() => layer.init(frame))
        .then(
          () => {
            if (disposed || !entries.includes(entry)) return
            entry.ready = true
            layer.setQuality?.(frame.quality)
            layer.resize?.(frame)
            markActivity()
            loop.request()
          },
          (reason: unknown) => {
            console.warn(`[drakter:jarvis] la capa ${layer.id} no pudo iniciarse`, reason)
            if (entries.includes(entry)) removeEntry(entry)
          }
        )
      if (!readySettled) pendingInits.push(init)
    },
    remove(id) {
      const entry = entries.find((e) => e.layer.id === id)
      if (entry) removeEntry(entry)
      loop.request()
    },
    setQuality(tier) {
      mode = tier
      ladder = ladderFrom(startTier())
      applyRung(0, 'manual')
      markActivity()
    },
    setReducedMotion(on) {
      frame.reducedMotion = on
      loop.request()
    },
    requestFrame() {
      loop.request()
    },
    anchor(id): StageAnchor | null {
      for (const e of entries) {
        if (!e.ready || !e.layer.anchors) continue
        const a = e.layer.anchors()[id]
        if (a) return a
      }
      return null
    },
    stats(): StageStats {
      // A demanda o parado no hay fotogramas nuevos: el último valor ya no vale.
      const live = lastDrawAt >= 0 && performance.now() - lastDrawAt < 1500
      return { fps: live ? fps : 0, p90ms: governor.p90ms, tier: frame.quality.tier, renderScale: frame.renderScale, calls, tris }
    },
    dispose() {
      if (disposed) return
      disposed = true
      loop.dispose()
      window.removeEventListener('pointermove', onPointer)
      window.removeEventListener('mouseout', onMouseOut)
      window.removeEventListener('focus', onFocus)
      window.removeEventListener('blur', onBlur)
      document.removeEventListener('visibilitychange', onVisibility)
      canvas.removeEventListener('webglcontextlost', onLost)
      canvas.removeEventListener('webglcontextrestored', onRestored)
      dprQuery?.removeEventListener('change', onDpr)
      resizeObserver.disconnect()
      for (const e of entries.splice(0)) e.layer.dispose()
      bloom?.dispose()
      bloom = null
      // Sin forceContextLoss: en desarrollo React monta dos veces sobre el mismo lienzo.
      renderer.dispose()
    }
  }
  return stage
}

/** Para diagnóstico y para la ruta «HUD sin lienzo»: ¿hay WebGL2 y qué GPU? */
export { detectGpu }
