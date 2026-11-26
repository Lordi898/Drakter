/**
 * Interfaz Jarvis «Holomesa»: una mesa de operaciones holográfica en perspectiva donde cada sección del
 * Workspace es un holograma con datos reales. Escena 3D y etiquetas en el Stage único; HUD en DOM
 * estático encima (nada se mueve por fotograma desde React). Contrato: `jarvis/layouts/types.ts`.
 */
import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore, type PointerEvent } from 'react'
import { useJarvisData } from '@/jarvis/data'
import type { SectionId as AppSection } from '@/navigation/sections'
import { useDrakterState } from '@/stores/agent'
import { useJobs } from '@/stores/jobs'
import type { JarvisLayoutProps } from '../types'
import { buildSnapshot, HOLO_TOPICS } from './adapt'
import { DetailPanel, type ReloadTopic } from './hud/Detail'
import { AgentChip, Chat, Clock, Jobs, Rail, VoiceConsole } from './hud/parts'
import { SECTION_NAMES, SECTION_ORDER, TO_APP_SECTION, type PickInfo, type SectionId } from './model'
import { createHolomesaScene, type HolomesaView } from './scene/holomesaScene'
import './holomesa.css'

const TO_APP: Record<SectionId, AppSection> = TO_APP_SECTION
/** Sección común → estación. «Drakter» (la conversación) es la vista general de la mesa; Configuración no tiene estación. */
const FROM_APP: Partial<Record<AppSection, SectionId | null>> = { home: null, today: 'hoy', calendar: 'calendario', subjects: 'calendario', tasks: 'tareas', projects: 'proyectos', habits: 'habitos', relationships: 'relaciones', storage: 'almacen' }
const OVERVIEW: AppSection = 'home'

const EMPTY_METRICS = Object.fromEntries(SECTION_ORDER.map((id) => [id, ''])) as Record<SectionId, string>

const isTyping = (t: EventTarget | null): boolean =>
  t instanceof HTMLElement && (t.isContentEditable || t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT')

export default function Holomesa({ stage, avatar, reducedMotion, section, navigate, onReady, exit }: JarvisLayoutProps) {
  const [scene] = useState(() => createHolomesaScene(reducedMotion))
  useEffect(() => () => scene.dispose(), [scene])

  const data = useJarvisData(HOLO_TOPICS)
  const agent = useDrakterState()
  const jobs = useJobs()
  const view: HolomesaView = useSyncExternalStore(scene.subscribe, scene.getView)
  const [metrics, setMetrics] = useState<Record<SectionId, string>>(EMPTY_METRICS)
  const [booted, setBooted] = useState(false)
  const [bootMark, setBootMark] = useState(false)
  const [selected, setSelected] = useState<PickInfo | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const dockRef = useRef<HTMLDivElement>(null)
  const rootRef = useRef<HTMLDivElement>(null)

  // ── datos reales → escena (solo cuando cambia alguna instantánea)
  const snapshot = useMemo(
    () => buildSnapshot(data, new Date()),
    [data.today, data.tasks, data.projects, data.habits, data.habitHistory, data.agenda, data.relationships, data.resources, data.folders, data.subjects, data.entityNames]
  )
  useEffect(() => {
    scene.setData(snapshot)
    setMetrics(Object.fromEntries(scene.stations.map((s) => [s.id, s.metric])) as Record<SectionId, string>)
  }, [scene, snapshot])

  // La selección del holograma (clic) y la de la lista del panel comparten un mismo estado.
  useEffect(() => setSelected(view.selected), [view.selected])
  useEffect(() => setSelected(null), [view.focusId])

  // ── estado vivo
  useEffect(() => scene.setAgent(agent), [scene, agent])
  const indexing = jobs.some((j) => j.state === 'running' && /index/i.test(`${j.last_tool ?? ''} ${j.title}`))
  useEffect(() => scene.setIndexing(indexing), [scene, indexing])

  // ── Stage: capas propias, bombeo de fotogramas, avatar en la cabecera y aviso de «ya se ve»
  useEffect(() => {
    if (!stage) {
      // «HUD sin lienzo»: el DOM ya es la interfaz.
      onReady()
      return
    }
    stage.add(scene.world)
    stage.add(scene.overlay)
    scene.attach(() => stage.requestFrame())
    avatar.setViewport((frame) => scene.avatarViewport(frame))
    let cancelled = false
    void stage.ready.then(() => {
      if (!cancelled) requestAnimationFrame(() => onReady())
    })
    return () => {
      cancelled = true
      avatar.setViewport(null)
      scene.attach(null)
      stage.remove(scene.overlay.id)
      stage.remove(scene.world.id)
    }
    // `avatar` cambia de identidad cuando el avatar carga; solo hace falta volver a fijar el recuadro.
  }, [stage, scene, onReady])
  useEffect(() => {
    avatar.setViewport(stage ? (frame) => scene.avatarViewport(frame) : null)
  }, [avatar, stage, scene])

  // El orbe propio preside hasta que el avatar 3D se dibuja de verdad (su anclaje existe).
  useEffect(() => {
    scene.setAvatarReady(false)
    if (!stage || !avatar.available) return
    const timer = setInterval(() => {
      if (stage.anchor(avatar.anchorId)) {
        scene.setAvatarReady(true)
        clearInterval(timer)
      }
    }, 400)
    return () => clearInterval(timer)
  }, [stage, avatar.available, avatar.anchorId, scene])

  // ── arranque: siempre en la vista general (la mesa entera se revela); luego sigue a la sección común.
  useEffect(() => {
    const raf = requestAnimationFrame(() => setBooted(true))
    if (!reducedMotion) setBootMark(true)
    void scene.boot()
    return () => cancelAnimationFrame(raf)
    // Una sola vez al montar.
  }, [scene])

  // ── sección ↔ navegación común
  const go = useCallback(
    (id: SectionId | null) => {
      scene.focus(id)
      navigate(id ? TO_APP[id] : OVERVIEW)
    },
    [scene, navigate]
  )
  const lastSection = useRef(section)
  useEffect(() => {
    if (section === lastSection.current) return
    lastSection.current = section
    const id = FROM_APP[section]
    if (id !== undefined && id !== scene.getView().focusId) scene.focus(id)
  }, [section, scene])

  // ── teclado: los dígitos los gestiona el anfitrión (mapa común de secciones, 0…9); aquí Esc vista
  //    general, ←/→ estación anterior/siguiente y «/» para escribir.
  useEffect(() => {
    const onKey = (e: KeyboardEvent): void => {
      if (e.ctrlKey || e.metaKey || e.altKey || isTyping(e.target)) return
      const cur = scene.getView().focusId
      if (e.key === 'Escape') {
        if (cur) go(null)
      } else if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
        const i = cur ? SECTION_ORDER.indexOf(cur) : -1, n = SECTION_ORDER.length
        const next = e.key === 'ArrowRight' ? (i + 1) % n : i < 0 ? n - 1 : (i - 1 + n) % n
        go(SECTION_ORDER[next]!)
      } else if (e.key === '/') {
        e.preventDefault()
        inputRef.current?.focus()
      } else return
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [scene, go])

  // ── puntero sobre la escena (el resto del HUD no pica hologramas)
  const downAt = useRef({ x: 0, y: 0 })
  const onDown = (e: PointerEvent<HTMLDivElement>): void => {
    downAt.current = { x: e.clientX, y: e.clientY }
  }
  const onUp = (e: PointerEvent<HTMLDivElement>): void => {
    if (Math.hypot(e.clientX - downAt.current.x, e.clientY - downAt.current.y) > 6) return
    const before = scene.getView().focusId
    scene.click()
    const after = scene.getView().focusId
    if (after && after !== before) navigate(TO_APP[after])
  }

  // ── hueco del avatar junto a la consola de voz (se mide al cambiar el tamaño, no por fotograma)
  useEffect(() => {
    const el = dockRef.current
    if (!el) return
    const measure = (): void => {
      const r = el.getBoundingClientRect()
      scene.setDock(r.width > 0 ? { x: r.x, y: r.y, width: r.width, height: r.height } : null)
    }
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    window.addEventListener('resize', measure)
    const late = setTimeout(measure, 1200) // tras el despliegue del HUD
    return () => {
      ro.disconnect()
      window.removeEventListener('resize', measure)
      clearTimeout(late)
    }
  }, [scene])

  const reloaders: Record<ReloadTopic, () => void> = { tasks: data.tasks.reload, habits: data.habits.reload, today: data.today.reload }
  const reload = (t: ReloadTopic): void => {
    reloaders[t]()
    if (t === 'habits') data.habitHistory.reload()
  }
  const openInDrakter = (s: AppSection): void => {
    navigate(s)
    exit()
  }

  const focusName = view.focusId ? SECTION_NAMES[view.focusId] : null
  return (
    <div
      ref={rootRef}
      className={`hm st-${agent}${booted ? ' booted' : ''}${reducedMotion ? ' reduced' : ''}${view.focusId ? ' focused' : ''}`}
      data-quality={stage ? 'stage' : 'none'}
    >
      <div
        className="hm-catcher"
        aria-hidden="true"
        onPointerEnter={() => scene.setPointerInside(true)}
        onPointerLeave={() => scene.setPointerInside(false)}
        onPointerDown={onDown}
        onPointerUp={onUp}
      />
      {bootMark ? (
        <div className="hm-boot on" aria-hidden="true" onAnimationEnd={() => setBootMark(false)}>
          <div className="wm">HOLOMESA</div>
          <div className="wmsub">Drakter · modo Jarvis</div>
        </div>
      ) : null}

      <header className="hm-top hm-unfold">
        <div className="hm-mark">
          <svg viewBox="0 0 34 34" aria-hidden="true">
            <path d="M17 2l13 7.5v15L17 32 4 24.5v-15z" fill="none" stroke="#6fd6ff" />
            <path d="M12 10h5.5a7 7 0 010 14H12z" fill="none" stroke="#eafaff" strokeWidth="1.4" />
          </svg>
          <div>
            <div className="t1">DRAKTER</div>
            <div className="t2">Holomesa · modo Jarvis</div>
          </div>
        </div>
        <div className="hm-crumb" aria-live="polite">
          {focusName ? (
            <>Vista general / <b>{focusName}</b> · Esc para salir</>
          ) : (
            <>Vista general · <b>7 secciones</b> · clic, números o ←/→</>
          )}
        </div>
        <Clock timezone={snapshot.timezone} />
        <AgentChip state={agent} />
      </header>

      <Rail focus={view.focusId} metrics={metrics} onGo={go} />
      <Chat inputRef={inputRef} />
      <VoiceConsole state={agent} dockRef={dockRef} />
      <Jobs />
      <DetailPanel
        focus={view.focusId}
        snap={snapshot}
        selected={selected}
        onSelect={setSelected}
        reload={reload}
        openInDrakter={openInDrakter}
        onActionDone={() => scene.shock(0xffffff)}
      />
      {!stage ? (
        <p className="hm-state" style={{ position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%,-50%)' }} role="status">
          Sin aceleración gráfica: la mesa 3D no está disponible, pero todo el HUD sigue funcionando.
        </p>
      ) : null}
    </div>
  )
}
