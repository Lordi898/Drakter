import { useMemo } from 'react'
import { addDays, formatLongDate, isoWeekday } from './dates'
import { WEEK_DAYS } from './rrule'
import { cn } from '@/lib/utils'
import { STATUS_LABEL } from './status'
import type { HabitHistoryDay } from './types'

export interface HistoryGridProps {
  readonly days: readonly HabitHistoryDay[]
  readonly today: string
  readonly selected: string | null
  readonly onSelect: (date: string) => void
}

function cellClass(day: HabitHistoryDay | undefined, future: boolean): string {
  if (future || !day) return 'border-dashed border-border bg-transparent opacity-40'
  if (day.status === 'done') return 'border-success bg-success'
  if (day.status === 'skipped') return 'border-warning bg-ambar/60'
  if (day.status === 'missed') return 'border-destructive bg-destructive'
  if (day.scheduled) return 'border-plan-line bg-transparent'
  return 'border-border bg-muted'
}

function cellLabel(date: string, day: HabitHistoryDay | undefined, future: boolean): string {
  const base = formatLongDate(date)
  if (future) return `${base}: aún no se puede registrar`
  if (day?.status) return `${base}: ${STATUS_LABEL[day.status]}`
  return `${base}: ${day?.scheduled ? 'programado, sin registro' : 'no programado'}`
}

/** Cuadrícula tipo calendario de contribuciones: columnas = semanas, filas = lunes a domingo. */
export function HabitHistoryGrid({ days, today, selected, onSelect }: HistoryGridProps) {
  const { weeks, byDate } = useMemo(() => {
    const map = new Map(days.map((d) => [d.date, d]))
    const first = days[0]?.date ?? today
    const start = addDays(first, -(isoWeekday(first) - 1))
    const cols: string[][] = []
    for (let cursor = start; cursor <= today; cursor = addDays(cursor, 7)) {
      cols.push(Array.from({ length: 7 }, (_, i) => addDays(cursor, i)))
    }
    return { weeks: cols, byDate: map }
  }, [days, today])

  return (
    <div className="overflow-x-auto pb-1">
      <div className="inline-flex gap-1.5" role="grid" aria-label="Historial por días">
        <div className="flex flex-col gap-1 pr-1 text-[10px] leading-none text-muted-foreground" aria-hidden="true">
          {WEEK_DAYS.map((d) => (
            <span key={d.code} className="flex size-5 items-center">
              {d.short}
            </span>
          ))}
        </div>
        {weeks.map((week) => (
          <div key={week[0]} role="row" className="flex flex-col gap-1">
            {week.map((date) => {
              const day = byDate.get(date)
              const future = date > today
              const outOfRange = !future && !day
              return (
                <button
                  key={date}
                  type="button"
                  role="gridcell"
                  disabled={future || outOfRange}
                  aria-label={cellLabel(date, day, future)}
                  aria-pressed={selected === date}
                  title={cellLabel(date, day, future)}
                  onClick={() => onSelect(date)}
                  className={cn(
                    'size-5 rounded-[4px] border outline-none transition-shadow focus-visible:ring-[3px] focus-visible:ring-ring/60',
                    cellClass(day, future || outOfRange),
                    selected === date && 'ring-2 ring-foreground',
                    date === today && 'outline outline-1 outline-offset-1 outline-foreground'
                  )}
                />
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}

export function HistoryLegend() {
  const items = [
    ['border-success bg-success', 'Hecho'],
    ['border-warning bg-ambar/60', 'Saltado'],
    ['border-destructive bg-destructive', 'No hecho'],
    ['border-plan-line bg-transparent', 'Programado sin registro'],
    ['border-border bg-muted', 'No programado']
  ] as const
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
      {items.map(([cls, text]) => (
        <li key={text} className="flex items-center gap-1.5">
          <span aria-hidden="true" className={cn('size-3 rounded-[3px] border', cls)} />
          {text}
        </li>
      ))}
    </ul>
  )
}
