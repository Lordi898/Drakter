import { useMemo, useState } from 'react'
import { CalendarClock, CalendarPlus, RefreshCw, TriangleAlert, X } from 'lucide-react'
import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { CalendarDrawing } from './CalendarDrawing'
import { CalendarToolbar } from './CalendarToolbar'
import { ConfirmationDialog } from './ConfirmationDialog'
import { DayView } from './DayView'
import { EventDialog, type EventDialogTarget } from './EventDialog'
import { MonthView, monthGridStart } from './MonthView'
import { OccurrenceDialog } from './OccurrenceDialog'
import { TimeBlockDialog, type TimeBlockDialogTarget } from './TimeBlockDialog'
import { WeekView } from './WeekView'
import { addDays, addMonths, dateTimeLabel, dayLabel, isValidTimeZone, monthLabel, startOfWeek, systemTimeZone, todayIn, weekLabel } from './dateUtils'
import { normalizeKind, type AgendaItem, type CalendarView, type OccurrenceKind } from './types'
import { useAgenda } from './useAgenda'
import type { ConfirmationTicket } from './workspaceApi'

function rangeFor(view: CalendarView, day: string): { from: string; to: string } {
  if (view === 'day') return { from: day, to: addDays(day, 1) }
  if (view === 'week') {
    const monday = startOfWeek(day)
    return { from: monday, to: addDays(monday, 7) }
  }
  const from = monthGridStart(day)
  return { from, to: addDays(from, 42) }
}

export function CalendarPage() {
  const initialZone = isValidTimeZone(systemTimeZone()) ? systemTimeZone() : 'UTC'
  const [timezone, setTimezone] = useState(initialZone)
  const [view, setView] = useState<CalendarView>('week')
  const [day, setDay] = useState(() => todayIn(initialZone))
  const [hidden, setHidden] = useState<ReadonlySet<OccurrenceKind>>(new Set())
  const [selected, setSelected] = useState<AgendaItem | null>(null)
  const [eventTarget, setEventTarget] = useState<EventDialogTarget | null>(null)
  const [blockTarget, setBlockTarget] = useState<TimeBlockDialogTarget | null>(null)
  const [conflicts, setConflicts] = useState<readonly AgendaItem[]>([])
  const [confirmation, setConfirmation] = useState<ConfirmationTicket | null>(null)

  const { from, to } = rangeFor(view, day)
  const { state, reload } = useAgenda(from, to, timezone)
  const today = todayIn(timezone)

  const visible = useMemo(
    () => (state.status === 'ready' ? state.items.filter((i) => !hidden.has(normalizeKind(i.kind))) : []),
    [state, hidden]
  )
  const overlapIds = state.status === 'ready' ? state.overlapIds : new Set<string>()

  const label = view === 'day' ? dayLabel(day) : view === 'week' ? weekLabel(startOfWeek(day)) : monthLabel(day)

  function step(direction: -1 | 1): void {
    setDay((current) => (view === 'day' ? addDays(current, direction) : view === 'week' ? addDays(current, 7 * direction) : addMonths(current, direction)))
  }

  function openDay(target: string): void {
    setDay(target)
    setView('day')
  }

  function toggleKind(kind: OccurrenceKind): void {
    setHidden((current) => {
      const next = new Set(current)
      if (next.has(kind)) next.delete(kind)
      else next.add(kind)
      return next
    })
  }

  function createAt(target: string, minutes: number): void {
    setEventTarget({ mode: 'create', day: target, minutes })
  }

  function edit(item: AgendaItem): void {
    setSelected(null)
    if (item.source_type === 'calendar_event') setEventTarget({ mode: 'edit', eventId: item.source_id })
    else if (item.source_type === 'time_block') setBlockTarget({ mode: 'edit', blockId: item.source_id })
  }

  function saved(found: readonly AgendaItem[]): void {
    setEventTarget(null)
    setBlockTarget(null)
    setConflicts(found)
    reload()
  }

  const shared = { today, items: visible, overlapIds, onSelect: setSelected }

  return (
    <>
      <PageHeader
        title="Calendario"
        summary="Eventos y bloques de tiempo, con vista diaria, semanal y mensual."
        actions={
          <>
            <Button variant="outline" onClick={() => setBlockTarget({ mode: 'create', day, minutes: 9 * 60 })}>
              <CalendarClock /> Nuevo bloque
            </Button>
            <Button onClick={() => createAt(day, 9 * 60)}>
              <CalendarPlus /> Nuevo evento
            </Button>
          </>
        }
      />
      <CalendarToolbar
        view={view}
        label={label}
        date={day}
        timezone={timezone}
        hidden={hidden}
        onView={setView}
        onStep={step}
        onToday={() => setDay(today)}
        onDate={setDay}
        onTimezone={setTimezone}
        onToggleKind={toggleKind}
      />

      {conflicts.length > 0 ? (
        <div role="status" className="mb-3 flex items-start gap-3 rounded-md border border-warning/60 bg-warning/10 px-3 py-2 text-sm">
          <TriangleAlert className="mt-0.5 size-4 shrink-0 text-warning" aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <p className="font-medium">Guardado, pero se solapa con {conflicts.length === 1 ? 'otro elemento' : `${conflicts.length} elementos`}:</p>
            <ul className="mt-1 list-disc pl-5 text-muted-foreground">
              {conflicts.map((c) => (
                <li key={c.occurrence_id}>
                  {c.title}
                  {c.display_start ? ` (${dateTimeLabel(c.display_start)})` : ''}
                </li>
              ))}
            </ul>
          </div>
          <Button variant="ghost" size="icon-xs" aria-label="Cerrar aviso de solape" onClick={() => setConflicts([])}>
            <X />
          </Button>
        </div>
      ) : null}

      {state.status === 'unavailable' || state.status === 'error' ? (
        <div className="flex flex-col items-start gap-4">
          <EmptyState
            title={state.status === 'unavailable' ? 'El calendario no está conectado' : 'No se pudo cargar la agenda'}
            description={
              state.status === 'unavailable'
                ? 'El espacio de trabajo aún no está conectado, así que no se puede leer ni guardar nada. No se muestran datos de ejemplo.'
                : state.message
            }
            drawing={<CalendarDrawing />}
          />
          <Button variant="outline" onClick={reload}>
            <RefreshCw /> Reintentar
          </Button>
        </div>
      ) : (
        <div className="flex flex-col gap-3" aria-busy={state.status === 'loading'}>
          {state.status === 'ready' && state.truncated ? (
            <p role="status" className="text-sm text-warning">La agenda tiene más elementos de los que se muestran en este periodo.</p>
          ) : null}
          {state.status === 'ready' && state.items.length === 0 ? (
            <p role="status" className="text-sm text-muted-foreground">No hay eventos ni bloques en este periodo.</p>
          ) : null}
          {state.status === 'loading' ? <p className="text-sm text-muted-foreground">Cargando agenda…</p> : null}
          <div className="flex h-[calc(100vh-22rem)] min-h-[520px] flex-col">
            {view === 'day' ? <DayView day={day} {...shared} onCreateAt={createAt} /> : null}
            {view === 'week' ? <WeekView day={day} {...shared} onCreateAt={createAt} onOpenDay={openDay} /> : null}
            {view === 'month' ? <MonthView day={day} {...shared} onOpenDay={openDay} /> : null}
          </div>
        </div>
      )}

      <OccurrenceDialog
        item={selected}
        overlapping={selected !== null && overlapIds.has(selected.occurrence_id)}
        onClose={() => setSelected(null)}
        onEdit={edit}
        onChanged={reload}
        onConfirmationRequired={setConfirmation}
      />
      <EventDialog target={eventTarget} timezone={timezone} onClose={() => setEventTarget(null)} onSaved={saved} />
      <TimeBlockDialog target={blockTarget} timezone={timezone} onClose={() => setBlockTarget(null)} onSaved={saved} />
      <ConfirmationDialog
        confirmation={confirmation}
        onResolved={(approved) => {
          setConfirmation(null)
          if (approved) reload()
        }}
      />
    </>
  )
}
