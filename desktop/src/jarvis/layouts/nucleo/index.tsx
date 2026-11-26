/**
 * Interfaz «Núcleo» del modo Jarvis (por defecto): un astrolabio de luz alrededor de Drakter. Cada
 * anillo es un instrumento con datos REALES del Workspace (`jarvis/data`); al elegir una sección, su
 * anillo se despliega y se abren cuatro paneles radiales. Las acciones usan `modules/<x>/api.ts`; las
 * confirmaciones van por `stores/confirmations` (diálogo nativo de main, lo sirve `SessionHosts`).
 * Concepto y prototipo: drakter-97 (`research/jarvis-hud/nucleo`); extras de Visor: telemetría,
 * retícula de fijación, alertas y estado de error en rojo.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useDrakterState } from '@/stores/agent'
import { useLinkStatus } from '@/stores/connection'
import { sendMessage, useChatMessages } from '@/stores/chat'
import { describeError } from '@/services/api'
import { completeTask, getTask, reopenTask } from '@/modules/tasks/api'
import { registerRecord } from '@/modules/habits/api'
import { todayIn } from '@/modules/habits/dates'
import type { EntityType } from '@/modules/relationships/types'
import type { SectionId } from '@/navigation/sections'
import { acquireAudioTaps } from '@/voice/levels'
import { useJarvisData } from '@/jarvis/data'
import type { JarvisLayoutProps } from '../types'
import { createBackdropLayer, createVignetteLayer } from './gl/backdrop'
import { createNucleoScene, type NucleoScene } from './gl/scene'
import { Alerts, Overlay, useAlerts, type OverlayApi } from './hud/Overlay'
import { LeftColumn, RightColumn, SayForm } from './hud/Columns'
import { panelsFor, type Acts } from './hud/content'
import { Icon, type IconKey } from './hud/icons'
import { RadialPanels } from './hud/Panels'
import { TopBar } from './hud/TopBar'
import { buildModel, IdMap, type VTask } from './model'
import type { ModuleId, Tip } from './modules/base'
import type { RelState } from './modules/relaciones'
import './nucleo.css'

const TOPICS = ['today', 'tasks', 'projects', 'habits', 'habitHistory', 'agenda', 'timetable', 'subjects', 'relationships', 'entityNames', 'resources', 'folders'] as const

const SECTION_TO_MODULE: Partial<Record<SectionId, ModuleId>> = {
  today: 'hoy', tasks: 'tareas', projects: 'tareas', habits: 'habitos', calendar: 'calendario', subjects: 'calendario', relationships: 'relaciones', storage: 'almacen'
}
const MODULE_TO_SECTION: Record<ModuleId, SectionId> = { hoy: 'today', tareas: 'tasks', habitos: 'habits', calendario: 'calendar', relaciones: 'relationships', almacen: 'storage' }
/**
 * Los dígitos 0…9 los captura `JarvisShell` (contrato J1) con el mapa de `navigation/sections.ts`; aquí solo se
 * muestran. `key` debe coincidir con ese mapa (y con `key` de cada módulo, que sale en la descripción del anillo).
 */
const NAV: readonly { id: ModuleId | null; section: SectionId; name: string; icon: IconKey; key: string }[] = [
  { id: null, section: 'home', name: 'Núcleo', icon: 'nucleo', key: '1' },
  { id: 'hoy', section: 'today', name: 'Hoy', icon: 'hoy', key: '0' },
  { id: 'tareas', section: 'tasks', name: 'Tareas', icon: 'tareas', key: '3' },
  { id: 'habitos', section: 'habits', name: 'Hábitos', icon: 'habitos', key: '2' },
  { id: 'calendario', section: 'calendar', name: 'Calendario', icon: 'calendario', key: '6' },
  { id: 'relaciones', section: 'relationships', name: 'Relaciones', icon: 'relaciones', key: '8' },
  { id: 'almacen', section: 'storage', name: 'Almacén', icon: 'almacen', key: '5' }
]
const TITLE: Record<ModuleId, string> = { hoy: 'Hoy', tareas: 'Tareas y proyectos', habitos: 'Hábitos', calendario: 'Calendario y asignaturas', relaciones: 'Relaciones', almacen: 'Almacén' }
const IDLE_MS = 8000

export default function NucleoLayout({ stage, avatar, quality, reducedMotion, section, navigate, onReady, setExitTransition }: JarvisLayoutProps) {
  const data = useJarvisData(TOPICS)
  const state = useDrakterState()
  const link = useLinkStatus()
  const messages = useChatMessages()
  const ids = useRef(new IdMap()).current
  const [root, setRoot] = useState<HTMLDivElement | null>(null)
  const [scene, setScene] = useState<NucleoScene | null>(null)
  const [on, setOn] = useState(false)
  const [focus, setFocus] = useState<ModuleId | null>(null)
  const [panelsShown, setPanelsShown] = useState(false)
  const [selTick, setSelTick] = useState(0)
  const [busy, setBusy] = useState<ReadonlySet<string>>(new Set())
  const [minute, setMinute] = useState(0)
  const [idle, setIdle] = useState(false)
  const [booting, setBooting] = useState(false)
  const overlay = useRef<OverlayApi>(null)
  const { alerts, push } = useAlerts()

  // ── Modelo de vista (puro) a partir de los datos reales; se rehace al minuto para mover «ahora».
  useEffect(() => { const id = setInterval(() => setMinute((m) => m + 1), 60_000); return () => clearInterval(id) }, [])
  const model = useMemo(() => buildModel({
    today: data.today.data, tasks: data.tasks.data, projects: data.projects.data, habits: data.habits.data, agenda: data.agenda.data,
    timetable: data.timetable.data, relationships: data.relationships.data, resources: data.resources.data, doneLocal: new Set(), ids,
    habitHistory: data.habitHistory.data, subjects: data.subjects.data, entityNames: data.entityNames.data, folders: data.folders.data
  }), [data.today.data, data.tasks.data, data.projects.data, data.habits.data, data.agenda.data, data.timetable.data, data.relationships.data, data.resources.data,
    data.habitHistory.data, data.subjects.data, data.entityNames.data, data.folders.data, ids, minute])
  const modelRef = useRef(model)
  modelRef.current = model

  // ── Escena en el Stage (si hay lienzo). Las fuentes del atlas se cargan antes.
  useEffect(() => {
    if (!stage) { onReady(); setOn(true); return }
    let disposed = false
    let created: NucleoScene | null = null
    const backdrop = createBackdropLayer(), vignette = createVignetteLayer()
    void (async () => {
      await Promise.all(['500 52px "Saira Condensed"', '400 16px "NX Saira"', '600 20px "NX Oxanium"'].map((f) => document.fonts.load(f).catch(() => undefined)))
      if (disposed) return
      created = createNucleoScene(ids, modelRef.current, {
        hover: (tip: Tip | null) => { overlay.current?.setTip(tip); document.body.style.cursor = tip ? 'pointer' : '' ; overlay.current?.setCanvasTarget(tip && created?.focus ? () => created!.target() : null) },
        focus: (id) => setFocus(id),
        action: (id, a) => {
          const m = modelRef.current
          if (a.kind === 'toggleTask') { const t = m.todayTasks?.find((x) => x.id === a.id) ?? m.tasks?.find((x) => x.id === a.id); if (t) toggleTaskRef.current(t) }
          else if (a.kind === 'toggleHabit') toggleHabitRef.current(a.id)
          void id
          setSelTick((n) => n + 1)
        },
        booted: () => setBooting(false)
      })
      stage.add(backdrop)
      stage.add(created)
      stage.add(vignette)
      backdrop.setOpacity(1)
      avatar.setViewport((f) => created!.avatarViewport(f))
      setScene(created)
      await stage.ready
      if (disposed) return
      if (!reducedMotion) setBooting(true)
      created.boot(reducedMotion)
      requestAnimationFrame(() => { onReady(); setOn(true) })
    })()
    return () => {
      disposed = true
      avatar.setViewport(null)
      stage.remove(vignette.id)
      if (created) stage.remove(created.id)
      stage.remove(backdrop.id)
      setScene(null)
      document.body.style.cursor = ''
    }
  }, [stage])

  useEffect(() => { scene?.setModel(model); setSelTick((n) => n + 1) }, [scene, model])
  useEffect(() => scene?.setAgentState(state), [scene, state])
  useEffect(() => scene?.setOrb(!avatar.available), [scene, avatar.available])
  useEffect(() => acquireAudioTaps(), [])
  // Ahorro en reposo dibuja a demanda: un fotograma al cambiar datos, estado o sección, y ritmo propio mientras hay voz o trabajo.
  useEffect(() => { stage?.requestFrame() }, [stage, model, state, focus, selTick])
  useEffect(() => {
    if (!stage || quality !== 'ahorro' || state === 'idle' || state === 'offline') return
    const id = setInterval(() => stage.requestFrame(), 100)
    return () => clearInterval(id)
  }, [stage, quality, state])

  // ── Sección común a los dos modos → anillo desplegado.
  const target = SECTION_TO_MODULE[section] ?? null
  useEffect(() => { if (scene) scene.go(target); else setFocus(target) }, [scene, target])
  useEffect(() => {
    setPanelsShown(false)
    if (!focus) return
    const id = setTimeout(() => setPanelsShown(true), reducedMotion ? 0 : 300)
    return () => clearTimeout(id)
  }, [focus, reducedMotion])
  // Clic en un anillo del núcleo: la escena lo despliega; la sección (hash) lo sigue.
  useEffect(() => { if (focus && focus !== target) navigate(MODULE_TO_SECTION[focus]) }, [focus])

  // ── Salida: los anillos se recogen hacia el núcleo.
  useEffect(() => {
    if (!scene || reducedMotion) { setExitTransition(null); return }
    setExitTransition(() => { setOn(false); return scene.collapse() })
    return () => setExitTransition(null)
  }, [scene, reducedMotion, setExitTransition])

  // ── Acciones reales.
  const markBusy = (id: string, v: boolean): void => setBusy((s) => { const n = new Set(s); if (v) n.add(id); else n.delete(id); return n })
  const toggleTaskRef = useRef<(t: VTask) => void>(() => undefined)
  toggleTaskRef.current = (t: VTask) => {
    if (busy.has(t.id)) return
    markBusy(t.id, true)
    void (async () => {
      try {
        const rev = t.revision ?? modelRef.current.tasks?.find((x) => x.id === t.id)?.revision ?? (await getTask(t.id)).revision
        if (t.done) await reopenTask(t.id, rev)
        else await completeTask(t.id, rev)
        push('ok', t.done ? 'Tarea reabierta' : 'Tarea completada', t.title)
        if (!t.done) scene?.shock('success')
        data.today.reload()
        data.tasks.reload()
        data.projects.reload()
      } catch (e) {
        push('error', 'No se pudo cambiar la tarea', describeError(e, 'Inténtalo de nuevo.'))
      } finally {
        markBusy(t.id, false)
      }
    })()
  }
  const toggleHabitRef = useRef<(id: string) => void>(() => undefined)
  toggleHabitRef.current = (id: string) => {
    const h = data.habits.data?.find((x) => x.id === id), vh = modelRef.current.habits?.find((x) => x.id === id)
    if (!h || !vh || busy.has(id)) return
    markBusy(id, true)
    void (async () => {
      try {
        await registerRecord(id, todayIn(h.timezone), vh.todayDone ? 'skipped' : 'done')
        push('ok', vh.todayDone ? `${h.name}: desmarcado` : `${h.name}: hecho`, vh.todayDone ? 'Queda como omitido hoy.' : vh.streak !== null ? `Racha: ${vh.streak + 1} días.` : 'Anotado en el registro de hoy.')
        if (!vh.todayDone) scene?.shock('success')
        data.habits.reload()
        data.habitHistory.reload()
        data.today.reload()
      } catch (e) {
        push('error', 'No se pudo marcar el hábito', describeError(e, 'Inténtalo de nuevo.'))
      } finally {
        markBusy(id, false)
      }
    })()
  }
  const acts: Acts = {
    busy,
    toggleTask: (t) => toggleTaskRef.current(t),
    toggleHabit: (id) => toggleHabitRef.current(id),
    select: (id, num) => {
      if (!scene) return
      const m = scene.module(id)
      if (id === 'almacen') m.def.click(num, scene.ctx, m as never)
      m.sel = num
      setSelTick((n) => n + 1)
    },
    filter: (type: EntityType | null) => {
      if (!scene) return
      const m = scene.module('relaciones')
      ;(m.s as RelState).filter = type
      m.sel = 0
      setSelTick((n) => n + 1)
    },
    say: (text) => { sendMessage(text).catch((e: unknown) => push('error', 'No se pudo enviar', describeError(e, 'Inténtalo de nuevo.'))) }
  }

  // ── Avisos reales: error del agente, enlace caído.
  const prevState = useRef(state)
  useEffect(() => {
    if (state === 'error' && prevState.current !== 'error') {
      const failed = [...messages].reverse().find((m) => m.status === 'failed')
      push('error', 'Algo ha fallado', failed?.error ?? 'El agente ha devuelto un error.')
    }
    prevState.current = state
  }, [state])
  const prevLink = useRef(link)
  useEffect(() => {
    if (link !== 'open' && prevLink.current === 'open') push('warn', 'Sin conexión con el servicio local', 'Reintento automático. Los datos muestran la última copia buena.')
    if (link === 'open' && (prevLink.current === 'reconnecting' || prevLink.current === 'disconnected')) push('ok', 'Conexión recuperada', 'El enlace con el backend vuelve a estar abierto.')
    prevLink.current = link
  }, [link])

  // ── Puntero y teclado. El lienzo no recibe eventos: se escuchan en la ventana y se descartan los del HUD.
  useEffect(() => {
    if (!root) return
    let idleTimer = 0
    const wake = (): void => { setIdle(false); clearTimeout(idleTimer); idleTimer = window.setTimeout(() => setIdle(true), IDLE_MS) }
    const overUi = (e: Event): boolean => !!(e.target as HTMLElement | null)?.closest?.('.ui, [role="dialog"], button, a, input')
    const parEls = root.querySelectorAll<HTMLElement>('.nx-colL, .nx-colR, .nx-panels')
    const move = (e: PointerEvent): void => {
      overlay.current?.move(e.clientX, e.clientY)
      scene?.pointer(e.clientX, e.clientY, !overUi(e))
      if (quality === 'cine' && !reducedMotion) { const pc = `${(((e.clientX / window.innerWidth) * 2 - 1) * -9).toFixed(1)}px ${(((e.clientY / window.innerHeight) * 2 - 1) * -5).toFixed(1)}px`; for (const el of parEls) el.style.translate = pc }
      wake()
    }
    const down = (e: PointerEvent): void => {
      wake()
      if (scene?.booting) { scene.skipBoot(); return }
      if (e.button !== 0 || overUi(e)) return
      scene?.pointerDown(e.clientX, e.clientY)
    }
    const up = (): void => { if (scene?.pointerUp()) setSelTick((n) => n + 1) }
    const leave = (): void => scene?.pointer(-1, -1, false)
    const key = (e: KeyboardEvent): void => {
      wake()
      if (scene?.booting) { scene.skipBoot(); return }
      const typing = (e.target as HTMLElement | null)?.closest?.('input, textarea, [contenteditable="true"], [role="dialog"]')
      if (e.defaultPrevented || typing || document.querySelector('[role="dialog"], [role="alertdialog"]') || e.ctrlKey || e.metaKey || e.altKey) return
      if (e.key === 'Escape' && focus) { e.preventDefault(); navigate('home') }
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
        const i = NAV.findIndex((n) => n.id === focus), n = NAV[(i + (e.key === 'ArrowRight' ? 1 : NAV.length - 1)) % NAV.length]!
        e.preventDefault()
        navigate(n.section)
      }
      if (e.key === '/') { e.preventDefault(); root.querySelector<HTMLInputElement>(focus ? '#nx-say-dock' : '#nx-say-main')?.focus() }
    }
    window.addEventListener('pointermove', move, { passive: true })
    window.addEventListener('pointerdown', down)
    window.addEventListener('pointerup', up)
    document.documentElement.addEventListener('pointerleave', leave)
    window.addEventListener('keydown', key)
    wake()
    return () => {
      clearTimeout(idleTimer)
      window.removeEventListener('pointermove', move)
      window.removeEventListener('pointerdown', down)
      window.removeEventListener('pointerup', up)
      document.documentElement.removeEventListener('pointerleave', leave)
      window.removeEventListener('keydown', key)
    }
  }, [root, scene, focus, quality, reducedMotion, navigate])

  const focusFrame = useCallback(() => scene?.focusFrame() ?? (root ? { cx: root.clientWidth / 2, cy: root.clientHeight / 2, r: root.clientHeight * 0.28, ry: root.clientHeight * 0.16 } : null), [scene, root])
  const mod = focus && scene ? scene.module(focus) : null
  const panels = focus && mod ? panelsFor(focus, model, mod, acts) : []
  const kpi = focus && scene ? scene.module(focus).def.kpi(scene.ctx) : ''
  const lastAgent = [...messages].reverse().find((m) => m.role === 'agent')
  const relCount = model.graph?.edges.length ?? null
  const bootLines = [
    `enlace con el Workspace · ${link === 'open' ? 'correcto' : 'reintentando'}`,
    `${model.tasks?.length ?? '…'} tareas · ${model.habits?.length ?? '…'} hábitos · ${relCount ?? '…'} vínculos`,
    'memoria cercada como dato no confiable',
    `avatar · ${avatar.available ? 'condensando' : 'orbe de reserva'}`,
    'astrolabio en línea'
  ]

  return (
    <div ref={setRoot} className={`nx ${on ? 'on' : ''} ${focus ? 'focus' : ''}`} data-state={state} data-quality={quality} data-idle={idle} data-reduced={reducedMotion}>
      <div className="nx-frame" />
      <TopBar state={state} stage={stage} tz={model.tz} />
      <LeftColumn state={state} />
      <RightColumn state={state} quality={quality} />
      <div className="nx-sect ui">
        <button type="button" className="nx-back" onClick={() => navigate('home')} data-lock="Volver al núcleo"><Icon k="nucleo" /><span>Núcleo</span><kbd>Esc</kbd></button>
        <h2>{focus ? TITLE[focus] : ''}</h2>
        <p>{kpi}</p>
      </div>
      <RadialPanels panels={panels} show={panelsShown} frame={focusFrame} version={`${focus}|${selTick}|${model.todayKey}|${panels.length}`} />
      <div className="nx-dock ui">
        <p className="last">{lastAgent?.status === 'failed' ? lastAgent.error ?? '' : lastAgent?.content.slice(0, 220) ?? ''}</p>
        <SayForm id="nx-say-dock" placeholder="Habla con Drakter…" />
      </div>
      <nav className="nx-nav ui" aria-label="Secciones">
        {NAV.map((n) => (
          <button key={n.section} type="button" aria-current={n.id === focus} onClick={() => navigate(n.section)} data-lock={`Ir a ${n.name} · tecla ${n.key}`}>
            <Icon k={n.icon} /><span>{n.name}</span><kbd>{n.key}</kbd>
          </button>
        ))}
      </nav>
      <Alerts alerts={alerts} />
      <BootLog active={booting} lines={bootLines} />
      <Overlay ref={overlay} reduced={reducedMotion} root={root} />
      {!stage ? <p className="nx-sr" role="status">Sin lienzo 3D: la interfaz funciona solo con paneles.</p> : null}
    </div>
  )
}

/** Registro de arranque: escribe las líneas carácter a carácter durante la secuencia (≤ 3,4 s) y se va. */
function BootLog({ active, lines }: { readonly active: boolean; readonly lines: readonly string[] }) {
  const logRef = useRef<HTMLDivElement>(null)
  const numRef = useRef<HTMLElement>(null)
  const linesRef = useRef(lines)
  linesRef.current = lines
  useEffect(() => {
    if (!active) return
    const total = linesRef.current.reduce((a, l) => a + l.length, 0), t0 = performance.now(), D = 2600
    let raf = 0
    const step = (now: number): void => {
      const k = Math.min(1, (now - t0) / D)
      let n = Math.floor(k * total)
      const log = logRef.current
      if (log) {
        log.replaceChildren()
        for (const l of linesRef.current) { if (n <= 0) break; const p = document.createElement('p'); p.textContent = l.slice(0, n); if (n >= l.length) p.className = 'ok'; log.append(p); n -= l.length }
      }
      if (numRef.current) numRef.current.textContent = String(Math.round(k * 100)).padStart(3, '0')
      if (k < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [active])
  return (
    <div className={`nx-boot ${active ? 'on' : ''}`} aria-hidden="true">
      <div className="nx-bootlog" ref={logRef} />
      <div className="nx-bootc"><b ref={numRef}>000</b><span>ensamblando el astrolabio</span></div>
    </div>
  )
}
