/**
 * Sector Hoy (rumbo 051°, sección `today`): esfera de 24 h con la agenda de hoy, prioridades (vencidas
 * y de hoy) con «Completar», hábitos de hoy con «Hecho» y una fila de indicadores. Datos: `GET /today`
 * (zona del usuario) y las tareas abiertas (para la revisión y las subtareas al completar).
 */
import { useMemo } from 'react'
import { useJarvisData } from '@/jarvis/data'
import { minutesOf, timeText, todayIn } from '@/modules/calendar/dateUtils'
import { registerRecord } from '@/modules/habits/api'
import { completeTask } from '@/modules/tasks/api'
import { longDay, weekdayOf } from '@/pages/today/format'
import type { TodayTask } from '@/pages/today/contract'
import { drawDial, type DialData } from '../charts'
import { Panel } from '../Panel'
import { D, FAR, NEAR } from '../stage/world'
import { Chart2D, Kpis, PRIORITY_RANK, SnapNote, nowHours, plural, useAction, useMinute, useVisorNav } from './common'

const TOPICS = ['today', 'tasks'] as const
const S = 1

const hourOf = (local: string | null, day: string, fallback: number): number =>
  local === null ? fallback : local.slice(0, 10) < day ? 0 : local.slice(0, 10) > day ? 24 : minutesOf(local) / 60

export function Hoy() {
  const { today, tasks } = useJarvisData(TOPICS)
  const { openInDrakter } = useVisorNav()
  const { busy, run } = useAction()
  const minute = useMinute()
  const t = today.data
  const day = t?.date ?? ''

  const prio = useMemo(() => {
    if (!t) return []
    const all: TodayTask[] = [...t.overdue.items, ...t.due_today.items]
    return all.sort((a, b) => b.days_overdue - a.days_overdue || (PRIORITY_RANK[a.priority] ?? 9) - (PRIORITY_RANK[b.priority] ?? 9)).slice(0, 5)
  }, [t])
  const agenda = useMemo(() => (t ? t.agenda.items.filter((a) => !a.all_day) : []), [t])
  const now = nowHours()
  const next = agenda.find((a) => a.display_start && hourOf(a.display_start, day, 0) > now)
  const habits = t?.habits.items ?? []
  const habitsDone = habits.filter((h) => h.today_status === 'done').length

  const dial: DialData = useMemo(() => {
    const events = agenda.map((a) => ({ start: hourOf(a.display_start, day, 0), end: hourOf(a.display_end, day, 24), accent: a.source_type === 'time_block' }))
    const busyH = events.reduce((s, e) => s + Math.max(0, e.end - e.start), 0)
    const taskDots = (t?.due_today.items ?? []).filter((x) => x.due_at).map((x) => { const d = new Date(x.due_at!); return { hour: d.getHours() + d.getMinutes() / 60, urgent: x.priority === 'urgent' || x.priority === 'high' } })
    return {
      events, tasks: taskDots, load: busyH / 16,
      caption: events.length ? `${plural(events.length, 'evento', 'eventos')} · ${busyH.toFixed(1).replace('.', ',')} h` : 'agenda libre',
      next: next ? `siguiente ${timeText(next.display_start!)} ${next.title}` : 'sin más eventos hoy'
    }
    // `minute` mueve «siguiente» con el reloj
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agenda, day, t, next?.occurrence_id, minute])

  const complete = (task: TodayTask): void => {
    const full = tasks.data?.find((x) => x.id === task.id)
    if (!full) { openInDrakter('tasks'); return }
    if (full.subtask_count > full.completed_subtask_count) { openInDrakter('tasks'); return } // el diálogo de subtareas vive en Drakter
    run(task.id, () => completeTask(full.id, full.revision), `Completada: ${task.title}`, () => { today.reload(); tasks.reload() })
  }

  return (
    <>
      <Panel sector={S} R={FAR} y={30} w={780} h={560} title={t ? `Hoy, ${weekdayOf(day)} ${longDay(day)}` : 'Hoy'} code="HOY-01">
        <div className="jv-visor-split">
          <Chart2D sector={S} w={430} h={430} clock sig={JSON.stringify(dial)} lock="Esfera de 24 horas" draw={(x, w, h, b) => drawDial(x, w, h, dial, nowHours(), b)} />
          <div className="jv-visor-agenda">
            <SnapNote snap={today} empty="Agenda libre: nada programado para hoy." isEmpty={t !== null && t.agenda.items.length === 0} />
            {t?.agenda.items.slice(0, 9).map((a) => {
              const past = !a.all_day && a.display_end !== null && hourOf(a.display_end, day, 24) < now
              return (
                <div key={a.occurrence_id} className={`ag-row ${a.source_type} ${past ? 'past' : ''}`} data-lock={`${a.title}  ${a.all_day ? 'todo el día' : `${timeText(a.display_start ?? '')}–${timeText(a.display_end ?? '')}`}`}>
                  <time>{a.all_day ? 'día' : timeText(a.display_start ?? '')}</time>
                  <div><b>{a.title}</b><small>{a.room ?? (a.source_type === 'class_session' ? 'clase' : a.source_type === 'time_block' ? 'bloque' : 'evento')}</small></div>
                </div>
              )
            })}
            {t && t.agenda.total > 9 && <button type="button" className="link" data-lock="Ver la agenda completa" onClick={() => openInDrakter('calendar')}>{t.agenda.total - 9} más en el calendario</button>}
          </div>
        </div>
      </Panel>

      <Panel sector={S} dA={-26} R={NEAR} y={20} w={330} h={430} side title="Prioridades" code="HOY-02">
        <SnapNote snap={today} empty="Sin tareas para hoy." isEmpty={prio.length === 0} />
        {prio.map((x, i) => (
          <div key={x.id} className={`jv-visor-prio ${x.days_overdue > 0 ? 'late' : ''}`} data-lock={`${x.title}  ${x.days_overdue > 0 ? `vencida hace ${plural(x.days_overdue, 'día', 'días')}` : 'vence hoy'}`}>
            <span className="pn">{i + 1}</span>
            <div><b>{x.title}</b><small>{x.project_name ?? 'sin proyecto'}  ·  {x.days_overdue > 0 ? `vencida hace ${plural(x.days_overdue, 'día', 'días')}` : x.due_at ? `hoy ${new Date(x.due_at).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}` : 'hoy'}</small></div>
            <button type="button" disabled={busy !== null} data-lock={`Completar: ${x.title}`} onClick={() => complete(x)}>{busy === x.id ? '…' : 'Completar'}</button>
          </div>
        ))}
      </Panel>

      <Panel sector={S} dA={26} R={NEAR} y={20} w={330} h={430} side title="Hábitos de hoy" code="HOY-03">
        <SnapNote snap={today} empty="Hoy no toca ningún hábito." isEmpty={habits.length === 0} />
        {habits.map((h) => (
          <div key={h.id} className={`jv-visor-hab ${h.today_status ?? ''}`} data-lock={`${h.name}  ${h.today_status === 'done' ? 'hecho' : 'pendiente'}`}>
            <i />
            <div><b>{h.name}</b><small>{h.preferred_local_time ? `a las ${h.preferred_local_time.slice(0, 5)}` : 'cualquier hora'}{h.today_status === 'skipped' ? '  ·  saltado' : ''}</small></div>
            {h.today_status !== 'done' && (
              <button type="button" disabled={busy !== null} data-lock={`Marcar hecho: ${h.name}`} onClick={() => run(h.id, () => registerRecord(h.id, t ? todayIn(t.timezone) : day, 'done'), `${h.name}: hecho`, today.reload)}>{busy === h.id ? '…' : 'Hecho'}</button>
            )}
          </div>
        ))}
      </Panel>

      <Panel sector={S} R={D - 110} y={-300} w={640} h={100} side title="Resumen" code="HOY-04" className="kpis">
        <Kpis items={[
          [t ? t.due_today.total : '–', 'vencen hoy'],
          [t ? t.overdue.total : '–', 'vencidas', (t?.overdue.total ?? 0) > 0],
          [t ? `${habitsDone}/${habits.length}` : '–', 'hábitos'],
          [next ? timeText(next.display_start!) : '–', 'lo siguiente'],
          [t ? t.projects.total : '–', 'proyectos activos']
        ]} />
      </Panel>
    </>
  )
}
