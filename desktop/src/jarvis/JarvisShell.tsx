import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState, type LazyExoticComponent } from 'react'
import { Check, ChevronDown } from 'lucide-react'
import { JARVIS_LAYOUTS } from '@/app/jarvisLayouts'
import { UI_MODE_SHORTCUT, UI_MODE_SHORTCUT_LABEL } from '@/app/useGlobalShortcuts'
import { useReducedMotion } from '@/app/useReducedMotion'
import { listAvatars, NO_AVATAR, useActiveAvatar, type AvatarEntry } from '@/character/avatars/registry'
import type { AvatarViewport } from '@/character/avatars/types'
import { useAvatarWiring } from '@/character/avatars/wiring'
import { CHARACTER_STATE_LABELS } from '@/character/labels'
import { FloatingButton } from '@/floating'
import { navigateTo, useCurrentSection } from '@/navigation/route'
import { SECTIONS } from '@/navigation/sections'
import { useDrakterState } from '@/stores/agent'
import { requestAppearance } from '@/stores/appearance'
import { usePreferences } from '@/stores/preferences'
import { requestUiMode, setLeaveTransition, settleUiMode } from '@/stores/uiMode'
import { availableLayouts, layoutLoader, resolveLayout } from './layouts/registry'
import type { JarvisAvatarSlot, JarvisLayout, JarvisLayoutId } from './layouts/types'
import { createStage } from './stage/createStage'
import { createAvatarStageLayer, type AvatarStageLayer } from './stage/layers/avatar'
import type { QualityTier, Stage, StageFrame } from './stage/types'

/** Si la interfaz no avisa de que ya se ve, la transición se cierra igualmente (Drakter no queda debajo). */
const READY_TIMEOUT_MS = 4000
const AVATAR_ANCHOR = 'avatar'
/** Selector rápido de interfaz y avatar. */
const PICKER_SHORTCUT = 'Control+Shift+A'

// Fondo de respaldo en CSS (sin lienzo): retícula fina y halo central. Coste de GPU ~0.
const BACKDROP = [
  'radial-gradient(ellipse at 50% 45%, rgba(56, 189, 248, 0.16), transparent 60%)',
  'linear-gradient(rgba(125, 211, 252, 0.06) 1px, transparent 1px)',
  'linear-gradient(90deg, rgba(125, 211, 252, 0.06) 1px, transparent 1px)'
].join(', ')

/** Recuadro por defecto del avatar: centrado, 60 % del lado menor. */
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

/** El Stage único (o `null` sin WebGL2 o con el contexto perdido). */
function useStage(canvas: HTMLCanvasElement | null) {
  const { jarvisQuality } = usePreferences()
  const reducedMotion = useReducedMotion()
  const [stage, setStage] = useState<Stage | null>(null)
  const [tier, setTier] = useState<QualityTier>('equilibrado')
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
    const onLost = (): void => setStage(null)
    canvas.addEventListener('webglcontextlost', onLost)
    const timer = setInterval(() => setTier(created.stats().tier), 2000)
    setTier(created.stats().tier)
    setStage(created)
    return () => {
      clearInterval(timer)
      canvas.removeEventListener('webglcontextlost', onLost)
      setStage(null)
      created.dispose()
    }
  }, [canvas])

  useEffect(() => stage?.setQuality(jarvisQuality), [stage, jarvisQuality])
  useEffect(() => stage?.setReducedMotion(reducedMotion), [stage, reducedMotion])

  return { stage, tier, reducedMotion }
}

/** Capa del avatar elegido (`avatarId`) en el Stage; cambiar de avatar sustituye la capa. */
function useAvatarLayer(stage: Stage | null, entry: AvatarEntry | null) {
  const [layer, setLayer] = useState<AvatarStageLayer | null>(null)
  const viewportRef = useRef<((frame: StageFrame) => AvatarViewport) | null>(null)

  useEffect(() => {
    const load = entry?.loadLayer
    if (!stage || !load) return
    const created = createAvatarStageLayer({
      load,
      viewport: (frame) => viewportRef.current?.(frame) ?? centeredViewport(frame),
      transparent: true
    })
    stage.add(created)
    setLayer(created)
    return () => {
      setLayer(null)
      stage.remove(created.id) // la libera
    }
  }, [stage, entry])

  return { layer, viewportRef }
}

/** 0…9 sin modificadores cambian de sección en Jarvis (mismo mapa que la barra de Drakter). */
function useSectionKeys(): void {
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent): void {
      if (event.ctrlKey || event.altKey || event.metaKey || event.shiftKey || event.repeat) return
      const target = event.target as HTMLElement | null
      if (target?.closest('input, textarea, select, [contenteditable=""], [contenteditable="true"], [role="dialog"]')) return
      const section = SECTIONS.find((candidate) => candidate.shortcut === event.key)
      if (!section) return
      event.preventDefault()
      navigateTo(section.id)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])
}

const pickerItem =
  'flex w-full items-center justify-between rounded px-2 py-1.5 text-left text-xs text-sky-100 outline-none hover:bg-sky-400/15 focus-visible:bg-sky-400/15'

/** Selector rápido común: interfaz Jarvis y avatar. Ctrl+Shift+A lo abre y lo cierra; Escape lo cierra. */
function AppearancePicker({ layoutId }: { readonly layoutId: JarvisLayoutId | null }) {
  const [open, setOpen] = useState(false)
  const { avatarId } = usePreferences()
  const layouts = availableLayouts()
  const avatars = listAvatars()

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent): void {
      if (event.key === 'Escape') setOpen(false)
      if (!event.ctrlKey || !event.shiftKey || event.altKey || event.metaKey || event.code !== 'KeyA') return
      event.preventDefault()
      setOpen((value) => !value)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  const pick = (request: Parameters<typeof requestAppearance>[0]): void => {
    setOpen(false)
    requestAppearance(request, 'button')
  }

  return (
    <div className="relative">
      <button
        type="button"
        aria-haspopup="true"
        aria-expanded={open}
        aria-keyshortcuts={PICKER_SHORTCUT}
        onClick={() => setOpen((value) => !value)}
        className="flex items-center gap-1.5 rounded-md border border-sky-400/40 bg-sky-950/60 px-3 py-1.5 text-xs tracking-wide text-sky-100 outline-none hover:bg-sky-900/60 focus-visible:ring-2 focus-visible:ring-sky-300"
      >
        Apariencia
        <ChevronDown className="size-3.5" aria-hidden="true" />
      </button>
      {open ? (
        <div className="absolute right-0 mt-1 w-60 rounded-md border border-sky-400/40 bg-[#03101c] p-1 shadow-[0_0_24px_rgba(56,189,248,0.2)]">
          <p className="px-2 pt-1 pb-0.5 font-mono text-[10px] tracking-[0.2em] text-sky-300/70 uppercase">Interfaz</p>
          <ul>
            {JARVIS_LAYOUTS.filter((info) => layouts.includes(info.id)).map((info) => (
              <li key={info.id}>
                <button type="button" className={pickerItem} onClick={() => pick({ layout: info.id })}>
                  {info.name}
                  {info.id === layoutId ? <Check className="size-3.5" aria-label="actual" /> : null}
                </button>
              </li>
            ))}
          </ul>
          <p className="px-2 pt-2 pb-0.5 font-mono text-[10px] tracking-[0.2em] text-sky-300/70 uppercase">Avatar</p>
          <ul>
            {avatars.map((entry) => (
              <li key={entry.meta.id}>
                <button type="button" className={pickerItem} onClick={() => pick({ avatar: entry.meta.id })}>
                  {entry.meta.name}
                  {entry.meta.id === avatarId ? <Check className="size-3.5" aria-label="actual" /> : null}
                </button>
              </li>
            ))}
            <li>
              <button type="button" className={pickerItem} onClick={() => pick({ avatar: NO_AVATAR })}>
                Ninguno (personaje clásico)
                {avatarId === NO_AVATAR ? <Check className="size-3.5" aria-label="actual" /> : null}
              </button>
            </li>
          </ul>
        </div>
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
 * Shell del modo Jarvis: anfitrión de las interfaces (contrato y decisiones en `jarvis/layouts/types.ts`).
 * Crea el ÚNICO lienzo y el Stage, la capa del avatar elegido y elige la interfaz (`jarvisLayout`);
 * captura las teclas de sección y pone la vuelta a Drakter y el selector rápido. Todo lo de sesión
 * (voz, avisos, confirmaciones) sigue vivo en `SessionHosts`.
 */
export default function JarvisShell() {
  const [canvas, setCanvas] = useState<HTMLCanvasElement | null>(null)
  const { stage, tier, reducedMotion } = useStage(canvas)
  const avatarEntry = useActiveAvatar()
  const { layer: avatarLayer, viewportRef } = useAvatarLayer(stage, avatarEntry)
  const { jarvisLayout } = usePreferences()
  const section = useCurrentSection()
  const agentState = useDrakterState()
  useAvatarWiring(avatarLayer?.controls ?? null, agentState)
  useSectionKeys()

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

  // La secuencia de salida es de la interfaz que está montada; al cambiar de interfaz o desmontar, se borra.
  useEffect(() => () => setLeaveTransition(null), [layoutId])

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
              setExitTransition={setLeaveTransition}
            />
          ) : (
            <FallbackLayout onReady={onReady} />
          )}
        </Suspense>
      </div>

      {/* Común a todas las interfaces: esquina superior derecha reservada. */}
      <div className="absolute top-4 right-4 z-10 flex items-center gap-2">
        <FloatingButton variant="jarvis" />
        <AppearancePicker layoutId={layoutId} />
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
