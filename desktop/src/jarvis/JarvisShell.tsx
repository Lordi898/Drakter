import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState, type LazyExoticComponent } from 'react'
import { Check, ChevronDown } from 'lucide-react'
import { jarvisLayoutInfo, JARVIS_LAYOUTS } from '@/app/jarvisLayouts'
import { UI_MODE_SHORTCUT, UI_MODE_SHORTCUT_LABEL } from '@/app/useGlobalShortcuts'
import { useReducedMotion } from '@/app/useReducedMotion'
import { activeAvatar } from '@/character/avatars/registry'
import type { AvatarViewport } from '@/character/avatars/types'
import { useAvatarWiring } from '@/character/avatars/wiring'
import { CHARACTER_STATE_LABELS } from '@/character/labels'
import { navigateTo, useCurrentSection } from '@/navigation/route'
import { useDrakterState } from '@/stores/agent'
import { requestAppearance } from '@/stores/appearance'
import { usePreferences } from '@/stores/preferences'
import { requestUiMode, settleUiMode } from '@/stores/uiMode'
import { availableLayouts, layoutLoader, resolveLayout } from './layouts/registry'
import type { JarvisAvatarSlot, JarvisLayout, JarvisLayoutId } from './layouts/types'
import { createStage } from './stage/createStage'
import { createAvatarStageLayer, type AvatarStageLayer } from './stage/layers/avatar'
import type { QualityTier, Stage, StageFrame } from './stage/types'

/** Si la interfaz no avisa de que ya se ve, la transición se cierra igualmente (Drakter no queda debajo). */
const READY_TIMEOUT_MS = 4000
const AVATAR_ANCHOR = 'avatar'

// Fondo de respaldo en CSS (sin lienzo): retícula fina y halo central. Coste de GPU ~0.
const BACKDROP = [
  'radial-gradient(ellipse at 50% 45%, rgba(56, 189, 248, 0.16), transparent 60%)',
  'linear-gradient(rgba(125, 211, 252, 0.06) 1px, transparent 1px)',
  'linear-gradient(90deg, rgba(125, 211, 252, 0.06) 1px, transparent 1px)'
].join(', ')

/** Recuadro por defecto del avatar: centrado, 60 % del alto. */
function centeredViewport(frame: StageFrame): AvatarViewport {
  const side = Math.round(Math.min(frame.width, frame.height) * 0.6)
  return { x: Math.round((frame.width - side) / 2), y: Math.round((frame.height - side) / 2), width: side, height: side }
}

// Un componente diferido por interfaz, creado una vez: cambiar de interfaz no vuelve a descargar la anterior.
const lazyLayouts = new Map<JarvisLayoutId, LazyExoticComponent<JarvisLayout>>()
function layoutComponent(id: JarvisLayoutId): LazyExoticComponent<JarvisLayout> | null {
  const load = layoutLoader(id)
  if (!load) return null
  let component = lazyLayouts.get(id)
  if (!component) {
    component = lazy(load)
    lazyLayouts.set(id, component)
  }
  return component
}

/** El Stage único (o `null` sin WebGL2) y la capa del avatar activo. */
function useStage(canvas: HTMLCanvasElement | null) {
  const { jarvisQuality } = usePreferences()
  const reducedMotion = useReducedMotion()
  const [stage, setStage] = useState<Stage | null>(null)
  const [avatarLayer, setAvatarLayer] = useState<AvatarStageLayer | null>(null)
  const [tier, setTier] = useState<QualityTier>('equilibrado')
  const viewportRef = useRef<((frame: StageFrame) => AvatarViewport) | null>(null)
  const initial = useRef({ jarvisQuality, reducedMotion })

  useEffect(() => {
    if (!canvas) return
    let created: Stage
    try {
      created = createStage(canvas, { quality: initial.current.jarvisQuality, reducedMotion: initial.current.reducedMotion })
    } catch (reason) {
      console.warn('[drakter:jarvis] sin WebGL2: interfaz sin lienzo', reason)
      return
    }
    // TODO(A1): `avatarEntry(avatarId)` cuando el registro de avatares lea la preferencia.
    const entry = activeAvatar
    const layer = entry?.loadLayer
      ? createAvatarStageLayer({
          load: entry.loadLayer,
          viewport: (frame) => viewportRef.current?.(frame) ?? centeredViewport(frame),
          transparent: true
        })
      : null
    if (layer) created.add(layer)
    const onLost = (): void => setStage(null)
    canvas.addEventListener('webglcontextlost', onLost)
    const timer = setInterval(() => setTier(created.stats().tier), 2000)
    setTier(created.stats().tier)
    setStage(created)
    setAvatarLayer(layer)
    return () => {
      clearInterval(timer)
      canvas.removeEventListener('webglcontextlost', onLost)
      setStage(null)
      setAvatarLayer(null)
      created.dispose()
    }
  }, [canvas])

  useEffect(() => stage?.setQuality(jarvisQuality), [stage, jarvisQuality])
  useEffect(() => stage?.setReducedMotion(reducedMotion), [stage, reducedMotion])

  return { stage, avatarLayer, tier, reducedMotion, viewportRef }
}

function LayoutPicker({ current }: { readonly current: JarvisLayoutId }) {
  const [open, setOpen] = useState(false)
  const available = availableLayouts()
  if (available.length < 2) return null
  const choose = (id: JarvisLayoutId): void => {
    setOpen(false)
    requestAppearance({ layout: id }, 'button')
  }
  return (
    <div className="relative">
      <button
        type="button"
        aria-haspopup="true"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 rounded-md border border-sky-400/40 bg-sky-950/60 px-3 py-1.5 text-xs tracking-wide text-sky-100 outline-none hover:bg-sky-900/60 focus-visible:ring-2 focus-visible:ring-sky-300"
      >
        Interfaz: {jarvisLayoutInfo(current).name}
        <ChevronDown className="size-3.5" aria-hidden="true" />
      </button>
      {open ? (
        <ul className="absolute right-0 mt-1 w-56 rounded-md border border-sky-400/40 bg-[#03101c] p-1 shadow-[0_0_24px_rgba(56,189,248,0.2)]">
          {JARVIS_LAYOUTS.filter((info) => available.includes(info.id)).map((info) => (
            <li key={info.id}>
              <button
                type="button"
                onClick={() => choose(info.id)}
                className="flex w-full items-center justify-between rounded px-2 py-1.5 text-left text-xs text-sky-100 outline-none hover:bg-sky-400/15 focus-visible:bg-sky-400/15"
              >
                {info.name}
                {info.id === current ? <Check className="size-3.5" aria-label="actual" /> : null}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}

/** Sin interfaz instalada: fondo, estado del agente y la vuelta. Avisa de que ya se ve. */
function FallbackLayout({ onReady }: { readonly onReady: () => void }) {
  const state = useDrakterState()
  useEffect(() => onReady(), [onReady])
  return (
    <div className="flex size-full flex-col items-center justify-center gap-3 text-center">
      <p className="font-mono text-xs tracking-[0.4em] text-sky-300/70 uppercase">Drakter</p>
      <h1 className="text-4xl font-light tracking-[0.25em] text-sky-50 uppercase [text-shadow:0_0_18px_rgba(56,189,248,0.55)]">
        Modo Jarvis
      </h1>
      <p className="max-w-[46ch] text-sm text-sky-200/75">
        La interfaz holográfica está en construcción. La voz, los avisos y las confirmaciones siguen funcionando
        como siempre.
      </p>
      <p className="font-mono text-xs text-sky-300/80" role="status">
        Estado: {CHARACTER_STATE_LABELS[state]}
      </p>
    </div>
  )
}

/**
 * Shell del modo Jarvis: anfitrión de las interfaces (`jarvis/layouts/types.ts`). Crea el ÚNICO lienzo y
 * el Stage, la capa del avatar elegido y elige la interfaz (`jarvisLayout`); pone la vuelta a Drakter y
 * el selector rápido. Todo lo de sesión (voz, avisos, confirmaciones) sigue vivo en `SessionHosts`.
 */
export default function JarvisShell() {
  const [canvas, setCanvas] = useState<HTMLCanvasElement | null>(null)
  const { stage, avatarLayer, tier, reducedMotion, viewportRef } = useStage(canvas)
  const { jarvisLayout } = usePreferences()
  const section = useCurrentSection()
  const agentState = useDrakterState()
  useAvatarWiring(avatarLayer?.controls ?? null, agentState)

  const layoutId = resolveLayout(jarvisLayout)
  const Layout = layoutId ? layoutComponent(layoutId) : null

  const settled = useRef(false)
  const onReady = useCallback(() => {
    if (settled.current) return
    settled.current = true
    requestAnimationFrame(() => settleUiMode('ready'))
  }, [])
  useEffect(() => {
    const timer = setTimeout(onReady, READY_TIMEOUT_MS)
    return () => clearTimeout(timer)
  }, [onReady])

  const exit = useCallback(() => requestUiMode('drakter', 'button'), [])

  const avatar = useMemo<JarvisAvatarSlot>(
    () => ({
      setViewport: (get) => {
        viewportRef.current = get
      },
      anchorId: AVATAR_ANCHOR,
      available: avatarLayer !== null
    }),
    [avatarLayer, viewportRef]
  )

  return (
    <main
      aria-label="Modo Jarvis"
      className="dark relative size-full animate-in overflow-hidden bg-[#02060c] text-sky-100 duration-500 fade-in"
      style={stage ? undefined : { backgroundImage: BACKDROP, backgroundSize: '100% 100%, 48px 48px, 48px 48px' }}
    >
      <canvas ref={setCanvas} />
      {/* El lienzo es `position: fixed`: el HUD va en una capa posicionada encima. */}
      <div className="absolute inset-0">
        <Suspense fallback={null}>
          {Layout && layoutId ? (
            <Layout
              key={layoutId}
              stage={stage}
              avatar={avatar}
              quality={tier}
              reducedMotion={reducedMotion}
              section={section}
              navigate={navigateTo}
              onReady={onReady}
              exit={exit}
            />
          ) : (
            <FallbackLayout onReady={onReady} />
          )}
        </Suspense>
      </div>

      {/* Común a todas las interfaces: esquina superior derecha reservada. */}
      <div className="absolute top-4 right-4 z-10 flex items-center gap-2">
        {layoutId ? <LayoutPicker current={layoutId} /> : null}
        <button
          type="button"
          autoFocus
          aria-keyshortcuts={UI_MODE_SHORTCUT}
          onClick={exit}
          className="rounded-md border border-sky-400/50 bg-sky-400/10 px-3 py-1.5 text-xs font-medium tracking-wide text-sky-50 shadow-[0_0_18px_rgba(56,189,248,0.25)] outline-none hover:bg-sky-400/20 focus-visible:ring-2 focus-visible:ring-sky-300"
        >
          Volver a Drakter
          <span className="ml-2 font-mono text-[10px] text-sky-300/80">{UI_MODE_SHORTCUT_LABEL}</span>
        </button>
      </div>
    </main>
  )
}
