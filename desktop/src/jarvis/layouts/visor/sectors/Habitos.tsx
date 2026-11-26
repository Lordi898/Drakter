/**
 * Sector Hábitos (rumbo 154°, sección `habits`): anillos de la semana y mapa de los últimos 28 días
 * (historial real por hábito), los de hoy con «Hecho» y «Saltar», rachas e indicadores de la semana.
 * Las rachas se calculan sobre los 28 días cargados: se dice así, sin extrapolar.
 */
import { useMemo } from 'react'
import { useJarvisData } from '@/jarvis/data'
import { todayIn } from '@/modules/calendar/dateUtils'
import { registerRecord } from '@/modules/habits/api'
import type { Habit, HabitHistoryDay, RecordStatus } from '@/modules/habits/types'
import { drawHabits } from '../charts'
import { Panel } from '../Panel'
import { D, FAR, NEAR } from '../stage/world'
import { Chart2D, Kpis, SnapNote, plural, useAction } from './common'

const TOPICS = ['habits', 'habitHistory'] as const
const S = 3
const WEEKDAYS = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']

interface Stats {
  readonly habit: Habit
  readonly days: readonly HabitHistoryDay[]
  readonly streak: number
  readonly best: number
  readonly week: number
}

/** Racha actual y mejor racha: días programados seguidos con «hecho»; «saltado» no rompe ni suma; hoy pendiente no rompe. */
function streaks(days: readonly HabitHistoryDay[]): { streak: number; best: number } {
  let best = 0, run = 0
  for (const d of days) {
    if (!d.scheduled || d.status === 'skipped') continue
    if (d.status === 'done') { run++; best = Math.max(best, run) } else run = 0
  }
  let streak = 0
  for (let i = days.length - 1; i >= 0; i--) {
    const d = days[i]!
    if (!d.scheduled || d.status === 'skipped') continue
    if (d.status === 'done') streak++
    else if (i === days.length - 1 && d.status === null) continue
    else break
  }
  return { streak, best }
}

/** Cumplimiento (hechos / programados ya cerrados) en [from, to) días desde el final. */
function rate(rows: readonly Stats[], fromEnd: number, toEnd: number): number | null {
  let done = 0, due = 0
  for (const r of rows) {
    const n = r.days.length
    for (let i = Math.max(0, n - toEnd); i < n - fromEnd; i++) {
      const d = r.days[i]!
      if (!d.scheduled || d.status === 'skipped') continue
      if (i === n - 1 && d.status === null) continue
      due++; if (d.status === 'done') done++
    }
  }
  return due ? done / due : null
}

const cell = (d: HabitHistoryDay): number | null => (!d.scheduled ? null : d.status === 'done' ? 1 : d.status === 'skipped' ? 0.35 : 0.08)

export function Habitos() {
  const { habits, habitHistory } = useJarvisData(TOPICS)
  const { busy, run } = useAction()
  const list = habits.data ?? []

  const rows: Stats[] = useMemo(() => list.map((habit) => {
    const days = habitHistory.data?.[habit.id] ?? []
    const weekdayToday = (new Date().getDay() + 6) % 7
    const thisWeek = days.slice(Math.max(0, days.length - 1 - weekdayToday))
    const sched = thisWeek.filter((d) => d.scheduled && d.status !== 'skipped').length
    const done = thisWeek.filter((d) => d.status === 'done').length
    return { habit, days, ...streaks(days), week: sched ? done / sched : 0 }
  }).sort((a, b) => b.streak - a.streak), [list, habitHistory.data])

  const now = rate(rows, 0, 7), prev = rate(rows, 7, 14)
  const bestDay = useMemo(() => {
    const done = new Array<number>(7).fill(0), due = new Array<number>(7).fill(0)
    for (const r of rows) for (const d of r.days) {
      if (!d.scheduled || d.status === 'skipped' || d.status === null) continue
      const wd = (new Date(`${d.date}T12:00:00`).getDay() + 6) % 7
      due[wd]!++; if (d.status === 'done') done[wd]!++
    }
    let best = -1, br = -1
    for (let i = 0; i < 7; i++) if (due[i]! > 0 && done[i]! / due[i]! > br) { br = done[i]! / due[i]!; best = i }
    return best < 0 ? null : WEEKDAYS[best]!
  }, [rows])
  const todays = list.filter((h) => h.today_scheduled)
  const doneToday = todays.filter((h) => h.today_status === 'done').length
  const chart = { rows: rows.map((r) => ({ name: r.habit.name, week: r.week, days: r.days.map(cell) })) }
  const pct = (v: number | null): string => (v === null ? '–' : `${Math.round(v * 100)} %`)
  const mark = (h: Habit, status: RecordStatus): void =>
    run(h.id, () => registerRecord(h.id, todayIn(h.timezone), status), `${h.name}: ${status === 'done' ? 'hecho' : 'saltado'}`, () => { habits.reload(); habitHistory.reload() })

  return (
    <>
      <Panel sector={S} R={FAR} y={30} w={780} h={560} title="Constancia" code="HAB-01">
        <SnapNote snap={habits} empty="Aún no hay hábitos. Créalos en Drakter o pídeselo a Drakter." isEmpty={list.length === 0} />
        {rows.length > 0 && <Chart2D sector={S} w={720} h={330} sig={JSON.stringify(chart)} lock="Semana actual y 28 días" draw={(x, w, h, b) => drawHabits(x, w, h, chart, b)} />}
        <div className="jv-visor-hablist">
          {rows.slice(0, 6).map((r) => (
            <div key={r.habit.id} data-lock={`${r.habit.name}  racha ${r.streak}`}><b>{r.habit.name}</b><span>{r.habit.goal_note ?? (r.habit.preferred_local_time ? `a las ${r.habit.preferred_local_time.slice(0, 5)}` : '')}</span><em>{r.streak} d</em></div>
          ))}
        </div>
      </Panel>

      <Panel sector={S} dA={-26} R={NEAR} y={10} w={330} h={440} side title="Hoy" code="HAB-02">
        <SnapNote snap={habits} empty="Hoy no toca ningún hábito." isEmpty={todays.length === 0} />
        {todays.map((h) => (
          <div key={h.id} className={`jv-visor-hab ${h.today_status ?? ''}`} data-lock={`${h.name}  ${h.today_status === 'done' ? 'hecho' : h.today_status === 'skipped' ? 'saltado' : 'pendiente'}`}>
            <i />
            <div><b>{h.name}</b><small>{h.today_status === 'done' ? 'hecho' : h.today_status === 'skipped' ? 'saltado' : 'pendiente'}</small></div>
            {h.today_status !== 'done' && <button type="button" disabled={busy !== null} data-lock={`Hecho: ${h.name}`} onClick={() => mark(h, 'done')}>{busy === h.id ? '…' : 'Hecho'}</button>}
            {h.today_status === null && <button type="button" className="ghost" disabled={busy !== null} data-lock={`Saltar hoy: ${h.name}`} onClick={() => mark(h, 'skipped')}>Saltar</button>}
          </div>
        ))}
      </Panel>

      <Panel sector={S} dA={26} R={NEAR} y={10} w={330} h={440} side title="Rachas" code="HAB-03">
        <SnapNote snap={habitHistory} empty="Sin historial todavía." isEmpty={rows.length === 0} />
        {rows.slice(0, 4).map((r, i) => (
          <div key={r.habit.id} className={`jv-visor-streak ${i === 0 ? 'big' : ''} ${r.streak === 0 ? 'dim' : ''}`} data-lock={`${r.habit.name}  mejor ${r.best}`}>
            <b>{r.streak}</b><span>{plural(r.streak, 'día', 'días')} · {r.habit.name}<br /><em>mejor en 28 días: {r.best}</em></span>
          </div>
        ))}
      </Panel>

      <Panel sector={S} R={D - 110} y={-300} w={640} h={100} side title="Semana" code="HAB-04" className="kpis">
        <Kpis items={[
          [pct(now), 'cumplimiento 7 días'],
          [now !== null && prev !== null ? `${now >= prev ? '+' : ''}${Math.round((now - prev) * 100)} %` : '–', 'vs. 7 días antes', now !== null && prev !== null && now < prev],
          [habits.data ? `${doneToday}/${todays.length}` : '–', 'hechos hoy'],
          [bestDay ?? '–', 'mejor día']
        ]} />
      </Panel>
    </>
  )
}
