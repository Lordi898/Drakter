import { useCallback, useEffect, useState } from 'react'
import { Archive, ArchiveRestore, ArrowLeft, Bell, Pencil } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { errorText } from '../calendar/workspaceClient'
import { getHistory, getStatistics, registerRecord, setArchived } from './api'
import { BackendState } from './BackendState'
import { addDays, formatDate, formatLongDate, todayIn } from './dates'
import { HabitHistoryGrid, HistoryLegend } from './HabitHistoryGrid'
import { HabitStats } from './HabitStats'
import { QuickMark } from './QuickMark'
import { describeRrule } from './rrule'
import type { Habit, HabitHistory, HabitStatistics, RecordStatus } from './types'

const RANGES = [
  { days: 30, label: '30 días' },
  { days: 90, label: '90 días' },
  { days: 180, label: '6 meses' }
] as const

export interface HabitDetailProps {
  readonly habit: Habit
  readonly onBack: () => void
  readonly onEdit: (habit: Habit) => void
  readonly onChanged: (habit?: Habit) => void
}

export function HabitDetail({ habit, onBack, onEdit, onChanged }: HabitDetailProps) {
  const today = todayIn(habit.timezone)
  const [range, setRange] = useState<number>(90)
  const [history, setHistory] = useState<HabitHistory | null>(null)
  const [stats, setStats] = useState<HabitStatistics | null>(null)
  const [loadError, setLoadError] = useState<unknown>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    const from = addDays(today, -(range - 1))
    setLoadError(null)
    Promise.all([getHistory(habit.id, from, today), getStatistics(habit.id, from, today)])
      .then(([h, s]) => {
        setHistory(h)
        setStats(s)
      })
      .catch(setLoadError)
  }, [habit.id, range, today])

  useEffect(load, [load])

  const archived = habit.archived_at !== null
  const selectedDay = history?.days.find((d) => d.date === selected) ?? null

  async function mark(date: string, status: RecordStatus) {
    setBusy(true)
    setActionError(null)
    try {
      await registerRecord(habit.id, date, status)
      load()
      onChanged()
    } catch (e) {
      setActionError(errorText(e))
    } finally {
      setBusy(false)
    }
  }

  async function toggleArchive() {
    setBusy(true)
    setActionError(null)
    try {
      onChanged(await setArchived(habit, !archived))
    } catch (e) {
      setActionError(errorText(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex max-w-4xl flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button type="button" variant="ghost" size="sm" onClick={onBack}>
          <ArrowLeft aria-hidden="true" /> Volver a la lista
        </Button>
        <div className="flex gap-2">
          <Button type="button" variant="outline" size="sm" onClick={() => onEdit(habit)}>
            <Pencil aria-hidden="true" /> Editar
          </Button>
          <Button type="button" variant="outline" size="sm" disabled={busy} onClick={toggleArchive}>
            {archived ? <ArchiveRestore aria-hidden="true" /> : <Archive aria-hidden="true" />}
            {archived ? 'Desarchivar' : 'Archivar'}
          </Button>
        </div>
      </div>

      <section aria-labelledby="habit-title" className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <h2 id="habit-title" className="type-display text-3xl text-foreground">
            {habit.name}
          </h2>
          {archived ? <Badge variant="outline">Archivado</Badge> : null}
        </div>
        {habit.description ? <p className="max-w-[65ch] text-muted-foreground">{habit.description}</p> : null}
        <dl className="mt-1 grid gap-x-8 gap-y-1 text-sm sm:grid-cols-2">
          <Meta label="Frecuencia" value={describeRrule(habit.rrule)} />
          <Meta label="Zona horaria" value={habit.timezone} />
          <Meta label="Desde" value={formatDate(habit.start_date)} />
          <Meta label="Hasta" value={habit.end_date ? formatDate(habit.end_date) : 'sin fecha final'} />
          {habit.goal_note ? <Meta label="Objetivo" value={habit.goal_note} /> : null}
          {habit.preferred_local_time ? <Meta label="Hora preferida" value={habit.preferred_local_time.slice(0, 5)} /> : null}
        </dl>
        {habit.reminder_enabled ? (
          <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Bell className="size-3.5" aria-hidden="true" /> Recordatorio guardado; el aviso se activará cuando exista el programador.
          </p>
        ) : null}
        {habit.schedule_versions.length > 1 ? (
          <details className="mt-1 text-sm text-muted-foreground">
            <summary className="cursor-pointer outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50">
              Versiones de la frecuencia ({habit.schedule_versions.length})
            </summary>
            <ul className="mt-1 list-disc pl-5">
              {habit.schedule_versions.map((v) => (
                <li key={v.id}>
                  {describeRrule(v.rrule)}: desde {formatDate(v.valid_from)}
                  {v.valid_until ? ` hasta ${formatDate(v.valid_until)}` : ''}
                </li>
              ))}
            </ul>
          </details>
        ) : null}
      </section>

      <Separator />

      {loadError ? (
        <BackendState error={loadError} onRetry={load} />
      ) : (
        <>
          <section aria-labelledby="hist-title" className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 id="hist-title" className="text-lg font-semibold text-foreground">
                Historial
              </h3>
              <div role="group" aria-label="Periodo" className="flex gap-1">
                {RANGES.map((r) => (
                  <Button
                    key={r.days}
                    type="button"
                    size="xs"
                    variant={range === r.days ? 'default' : 'outline'}
                    aria-pressed={range === r.days}
                    onClick={() => setRange(r.days)}
                  >
                    {r.label}
                  </Button>
                ))}
              </div>
            </div>
            {history ? (
              <HabitHistoryGrid days={history.days} today={today} selected={selected} onSelect={setSelected} />
            ) : (
              <p className="text-sm text-muted-foreground">Cargando historial…</p>
            )}
            <HistoryLegend />
            {selected && selectedDay ? (
              <div className="flex flex-col gap-2 rounded-md border border-border bg-card p-3">
                <p className="text-sm font-medium capitalize text-foreground">{formatLongDate(selected)}</p>
                <QuickMark
                  label={`Registro del ${formatDate(selected)}`}
                  current={selectedDay.status}
                  busy={busy}
                  disabled={archived}
                  onMark={(s) => void mark(selected, s)}
                />
                {!selectedDay.scheduled ? (
                  <p className="text-xs text-muted-foreground">Este día no estaba programado; puedes registrarlo igualmente.</p>
                ) : null}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">Elige un día de la cuadrícula para corregir su registro. Los días futuros no se pueden registrar.</p>
            )}
            {actionError ? (
              <p role="alert" className="text-sm text-destructive">
                {actionError}
              </p>
            ) : null}
          </section>

          <Separator />

          <section aria-labelledby="stats-title" className="flex flex-col gap-3">
            <h3 id="stats-title" className="text-lg font-semibold text-foreground">
              Estadísticas
            </h3>
            {stats ? <HabitStats stats={stats} /> : <p className="text-sm text-muted-foreground">Cargando estadísticas…</p>}
          </section>
        </>
      )}
    </div>
  )
}

function Meta({ label, value }: { readonly label: string; readonly value: string }) {
  return (
    <div className="flex gap-2">
      <dt className="text-muted-foreground">{label}:</dt>
      <dd className="text-foreground">{value}</dd>
    </div>
  )
}
