import { useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Field, TextInput } from './fields'
import { hhmm, minutesOf, todayIso, WEEKDAYS } from './format'
import { colorOf } from './palette'
import type { TimetableEntry } from './types'
import { useTimetable } from './useSubjects'

const PX_PER_HOUR = 56

interface Props {
  readonly reloadKey: number
  readonly onOpenSubject: (subjectId: string) => void
}

interface Placed {
  readonly entry: TimetableEntry
  readonly lane: number
  readonly lanes: number
}

/** Reparte en carriles las clases que se pisan dentro de un mismo día. */
function place(entries: readonly TimetableEntry[]): Placed[] {
  const sorted = [...entries].sort((a, b) => minutesOf(a.starts_local_time) - minutesOf(b.starts_local_time))
  const result: Placed[] = []
  let cluster: { entry: TimetableEntry; lane: number }[] = []
  let clusterEnd = -1
  const flush = () => {
    const lanes = Math.max(1, ...cluster.map((c) => c.lane + 1))
    for (const c of cluster) result.push({ ...c, lanes })
    cluster = []
  }
  for (const entry of sorted) {
    const s = minutesOf(entry.starts_local_time)
    if (cluster.length > 0 && s >= clusterEnd) {
      flush()
      clusterEnd = -1
    }
    const used = new Set(cluster.filter((c) => minutesOf(c.entry.ends_local_time) > s).map((c) => c.lane))
    let lane = 0
    while (used.has(lane)) lane += 1
    cluster.push({ entry, lane })
    clusterEnd = Math.max(clusterEnd, minutesOf(entry.ends_local_time))
  }
  flush()
  return result
}

export function WeeklyTimetable({ reloadKey, onOpenSubject }: Props) {
  const [on, setOn] = useState(todayIso())
  const { entries, error, reload } = useTimetable(on, reloadKey)

  const { startHour, endHour } = useMemo(() => {
    const all = entries ?? []
    if (all.length === 0) return { startHour: 8, endHour: 20 }
    const min = Math.min(...all.map((e) => minutesOf(e.starts_local_time)))
    const max = Math.max(...all.map((e) => minutesOf(e.ends_local_time)))
    return { startHour: Math.min(8, Math.floor(min / 60)), endHour: Math.max(20, Math.ceil(max / 60)) }
  }, [entries])

  const byDay = useMemo(
    () => WEEKDAYS.map((_, i) => place((entries ?? []).filter((e) => e.weekday === i + 1))),
    [entries]
  )
  const hours = Array.from({ length: endHour - startHour }, (_, i) => startHour + i)
  const height = hours.length * PX_PER_HOUR

  return (
    <section aria-label="Horario semanal" className="grid gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="w-48">
          <Field label="Horario vigente el" htmlFor="timetable-on">
            <TextInput id="timetable-on" type="date" value={on} onChange={(e) => e.target.value && setOn(e.target.value)} />
          </Field>
        </div>
        <p className="max-w-[56ch] text-sm text-muted-foreground">
          Muestra la semana tipo. Las excepciones de un día concreto se ven en el calendario.
        </p>
      </div>
      {error ? (
        <div role="alert" className="flex items-center gap-3 text-sm text-destructive">
          {error}
          <Button size="sm" variant="outline" onClick={reload}>
            Reintentar
          </Button>
        </div>
      ) : null}
      {entries && entries.length === 0 ? (
        <p className="text-sm text-muted-foreground">No hay clases vigentes en esa fecha.</p>
      ) : null}
      <div className="overflow-x-auto rounded-lg border border-border bg-card">
        <div className="grid min-w-[760px]" style={{ gridTemplateColumns: '3.5rem repeat(7, minmax(0, 1fr))' }}>
          <div className="border-b border-border" />
          {WEEKDAYS.map((name) => (
            <div key={name} className="border-b border-l border-border px-2 py-2 text-sm font-medium text-foreground">
              {name}
            </div>
          ))}
          <div className="relative" style={{ height }} aria-hidden="true">
            {hours.map((h, i) => (
              <span key={h} className="absolute right-2 -translate-y-1/2 text-xs text-muted-foreground" style={{ top: i * PX_PER_HOUR }}>
                {i === 0 ? '' : `${String(h).padStart(2, '0')}:00`}
              </span>
            ))}
          </div>
          {byDay.map((placed, day) => (
            <div key={WEEKDAYS[day]} className="relative border-l border-border" style={{ height }}>
              {hours.map((h, i) => (
                <div key={h} className="absolute inset-x-0 border-t border-border/60" style={{ top: i * PX_PER_HOUR }} aria-hidden="true" />
              ))}
              {placed.map(({ entry, lane, lanes }) => {
                const top = ((minutesOf(entry.starts_local_time) - startHour * 60) / 60) * PX_PER_HOUR
                const blockHeight = ((minutesOf(entry.ends_local_time) - minutesOf(entry.starts_local_time)) / 60) * PX_PER_HOUR
                const color = colorOf(entry.color)
                return (
                  <button
                    key={entry.session_id}
                    type="button"
                    onClick={() => onOpenSubject(entry.subject_id)}
                    aria-label={`${entry.subject_name}, ${WEEKDAYS[day]} de ${hhmm(entry.starts_local_time)} a ${hhmm(entry.ends_local_time)}${entry.room ? `, aula ${entry.room}` : ''}. Abrir asignatura`}
                    className="absolute overflow-hidden rounded-sm border-l-4 px-1.5 py-1 text-left text-xs leading-tight text-foreground outline-none focus-visible:ring-[3px] focus-visible:ring-ring"
                    style={{
                      top,
                      height: Math.max(blockHeight - 2, 18),
                      left: `calc(${(lane / lanes) * 100}% + 2px)`,
                      width: `calc(${100 / lanes}% - 4px)`,
                      borderLeftColor: color,
                      backgroundColor: `color-mix(in srgb, ${color} 24%, var(--card))`
                    }}
                  >
                    <span className="block truncate font-medium">{entry.subject_name}</span>
                    <span className="block truncate text-muted-foreground">
                      {hhmm(entry.starts_local_time)}–{hhmm(entry.ends_local_time)}
                      {entry.room ? ` · ${entry.room}` : ''}
                    </span>
                  </button>
                )
              })}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
