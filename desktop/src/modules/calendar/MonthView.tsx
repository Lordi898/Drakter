import { cn } from '@/lib/utils'
import { dayLabel, rangeOfDays, startOfMonth, startOfWeek, weekdayShort } from './dateUtils'
import { itemsOn } from './layout'
import { OccurrenceChip } from './OccurrenceChip'
import type { AgendaItem } from './types'

const MAX_VISIBLE = 3

export interface MonthViewProps {
  readonly day: string
  readonly today: string
  readonly items: readonly AgendaItem[]
  readonly overlapIds: ReadonlySet<string>
  readonly onSelect: (item: AgendaItem) => void
  readonly onOpenDay: (day: string) => void
}

export function monthGridStart(day: string): string {
  return startOfWeek(startOfMonth(day))
}

export function MonthView({ day, today, items, overlapIds, onSelect, onOpenDay }: MonthViewProps) {
  const days = rangeOfDays(monthGridStart(day), 42)
  const month = day.slice(0, 7)
  return (
    <div className="flex min-h-0 flex-1 flex-col rounded-md border border-border bg-card/40">
      <div className="grid grid-cols-7 border-b border-border">
        {days.slice(0, 7).map((d) => (
          <div key={d} className="px-2 py-1.5 text-xs font-medium text-muted-foreground">
            {weekdayShort(d)}
          </div>
        ))}
      </div>
      <div className="grid min-h-0 flex-1 grid-cols-7 grid-rows-6">
        {days.map((d) => {
          const list = itemsOn(items, d)
          return (
            <div
              key={d}
              className={cn(
                'flex min-h-0 flex-col gap-0.5 overflow-hidden border-b border-l border-border p-1',
                d.slice(0, 7) !== month && 'bg-background/40 text-muted-foreground',
                d === today && 'bg-ambar/5'
              )}
            >
              <button
                type="button"
                onClick={() => onOpenDay(d)}
                aria-label={`Abrir ${dayLabel(d)}`}
                className={cn(
                  'self-start rounded-sm px-1 text-xs font-medium outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/60',
                  d === today && 'bg-ambar text-primary-foreground'
                )}
              >
                {Number(d.slice(8, 10))}
              </button>
              {list.slice(0, MAX_VISIBLE).map((item) => (
                <OccurrenceChip
                  key={`${item.occurrence_id}-${d}`}
                  item={item}
                  overlapping={overlapIds.has(item.occurrence_id)}
                  showTime={false}
                  onSelect={onSelect}
                />
              ))}
              {list.length > MAX_VISIBLE ? (
                <button
                  type="button"
                  onClick={() => onOpenDay(d)}
                  className="self-start rounded-sm px-1 text-[11px] text-muted-foreground outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/60"
                >
                  +{list.length - MAX_VISIBLE} más
                </button>
              ) : null}
            </div>
          )
        })}
      </div>
    </div>
  )
}
