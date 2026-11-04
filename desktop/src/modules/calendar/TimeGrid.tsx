import { useEffect, useRef } from 'react'
import { cn } from '@/lib/utils'
import { dayLabel, minutesToText, weekdayShort } from './dateUtils'
import { allDayOn, placeTimed } from './layout'
import { OccurrenceChip } from './OccurrenceChip'
import type { AgendaItem } from './types'

const HOUR_PX = 48
const HOURS = Array.from({ length: 24 }, (_, h) => h)

export interface TimeGridProps {
  readonly days: readonly string[]
  readonly today: string
  readonly items: readonly AgendaItem[]
  readonly overlapIds: ReadonlySet<string>
  readonly onSelect: (item: AgendaItem) => void
  readonly onCreateAt: (day: string, minutes: number) => void
  readonly onOpenDay?: (day: string) => void
}

/** Rejilla horaria con CSS grid: una columna por día; las horas vienen ya en la zona pedida. */
export function TimeGrid({ days, today, items, overlapIds, onSelect, onCreateAt, onOpenDay }: TimeGridProps) {
  const scroller = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (scroller.current) scroller.current.scrollTop = 7 * HOUR_PX
  }, [])
  const template = { gridTemplateColumns: `3.5rem repeat(${days.length}, minmax(0, 1fr))` }

  return (
    <div className="flex min-h-0 flex-1 flex-col rounded-md border border-border bg-card/40">
      <div className="grid border-b border-border" style={template}>
        <div />
        {days.map((day) => (
          <div key={day} className="min-w-0 border-l border-border px-2 py-2">
            {onOpenDay ? (
              <button
                type="button"
                onClick={() => onOpenDay(day)}
                aria-label={`Abrir ${dayLabel(day)}`}
                className={cn(
                  'rounded-sm text-sm font-medium outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/60',
                  day === today && 'text-ambar'
                )}
              >
                {weekdayShort(day)} {Number(day.slice(8, 10))}
              </button>
            ) : (
              <span className={cn('text-sm font-medium', day === today && 'text-ambar')}>{dayLabel(day)}</span>
            )}
            <div className="mt-1 flex flex-col gap-1">
              {allDayOn(items, day).map((item) => (
                <OccurrenceChip
                  key={`${item.occurrence_id}-${day}`}
                  item={item}
                  overlapping={false}
                  showTime={false}
                  onSelect={onSelect}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
      <div ref={scroller} className="min-h-0 flex-1 overflow-y-auto">
        <div className="grid" style={{ ...template, height: HOUR_PX * 24 }}>
          <div className="relative">
            {HOURS.map((h) => (
              <span
                key={h}
                className="absolute right-2 -translate-y-1/2 font-mono text-[11px] text-muted-foreground"
                style={{ top: h * HOUR_PX, display: h === 0 ? 'none' : undefined }}
              >
                {minutesToText(h * 60)}
              </span>
            ))}
          </div>
          {days.map((day) => (
            <div
              key={day}
              role="group"
              aria-label={`Horario de ${dayLabel(day)}`}
              className={cn('relative border-l border-border', day === today && 'bg-ambar/5')}
              onClick={(e) => {
                const rect = e.currentTarget.getBoundingClientRect()
                const minutes = Math.floor((e.clientY - rect.top) / HOUR_PX) * 60
                onCreateAt(day, Math.min(Math.max(minutes, 0), 23 * 60))
              }}
            >
              {HOURS.map((h) => (
                <div key={h} className="absolute inset-x-0 border-t border-border/60" style={{ top: h * HOUR_PX }} aria-hidden="true" />
              ))}
              {placeTimed(items, day).map((p) => (
                <OccurrenceChip
                  key={`${p.item.occurrence_id}-${day}`}
                  item={p.item}
                  overlapping={overlapIds.has(p.item.occurrence_id)}
                  onSelect={onSelect}
                  className="absolute"
                  style={{
                    top: (p.startMin / 60) * HOUR_PX,
                    height: Math.max(((p.endMin - p.startMin) / 60) * HOUR_PX - 2, 18),
                    left: `${(p.lane / p.lanes) * 100}%`,
                    width: `calc(${100 / p.lanes}% - 2px)`
                  }}
                />
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
