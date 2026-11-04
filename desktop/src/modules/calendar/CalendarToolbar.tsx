import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { inputClass } from './formUtils'
import { timeZoneList } from './dateUtils'
import { KIND_STYLES } from './kinds'
import { KIND_ORDER, type CalendarView, type OccurrenceKind } from './types'

const VIEWS: readonly { value: CalendarView; label: string }[] = [
  { value: 'day', label: 'Día' },
  { value: 'week', label: 'Semana' },
  { value: 'month', label: 'Mes' }
]

export interface CalendarToolbarProps {
  readonly view: CalendarView
  readonly label: string
  readonly timezone: string
  readonly hidden: ReadonlySet<OccurrenceKind>
  readonly onView: (view: CalendarView) => void
  readonly onStep: (direction: -1 | 1) => void
  readonly onToday: () => void
  readonly onDate: (iso: string) => void
  readonly date: string
  readonly onTimezone: (zone: string) => void
  readonly onToggleKind: (kind: OccurrenceKind) => void
}

export function CalendarToolbar(props: CalendarToolbarProps) {
  const { view, label, timezone, hidden, date } = props
  const unit = view === 'day' ? 'día' : view === 'week' ? 'semana' : 'mes'
  return (
    <div className="flex flex-col gap-3 pb-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1">
          <Button variant="outline" size="icon-sm" aria-label={`Anterior ${unit}`} onClick={() => props.onStep(-1)}>
            <ChevronLeft />
          </Button>
          <Button variant="outline" size="sm" onClick={props.onToday}>Hoy</Button>
          <Button variant="outline" size="icon-sm" aria-label={`Siguiente ${unit}`} onClick={() => props.onStep(1)}>
            <ChevronRight />
          </Button>
        </div>
        <h2 className="type-display min-w-[12ch] text-xl" aria-live="polite">{label}</h2>
        <input
          type="date"
          aria-label="Ir a la fecha"
          className={cn(inputClass, 'w-40')}
          value={date}
          onChange={(e) => e.target.value && props.onDate(e.target.value)}
        />
        <div role="group" aria-label="Vista" className="ml-auto flex overflow-hidden rounded-md border border-input">
          {VIEWS.map((v) => (
            <button
              key={v.value}
              type="button"
              aria-pressed={view === v.value}
              onClick={() => props.onView(v.value)}
              className="px-3 py-1.5 text-sm outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 aria-pressed:bg-ambar/20 aria-pressed:font-medium"
            >
              {v.label}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">Zona horaria</span>
          <select aria-label="Zona horaria" className={cn(inputClass, 'w-56')} value={timezone} onChange={(e) => props.onTimezone(e.target.value)}>
            {timeZoneList(timezone).map((z) => (
              <option key={z} value={z}>{z}</option>
            ))}
          </select>
        </label>
      </div>
      <div role="group" aria-label="Filtrar por tipo" className="flex flex-wrap items-center gap-2">
        {KIND_ORDER.map((kind) => {
          const shown = !hidden.has(kind)
          return (
            <button
              key={kind}
              type="button"
              aria-pressed={shown}
              onClick={() => props.onToggleKind(kind)}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-full border border-input px-2.5 py-1 text-xs outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50',
                shown ? 'bg-card text-foreground' : 'text-muted-foreground line-through opacity-70'
              )}
            >
              <span className={cn('size-2 rounded-full', KIND_STYLES[kind].dot)} aria-hidden="true" />
              {KIND_STYLES[kind].label}
            </button>
          )
        })}
      </div>
    </div>
  )
}
