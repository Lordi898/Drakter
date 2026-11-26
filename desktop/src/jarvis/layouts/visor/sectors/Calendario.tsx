/**
 * Sector Calendario y asignaturas (rumbo 206°, secciones `calendar` y `subjects`): la semana desde hoy
 * (agenda real expandida, en la zona del usuario), lo siguiente con cuenta atrás por minutos, las clases
 * de hoy y los exámenes de la semana. Sin acciones destructivas: editar se hace en Drakter.
 * «Examen» = evento cuyo título lo dice (la agenda no tiene un tipo propio para exámenes).
 */
import { useMemo } from 'react'
import { useJarvisData } from '@/jarvis/data'
import { addDays, timeText, weekdayShort } from '@/modules/calendar/dateUtils'
import { allDayOn, placeTimed } from '@/modules/calendar/layout'
import type { AgendaItem } from '@/modules/calendar/types'
import { drawWeek, type WeekData } from '../charts'
import { Panel } from '../Panel'
import { D, FAR, NEAR } from '../stage/world'
import { Chart2D, Kpis, SnapNote, dayDiff, localDay, nowHours, plural, useMinute, useVisorNav } from './common'

const TOPICS = ['agenda', 'timetable', 'subjects'] as const
const S = 4
const EXAM = /examen|parcial|final\b/i

const isExam = (a: AgendaItem): boolean => EXAM.test(a.title)
const tone = (a: AgendaItem): WeekData['blocks'][number]['tone'] =>
  isExam(a) ? 'exam' : a.source_type === 'class_session' ? 'class' : a.source_type === 'time_block' ? 'block' : 'event'
const startKey = (a: AgendaItem): string => (a.all_day ? `${a.start_date}T00:00` : a.display_start ?? '')

function localNow(): string {
  const d = new Date()
  return `${localDay(d)}T${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
/** «en 18 min», «en 2 h 5 min», «mañana 9:00», «vie 11:30». */
function until(a: AgendaItem, now: string): string {
  const start = startKey(a), day = start.slice(0, 10), today = now.slice(0, 10)
  const dd = dayDiff(today, day)
  if (a.all_day) return dd === 0 ? 'hoy, todo el día' : dd === 1 ? 'mañana, todo el día' : `${weekdayShort(day).toLowerCase()}, todo el día`
  if (dd === 0) {
    const m = (Number(start.slice(11, 13)) * 60 + Number(start.slice(14, 16))) - (Number(now.slice(11, 13)) * 60 + Number(now.slice(14, 16)))
    if (m <= 0) return 'ahora'
    return m < 60 ? `en ${m} min` : `en ${Math.floor(m / 60)} h${m % 60 ? ` ${m % 60} min` : ''}`
  }
  return `${dd === 1 ? 'mañana' : weekdayShort(day).toLowerCase()} ${timeText(start)}`
}

export function Calendario() {
  const { agenda, timetable, subjects } = useJarvisData(TOPICS)
  const { openInDrakter } = useVisorNav()
  const minute = useMinute()
  const now = useMemo(() => localNow(), [minute]) // eslint-disable-line react-hooks/exhaustive-deps
  const today = now.slice(0, 10)
  const items = agenda.data ?? []

  const week: WeekData = useMemo(() => {
    const days = Array.from({ length: 7 }, (_, i) => addDays(today, i))
    let from = 8, to = 22
    const blocks = days.flatMap((d, i) => placeTimed(items, d).map((p) => {
      from = Math.min(from, Math.floor(p.startMin / 60)); to = Math.max(to, Math.ceil(p.endMin / 60))
      return { day: i, start: p.startMin / 60, end: p.endMin / 60, title: p.item.title, tone: tone(p.item) }
    }))
    return { days: days.map((d) => `${weekdayShort(d).toLowerCase()} ${Number(d.slice(8))}`), blocks, from, to: Math.min(24, to) }
  }, [items, today])

  const upcoming = useMemo(() => items
    .filter((a) => (a.all_day ? (a.end_date_exclusive ?? a.start_date ?? '') > today : (a.display_end ?? '') > now))
    .sort((a, b) => startKey(a).localeCompare(startKey(b)))
    .slice(0, 6), [items, now, today])
  const exams = items.filter(isExam).filter((a) => startKey(a) >= today)
  const nextExam = exams[0]
  const classes = [...(timetable.data ?? [])].sort((a, b) => a.starts_local_time.localeCompare(b.starts_local_time))
  const classMin = classes.reduce((s, c) => s + (Number(c.ends_local_time.slice(0, 2)) * 60 + Number(c.ends_local_time.slice(3, 5)) - Number(c.starts_local_time.slice(0, 2)) * 60 - Number(c.starts_local_time.slice(3, 5))), 0)
  const allDayToday = allDayOn(items, today).length
  const first = upcoming[0]

  return (
    <>
      <Panel sector={S} R={FAR} y={30} w={780} h={560} title={`Semana del ${Number(today.slice(8))} al ${Number(addDays(today, 6).slice(8))}`} code="CAL-01">
        <SnapNote snap={agenda} empty="Semana libre: no hay nada en el calendario." isEmpty={items.length === 0} />
        {items.length > 0 && <Chart2D sector={S} w={740} h={470} clock sig={JSON.stringify(week)} lock="Los próximos 7 días" draw={(x, w, h, b) => drawWeek(x, w, h, week, nowHours(), b)} />}
      </Panel>

      <Panel sector={S} dA={-26} R={NEAR} y={10} w={330} h={440} side title="Lo siguiente" code="CAL-02">
        <SnapNote snap={agenda} empty="Nada más esta semana." isEmpty={upcoming.length === 0} />
        {first && (
          <div className="jv-visor-count" data-lock={`${first.title}  ${until(first, now)}`}>
            <b>{until(first, now)}</b><span>{first.title}{first.room ? ` · ${first.room}` : first.location ? ` · ${first.location}` : ''}</span>
          </div>
        )}
        {upcoming.slice(1).map((a) => (
          <div key={a.occurrence_id} className={`jv-visor-nx ${isExam(a) ? 'warn' : ''}`} data-lock={a.title}>
            <time>{until(a, now)}</time><span>{a.title}</span>
          </div>
        ))}
        <button type="button" className="link" data-lock="Abrir el calendario en Drakter" onClick={() => openInDrakter('calendar')}>Abrir el calendario en Drakter</button>
      </Panel>

      <Panel sector={S} dA={26} R={NEAR} y={10} w={330} h={440} side title="Asignaturas" code="CAL-03">
        <h4 className="jv-visor-sub">Clases de hoy</h4>
        <SnapNote snap={timetable} empty="Hoy no hay clases." isEmpty={classes.length === 0} />
        {classes.map((c) => (
          <div key={c.session_id} className="jv-visor-nx" data-lock={`${c.subject_name}  ${c.starts_local_time.slice(0, 5)}–${c.ends_local_time.slice(0, 5)}`}>
            <time>{c.starts_local_time.slice(0, 5)}</time><span><i className="dot" style={{ background: c.color ?? undefined }} />{c.subject_name}{c.room ? ` · ${c.room}` : ''}</span>
          </div>
        ))}
        <h4 className="jv-visor-sub">Exámenes esta semana</h4>
        {exams.length === 0 ? <p className="jv-visor-note">Ninguno en el calendario.</p> : exams.slice(0, 3).map((a) => (
          <div key={a.occurrence_id} className="jv-visor-nx warn" data-lock={a.title}><time>{until(a, now)}</time><span>{a.title}</span></div>
        ))}
        <button type="button" className="link" data-lock="Abrir asignaturas en Drakter" onClick={() => openInDrakter('subjects')}>{subjects.data ? plural(subjects.data.length, 'asignatura', 'asignaturas') : 'Asignaturas'} en Drakter</button>
      </Panel>

      <Panel sector={S} R={D - 110} y={-300} w={640} h={100} side title="Curso" code="CAL-04" className="kpis">
        <Kpis items={[
          [agenda.data ? items.filter((a) => a.source_type !== 'class_session').length : '–', 'eventos en 7 días'],
          [timetable.data ? classes.length : '–', 'clases hoy'],
          [timetable.data ? `${(classMin / 60).toFixed(1).replace('.', ',')} h` : '–', 'de clase hoy'],
          [nextExam ? dayDiff(today, startKey(nextExam).slice(0, 10)) : '–', 'días al próximo examen', nextExam !== undefined],
          [agenda.data ? allDayToday : '–', 'de día completo hoy']
        ]} />
      </Panel>
    </>
  )
}
