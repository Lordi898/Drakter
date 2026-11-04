import { useMemo, useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { errorText } from '../calendar/workspaceClient'
import { createHabit, updateHabit } from './api'
import { dayOfMonth, systemTimezone, timeZoneOptions, todayIn } from './dates'
import { fieldClass } from './formStyles'
import { buildRrule, parseRrule, WEEK_DAYS, type Frequency, type FrequencyKind } from './rrule'
import type { Habit, HabitUpdate } from './types'

const KINDS: readonly { value: FrequencyKind; label: string }[] = [
  { value: 'daily', label: 'Todos los días' },
  { value: 'weekdays', label: 'Días concretos de la semana' },
  { value: 'everyNWeeks', label: 'Cada N semanas' },
  { value: 'monthly', label: 'Una vez al mes' }
]

export interface HabitDialogProps {
  /** null = crear. */
  readonly habit: Habit | null
  readonly open: boolean
  readonly onClose: () => void
  readonly onSaved: (habit: Habit) => void
}

export function HabitDialog({ habit, open, onClose, onSaved }: HabitDialogProps) {
  // Se monta con `key` distinto por hábito: el estado inicial sale de las props.
  const initialZone = habit?.timezone ?? systemTimezone()
  const initialFreq = useMemo<Frequency | null>(() => (habit ? parseRrule(habit.rrule) : null), [habit])
  const startDefault = habit?.start_date ?? todayIn(initialZone)

  const [name, setName] = useState(habit?.name ?? '')
  const [description, setDescription] = useState(habit?.description ?? '')
  const [timezone, setTimezone] = useState(initialZone)
  const [kind, setKind] = useState<FrequencyKind>(initialFreq?.kind ?? 'daily')
  const [days, setDays] = useState<readonly string[]>(initialFreq?.days ?? [])
  const [interval, setIntervalValue] = useState(initialFreq?.interval && initialFreq.interval > 1 ? initialFreq.interval : 2)
  const [monthDay, setMonthDay] = useState(initialFreq?.monthDay ?? dayOfMonth(startDefault))
  const [startDate, setStartDate] = useState(startDefault)
  const [endDate, setEndDate] = useState(habit?.end_date ?? '')
  const [time, setTime] = useState(habit?.preferred_local_time?.slice(0, 5) ?? '')
  const [reminder, setReminder] = useState(habit?.reminder_enabled ?? false)
  const [goal, setGoal] = useState(habit?.goal_note ?? '')
  const [effectiveFrom, setEffectiveFrom] = useState(todayIn(initialZone))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const zones = useMemo(() => timeZoneOptions(initialZone), [initialZone])
  const rrule = buildRrule({ kind, days, interval, monthDay })
  const rruleChanged = habit !== null && rrule !== habit.rrule
  const unreadable = habit !== null && initialFreq === null

  const problems: string[] = []
  if (!name.trim()) problems.push('Escribe un nombre.')
  if ((kind === 'weekdays' || kind === 'everyNWeeks') && days.length === 0) problems.push('Elige al menos un día de la semana.')
  if (kind === 'everyNWeeks' && (!Number.isInteger(interval) || interval < 2 || interval > 52)) problems.push('El intervalo va de 2 a 52 semanas.')
  if (kind === 'monthly' && (!Number.isInteger(monthDay) || monthDay < 1 || monthDay > 31)) problems.push('El día del mes va de 1 a 31.')
  if (endDate && endDate < startDate) problems.push('La fecha final no puede ser anterior a la de inicio.')
  if (reminder && !time) problems.push('Para el recordatorio indica una hora preferida.')

  function toggleDay(code: string) {
    setDays((cur) => (cur.includes(code) ? cur.filter((c) => c !== code) : [...cur, code]))
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (problems.length > 0) return
    setSaving(true)
    setError(null)
    try {
      if (!habit) {
        onSaved(
          await createHabit({
            name: name.trim(),
            description: description.trim() || null,
            timezone,
            rrule,
            start_date: startDate,
            end_date: endDate || null,
            goal_note: goal.trim() || null,
            preferred_local_time: time || null,
            reminder_enabled: reminder
          })
        )
      } else {
        const patch: { -readonly [K in keyof HabitUpdate]: HabitUpdate[K] } = {}
        if (name.trim() !== habit.name) patch.name = name.trim()
        if ((description.trim() || null) !== habit.description) patch.description = description.trim() || null
        if (timezone !== habit.timezone) patch.timezone = timezone
        if (rruleChanged && !unreadable) {
          patch.rrule = rrule
          patch.schedule_effective_from = effectiveFrom
        } else if (unreadable && kind !== 'daily') {
          patch.rrule = rrule
          patch.schedule_effective_from = effectiveFrom
        }
        if ((endDate || null) !== habit.end_date) patch.end_date = endDate || null
        if ((goal.trim() || null) !== habit.goal_note) patch.goal_note = goal.trim() || null
        if ((time || null) !== (habit.preferred_local_time?.slice(0, 5) ?? null)) patch.preferred_local_time = time || null
        if (reminder !== habit.reminder_enabled) patch.reminder_enabled = reminder
        onSaved(Object.keys(patch).length > 0 ? await updateHabit(habit, patch) : habit)
      }
    } catch (e) {
      setError(errorText(e))
    } finally {
      setSaving(false)
    }
  }

  const needsDays = kind === 'weekdays' || kind === 'everyNWeeks'

  return (
    <Dialog open={open} onOpenChange={(next) => (!next && !saving ? onClose() : undefined)}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{habit ? 'Editar hábito' : 'Crear hábito'}</DialogTitle>
          <DialogDescription>
            {habit ? 'Los cambios se guardan sin tocar el historial.' : 'Define qué quieres hacer y cada cuánto.'}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={(e) => void submit(e)} className="flex flex-col gap-4" noValidate>
          <Field id="h-name" label="Nombre">
            <input id="h-name" className={fieldClass} value={name} maxLength={200} onChange={(e) => setName(e.target.value)} autoFocus />
          </Field>
          <Field id="h-desc" label="Descripción (opcional)">
            <Textarea id="h-desc" value={description} maxLength={4000} rows={2} onChange={(e) => setDescription(e.target.value)} />
          </Field>

          <fieldset className="flex flex-col gap-3 rounded-md border border-border p-3">
            <legend className="px-1 text-sm font-medium text-foreground">Frecuencia</legend>
            <Field id="h-kind" label="Se repite">
              <select id="h-kind" className={fieldClass} value={kind} onChange={(e) => setKind(e.target.value as FrequencyKind)}>
                {KINDS.map((k) => (
                  <option key={k.value} value={k.value}>
                    {k.label}
                  </option>
                ))}
              </select>
            </Field>
            {kind === 'everyNWeeks' ? (
              <Field id="h-interval" label="Cada cuántas semanas">
                <input id="h-interval" type="number" min={2} max={52} className={cn(fieldClass, 'w-28')} value={interval} onChange={(e) => setIntervalValue(Number(e.target.value))} />
              </Field>
            ) : null}
            {needsDays ? (
              <div role="group" aria-label="Días activos" className="flex flex-wrap gap-1.5">
                {WEEK_DAYS.map((d) => {
                  const on = days.includes(d.code)
                  return (
                    <Button key={d.code} type="button" size="sm" variant={on ? 'default' : 'outline'} aria-pressed={on} aria-label={d.name} onClick={() => toggleDay(d.code)}>
                      {d.short}
                    </Button>
                  )
                })}
              </div>
            ) : null}
            {kind === 'monthly' ? (
              <Field id="h-monthday" label="Día del mes">
                <input id="h-monthday" type="number" min={1} max={31} className={cn(fieldClass, 'w-28')} value={monthDay} onChange={(e) => setMonthDay(Number(e.target.value))} />
              </Field>
            ) : null}
            {habit ? (
              <div className="flex flex-col gap-2 rounded-md bg-muted p-2.5 text-xs text-muted-foreground">
                <p>
                  Si cambias la frecuencia, el historial se conserva tal cual. La nueva frecuencia rige desde la fecha que indiques; los días anteriores siguen con la anterior.
                </p>
                {unreadable ? <p>La frecuencia actual ({habit.rrule}) no se puede editar aquí; si eliges otra, sustituirá a la actual.</p> : null}
                {rruleChanged || (unreadable && kind !== 'daily') ? (
                  <Field id="h-eff" label="La nueva frecuencia rige desde">
                    <input id="h-eff" type="date" className={cn(fieldClass, 'w-44')} value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} />
                  </Field>
                ) : null}
              </div>
            ) : null}
          </fieldset>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field id="h-start" label="Fecha de inicio">
              <input id="h-start" type="date" className={fieldClass} value={startDate} disabled={habit !== null} onChange={(e) => setStartDate(e.target.value)} />
            </Field>
            <Field id="h-end" label="Fecha final (opcional)">
              <input id="h-end" type="date" className={fieldClass} value={endDate} min={startDate} onChange={(e) => setEndDate(e.target.value)} />
            </Field>
          </div>

          <Field id="h-tz" label="Zona horaria">
            <select id="h-tz" className={fieldClass} value={timezone} onChange={(e) => setTimezone(e.target.value)}>
              {zones.map((z) => (
                <option key={z} value={z}>
                  {z}
                </option>
              ))}
            </select>
          </Field>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field id="h-time" label="Hora preferida (opcional)">
              <input id="h-time" type="time" className={fieldClass} value={time} onChange={(e) => setTime(e.target.value)} />
            </Field>
            <div className="flex items-center gap-2 self-end pb-1.5">
              <Switch id="h-rem" checked={reminder} onCheckedChange={setReminder} />
              <Label htmlFor="h-rem">Recordatorio</Label>
            </div>
          </div>
          {reminder ? (
            <p className="-mt-2 text-xs text-muted-foreground">
              Se guarda tu preferencia, pero el aviso no sonará todavía: se activará cuando exista el programador de recordatorios.
            </p>
          ) : null}

          <Field id="h-goal" label="Objetivo (opcional)">
            <Textarea id="h-goal" value={goal} maxLength={1000} rows={2} placeholder="Qué quieres conseguir con este hábito" onChange={(e) => setGoal(e.target.value)} />
          </Field>

          {problems.length > 0 ? (
            <ul className="list-disc pl-5 text-sm text-destructive" aria-live="polite">
              {problems.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          ) : null}
          {error ? (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          ) : null}

          <DialogFooter>
            <Button type="button" variant="ghost" disabled={saving} onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" disabled={saving || problems.length > 0}>
              {saving ? 'Guardando…' : habit ? 'Guardar cambios' : 'Crear hábito'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function Field({ id, label, children }: { readonly id: string; readonly label: string; readonly children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      {children}
    </div>
  )
}
