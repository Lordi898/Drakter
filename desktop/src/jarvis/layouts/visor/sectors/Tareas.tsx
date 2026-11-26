/**
 * Sector Tareas y proyectos (rumbo 103°, secciones `tasks` y `projects`): skyline 3D con la carga de
 * cada proyecto en las 8 próximas semanas (tareas abiertas por semana de vencimiento), próximas
 * entregas, progreso de los proyectos e indicadores. «Abrir» lleva a la sección en Drakter.
 */
import { useContext, useEffect, useMemo, useRef } from 'react'
import { useJarvisData } from '@/jarvis/data'
import { drawProjects } from '../charts'
import { Panel, WorldContext } from '../Panel'
import { createSkyline, SKY_WEEKS, type SkylinePart } from '../stage/parts'
import { D, FAR, NEAR } from '../stage/world'
import { Chart2D, Kpis, PRIORITY_RANK, SnapNote, dayDiff, dueDay, localDay, plural, useMinute, useVisorNav } from './common'

const TOPICS = ['tasks', 'projects'] as const
const S = 2
const COLORS = ['#8be9ff', '#5fb4ff', '#e9fcff', '#3d8bff', '#a8f0ff', '#ffb547']
const MAX_PROJECTS = 6

/** Lunes de la semana de `day` ('AAAA-MM-DD'). */
function monday(day: string): string {
  const d = new Date(`${day}T12:00:00`)
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7))
  return localDay(d)
}

export function Tareas() {
  const { tasks, projects } = useJarvisData(TOPICS)
  const { openInDrakter } = useVisorNav()
  const world = useContext(WorldContext)
  const minute = useMinute()
  const today = useMemo(() => localDay(), [minute]) // eslint-disable-line react-hooks/exhaustive-deps
  const open = tasks.data ?? []

  const top = useMemo(() => {
    const list = [...(projects.data ?? [])]
    list.sort((a, b) => (PRIORITY_RANK[a.priority] ?? 9) - (PRIORITY_RANK[b.priority] ?? 9) || b.progress.open - a.progress.open)
    return list.slice(0, MAX_PROJECTS)
  }, [projects.data])

  // carga[p][semana] = tareas abiertas del proyecto que vencen esa semana (las vencidas cuentan en la actual)
  const load = useMemo(() => {
    const week0 = monday(today)
    const idx = new Map(top.map((p, i) => [p.id, i]))
    const cells = top.map(() => new Array<number>(SKY_WEEKS).fill(0))
    for (const t of open) {
      const i = t.project_id ? idx.get(t.project_id) : undefined
      const due = dueDay(t)
      if (i === undefined || !due) continue
      const w = Math.max(0, Math.floor(dayDiff(week0, due) / 7))
      if (w < SKY_WEEKS) cells[i]![w]!++
    }
    return cells
  }, [open, top, today])

  // 3D: el skyline vive en la capa; recibe datos solo cuando cambian.
  const partRef = useRef<SkylinePart | null>(null)
  const readRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!world) return
    const part = createSkyline(world)
    partRef.current = part
    return () => { part.dispose(); partRef.current = null }
  }, [world])
  useEffect(() => { partRef.current?.setData(load, top.map((_, i) => COLORS[i % COLORS.length]!)) }, [load, top, world])
  // Lectura de la columna bajo el cursor: solo con eventos del puntero y en este sector.
  useEffect(() => {
    if (!world) return
    let last = ''
    const onMove = (e: PointerEvent): void => {
      if (world.sector !== S || !readRef.current) return
      const b = partRef.current?.pick(e.clientX, e.clientY)
      const txt = b && top[b.proj] ? `${top[b.proj]!.name} · ${b.week === 0 ? 'esta semana' : `dentro de ${plural(b.week, 'semana', 'semanas')}`}: ${plural(load[b.proj]![b.week]!, 'tarea', 'tareas')}` : 'Pasa el cursor por una columna'
      if (txt !== last) { last = txt; readRef.current.textContent = txt }
    }
    addEventListener('pointermove', onMove, { passive: true })
    return () => removeEventListener('pointermove', onMove)
  }, [world, top, load])

  const upcoming = useMemo(() => open
    .map((t) => ({ t, due: dueDay(t) }))
    .filter((x): x is { t: typeof x.t; due: string } => x.due !== null)
    .sort((a, b) => a.due.localeCompare(b.due) || (PRIORITY_RANK[a.t.priority] ?? 9) - (PRIORITY_RANK[b.t.priority] ?? 9))
    .slice(0, 7), [open])
  const projName = useMemo(() => new Map((projects.data ?? []).map((p) => [p.id, p.name])), [projects.data])
  const overdue = open.filter((t) => { const d = dueDay(t); return d !== null && d < today }).length
  const soon = open.filter((t) => { const d = dueDay(t); return d !== null && d >= today && dayDiff(today, d) <= 3 }).length
  const rows = top.map((p, i) => ({ name: p.name, percent: p.progress.percent, open: p.progress.open, done: p.progress.completed, weeks: load[i] ?? [], color: COLORS[i % COLORS.length]! }))

  return (
    <>
      <Panel sector={S} R={FAR} y={30} w={780} h={560} alpha={0.35} title="Carga por proyecto, próximas 8 semanas" code="TAR-01" className="sky">
        <SnapNote snap={projects} empty="No hay proyectos activos." isEmpty={top.length === 0} />
        {!world && rows.map((r) => <div key={r.name} className="jv-visor-row"><b>{r.name}</b><span>{r.weeks.join(' · ')}</span></div>)}
        <div className="sky-leg">
          {top.map((p, i) => <span key={p.id} data-lock={`${p.name}  ${p.progress.percent} %`}><i style={{ background: COLORS[i % COLORS.length] }} />{p.name}</span>)}
        </div>
        <div className="sky-axis"><span>esta semana</span><span>+7 semanas</span></div>
        <div className="sky-read" ref={readRef}>Pasa el cursor por una columna</div>
      </Panel>

      <Panel sector={S} dA={-26} R={NEAR} y={10} w={330} h={470} side title="Próximas entregas" code="TAR-02">
        <SnapNote snap={tasks} empty="No hay tareas con fecha." isEmpty={upcoming.length === 0} />
        {upcoming.map(({ t, due }) => {
          const n = dayDiff(today, due)
          return (
            <button type="button" key={t.id} className={`jv-visor-task p-${t.priority} ${n < 0 ? 'late' : ''}`} data-lock={`Abrir en Drakter: ${t.title}`} onClick={() => openInDrakter('tasks')}>
              <span className="tk-due"><b>{Math.abs(n)}</b><small>{n < 0 ? 'tarde' : n === 1 ? 'día' : 'días'}</small></span>
              <span className="tk-t"><b>{t.title}</b><small>{t.project_id ? projName.get(t.project_id) ?? 'proyecto' : 'sin proyecto'}{t.blocked ? '  ·  bloqueada' : ''}</small></span>
            </button>
          )
        })}
      </Panel>

      <Panel sector={S} dA={26} R={NEAR} y={10} w={330} h={470} side title="Proyectos" code="TAR-03">
        <SnapNote snap={projects} empty="No hay proyectos activos." isEmpty={top.length === 0} />
        {rows.length > 0 && <Chart2D sector={S} w={296} h={380} sig={JSON.stringify(rows)} lock="Progreso de los proyectos" draw={(x, w, h, b) => drawProjects(x, w, h, { rows }, b)} />}
        <button type="button" className="link" data-lock="Abrir proyectos en Drakter" onClick={() => openInDrakter('projects')}>Abrir proyectos en Drakter</button>
      </Panel>

      <Panel sector={S} R={D - 110} y={-300} w={640} h={100} side title="Ritmo" code="TAR-04" className="kpis">
        <Kpis items={[
          [tasks.data ? (open.length >= 200 ? '200+' : open.length) : '–', 'abiertas'],
          [tasks.data ? overdue : '–', 'vencidas', overdue > 0],
          [tasks.data ? soon : '–', 'vencen en 3 días', soon > 0],
          [tasks.data ? open.filter((t) => t.blocked).length : '–', 'bloqueadas'],
          [projects.data ? projects.data.length : '–', 'proyectos activos']
        ]} />
      </Panel>
    </>
  )
}
