import { useEffect, useId, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { addDays, systemTimeZone, timeZoneList } from './dateUtils'
import { createEvent, getEvent, updateEvent } from './api'
import { defaultRange, describeFailure, Field, inputClass, localIso, type FormFailure } from './formUtils'
import { buildRrule, describeRrule, NO_RECURRENCE, parseRrule, WEEKDAY_CODES, WEEKDAY_NAMES, type RecurrenceDraft, type Repeat } from './recurrence'
import type { AgendaItem, EventKind, EventOut, EventPayload, EventStatus } from './types'

export type EventDialogTarget =
  | { readonly mode: 'create'; readonly day: string; readonly minutes: number }
  | { readonly mode: 'edit'; readonly eventId: string }

export interface EventDialogProps {
  readonly target: EventDialogTarget | null
  readonly timezone: string
  readonly onClose: () => void
  /** `conflicts` llega de la respuesta del guardado: se muestran, no bloquean. */
  readonly onSaved: (conflicts: readonly AgendaItem[]) => void
}

const KINDS: readonly { value: EventKind; label: string }[] = [
  { value: 'event', label: 'Evento' },
  { value: 'reminder', label: 'Recordatorio' },
  { value: 'work_session', label: 'Sesión de trabajo' }
]
const STATUSES: readonly { value: EventStatus; label: string }[] = [
  { value: 'confirmed', label: 'Confirmado' },
  { value: 'tentative', label: 'Provisional' }
]

export function EventDialog({ target, timezone, onClose, onSaved }: EventDialogProps) {
  const uid = useId()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [failure, setFailure] = useState<FormFailure | null>(null)
  const [revision, setRevision] = useState<number | null>(null)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [location, setLocation] = useState('')
  const [reminder, setReminder] = useState('')
  const [kind, setKind] = useState<EventKind>('event')
  const [status, setStatus] = useState<EventStatus>('confirmed')
  const [tz, setTz] = useState(timezone)
  const [allDay, setAllDay] = useState(false)
  const [startDate, setStartDate] = useState('')
  const [startTime, setStartTime] = useState('09:00')
  const [endDate, setEndDate] = useState('')
  const [endTime, setEndTime] = useState('10:00')
  const [recurrence, setRecurrence] = useState<RecurrenceDraft>({ ...NO_RECURRENCE })
  const [rawRrule, setRawRrule] = useState<string | null>(null)
  const [customRrule, setCustomRrule] = useState(false)

  useEffect(() => {
    if (!target) return
    setFailure(null)
    setSaving(false)
    setRevision(null)
    if (target.mode === 'create') {
      const range = defaultRange(target.day, target.minutes)
      setTitle('')
      setDescription('')
      setLocation('')
      setReminder('')
      setKind('event')
      setStatus('confirmed')
      setTz(timezone || systemTimeZone())
      setAllDay(false)
      setStartDate(range.startDate)
      setStartTime(range.startTime)
      setEndDate(range.endDate)
      setEndTime(range.endTime)
      setRecurrence({ ...NO_RECURRENCE })
      setRawRrule(null)
      setCustomRrule(false)
      return
    }
    let active = true
    setLoading(true)
    getEvent(target.eventId)
      .then((event: EventOut) => {
        if (!active) return
        setRevision(event.revision)
        setTitle(event.title)
        setDescription(event.description ?? '')
        setLocation(event.location ?? '')
        setReminder(event.reminder_minutes_before === null ? '' : String(event.reminder_minutes_before))
        setKind(event.kind)
        setStatus(event.status === 'cancelled' ? 'confirmed' : event.status)
        setTz(event.timezone)
        setAllDay(event.all_day)
        if (event.all_day && event.start_date && event.end_date_exclusive) {
          setStartDate(event.start_date)
          setEndDate(addDays(event.end_date_exclusive, -1))
        } else if (event.local_start && event.local_end) {
          setStartDate(event.local_start.slice(0, 10))
          setStartTime(event.local_start.slice(11, 16))
          setEndDate(event.local_end.slice(0, 10))
          setEndTime(event.local_end.slice(11, 16))
        }
        const parsed = parseRrule(event.rrule)
        setRecurrence(parsed.draft)
        setRawRrule(event.rrule)
        setCustomRrule(event.rrule !== null && !parsed.supported)
      })
      .catch((error: unknown) => active && setFailure(describeFailure(error, timezone)))
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [target, timezone])

  if (!target) return null
  const editing = target.mode === 'edit'
  const timeError = failure?.nonexistentTime ? failure.message : null
  const generalError = failure && !failure.nonexistentTime ? failure.message : null

  function patchRecurrence(patch: Partial<RecurrenceDraft>): void {
    setRecurrence((current) => ({ ...current, ...patch }))
  }

  function toggleWeekday(code: (typeof WEEKDAY_CODES)[number]): void {
    setRecurrence((current) => ({
      ...current,
      weekdays: current.weekdays.includes(code) ? current.weekdays.filter((c) => c !== code) : [...current.weekdays, code]
    }))
  }

  async function submit(event: React.FormEvent): Promise<void> {
    event.preventDefault()
    if (!target) return
    const cleanTitle = title.trim()
    if (!cleanTitle) return setFailure({ message: 'El título es obligatorio.', nonexistentTime: false })
    if (!startDate || !endDate) return setFailure({ message: 'Indica las fechas.', nonexistentTime: false })
    if (allDay ? endDate < startDate : localIso(endDate, endTime) <= localIso(startDate, startTime)) {
      return setFailure({ message: 'El final debe ser posterior al inicio.', nonexistentTime: false })
    }
    if (recurrence.repeat !== 'none' && recurrence.endMode === 'until' && (!recurrence.until || recurrence.until < startDate)) {
      return setFailure({ message: 'La fecha final de la repetición debe ser igual o posterior al inicio.', nonexistentTime: false })
    }
    const payload: EventPayload = {
      title: cleanTitle,
      description: description.trim() || null,
      location: location.trim() || null,
      reminder_minutes_before: reminder === '' ? null : Math.max(0, Math.round(Number(reminder) || 0)),
      kind,
      status,
      timezone: tz,
      all_day: allDay,
      local_start: allDay ? null : localIso(startDate, startTime),
      local_end: allDay ? null : localIso(endDate, endTime),
      start_date: allDay ? startDate : null,
      end_date_exclusive: allDay ? addDays(endDate, 1) : null,
      rrule: customRrule ? rawRrule : buildRrule(recurrence, startDate)
    }
    setSaving(true)
    setFailure(null)
    try {
      const result =
        target.mode === 'edit' && revision !== null
          ? await updateEvent(target.eventId, payload, revision)
          : await createEvent(payload)
      onSaved(result.conflicts)
    } catch (error) {
      setFailure(describeFailure(error, tz))
    } finally {
      setSaving(false)
    }
  }

  const rec = recurrence
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{editing ? 'Editar evento' : 'Nuevo evento'}</DialogTitle>
          <DialogDescription>
            {editing && rec.repeat !== 'none' ? 'Los cambios afectan a toda la serie.' : 'Las horas son locales en la zona horaria elegida.'}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={(e) => void submit(e)} className="grid gap-4" aria-busy={loading}>
          <Field id={`${uid}-title`} label="Título">
            <input id={`${uid}-title`} className={inputClass} value={title} onChange={(e) => setTitle(e.target.value)} maxLength={300} required autoFocus disabled={loading} />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field id={`${uid}-kind`} label="Tipo">
              <select id={`${uid}-kind`} className={inputClass} value={kind} onChange={(e) => setKind(e.target.value as EventKind)} disabled={loading}>
                {KINDS.map((k) => (
                  <option key={k.value} value={k.value}>{k.label}</option>
                ))}
              </select>
            </Field>
            <Field id={`${uid}-status`} label="Estado">
              <select id={`${uid}-status`} className={inputClass} value={status} onChange={(e) => setStatus(e.target.value as EventStatus)} disabled={loading}>
                {STATUSES.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </Field>
          </div>
          <div className="flex items-center gap-2">
            <Switch id={`${uid}-allday`} checked={allDay} onCheckedChange={setAllDay} disabled={loading} />
            <Label htmlFor={`${uid}-allday`}>Todo el día</Label>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field id={`${uid}-sd`} label="Inicio" error={timeError}>
              <div className="flex gap-2">
                <input id={`${uid}-sd`} type="date" className={inputClass} value={startDate} onChange={(e) => setStartDate(e.target.value)} required disabled={loading} aria-invalid={timeError !== null} />
                {allDay ? null : (
                  <input aria-label="Hora de inicio" type="time" className={inputClass} value={startTime} onChange={(e) => setStartTime(e.target.value)} required disabled={loading} aria-invalid={timeError !== null} />
                )}
              </div>
            </Field>
            <Field id={`${uid}-ed`} label={allDay ? 'Último día' : 'Final'}>
              <div className="flex gap-2">
                <input id={`${uid}-ed`} type="date" className={inputClass} value={endDate} onChange={(e) => setEndDate(e.target.value)} required disabled={loading} />
                {allDay ? null : (
                  <input aria-label="Hora de final" type="time" className={inputClass} value={endTime} onChange={(e) => setEndTime(e.target.value)} required disabled={loading} aria-invalid={timeError !== null} />
                )}
              </div>
            </Field>
          </div>
          <Field id={`${uid}-tz`} label="Zona horaria">
            <select id={`${uid}-tz`} className={inputClass} value={tz} onChange={(e) => setTz(e.target.value)} disabled={loading}>
              {timeZoneList(tz).map((z) => (
                <option key={z} value={z}>{z}</option>
              ))}
            </select>
          </Field>

          <fieldset className="grid gap-3 rounded-md border border-border p-3" disabled={loading}>
            <legend className="px-1 text-sm font-medium">Repetición</legend>
            {customRrule ? (
              <p className="text-sm text-muted-foreground">
                {describeRrule(rawRrule)}. Esta regla no se puede editar aquí y se conservará tal cual.
              </p>
            ) : (
              <>
                <div className="grid grid-cols-2 gap-3">
                  <Field id={`${uid}-rep`} label="Frecuencia">
                    <select id={`${uid}-rep`} className={inputClass} value={rec.repeat} onChange={(e) => patchRecurrence({ repeat: e.target.value as Repeat })}>
                      <option value="none">Sin repetición</option>
                      <option value="daily">Diaria</option>
                      <option value="weekly">Semanal</option>
                      <option value="monthly">Mensual</option>
                    </select>
                  </Field>
                  {rec.repeat !== 'none' ? (
                    <Field id={`${uid}-int`} label="Cada" hint={rec.repeat === 'daily' ? 'días' : rec.repeat === 'weekly' ? 'semanas' : 'meses'}>
                      <input id={`${uid}-int`} type="number" min={1} max={99} className={inputClass} value={rec.interval} onChange={(e) => patchRecurrence({ interval: Math.max(1, Number(e.target.value) || 1) })} />
                    </Field>
                  ) : null}
                </div>
                {rec.repeat === 'weekly' ? (
                  <div role="group" aria-label="Días de la semana" className="flex flex-wrap gap-1.5">
                    {WEEKDAY_CODES.map((code) => (
                      <button
                        key={code}
                        type="button"
                        aria-pressed={rec.weekdays.includes(code)}
                        aria-label={WEEKDAY_NAMES[code]}
                        onClick={() => toggleWeekday(code)}
                        className="h-8 w-9 rounded-md border border-input text-xs outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 aria-pressed:border-ambar aria-pressed:bg-ambar/20"
                      >
                        {WEEKDAY_NAMES[code].slice(0, 2)}
                      </button>
                    ))}
                  </div>
                ) : null}
                {rec.repeat === 'monthly' ? (
                  <p className="text-xs text-muted-foreground">Se repite el día {Number(startDate.slice(8, 10)) || '—'} de cada mes.</p>
                ) : null}
                {rec.repeat !== 'none' ? (
                  <div className="grid grid-cols-2 gap-3">
                    <Field id={`${uid}-end`} label="Termina">
                      <select id={`${uid}-end`} className={inputClass} value={rec.endMode} onChange={(e) => patchRecurrence({ endMode: e.target.value as RecurrenceDraft['endMode'] })}>
                        <option value="never">Nunca</option>
                        <option value="until">En una fecha</option>
                        <option value="count">Tras un número de veces</option>
                      </select>
                    </Field>
                    {rec.endMode === 'until' ? (
                      <Field id={`${uid}-until`} label="Hasta">
                        <input id={`${uid}-until`} type="date" className={inputClass} value={rec.until} min={startDate} onChange={(e) => patchRecurrence({ until: e.target.value })} required />
                      </Field>
                    ) : null}
                    {rec.endMode === 'count' ? (
                      <Field id={`${uid}-count`} label="Veces">
                        <input id={`${uid}-count`} type="number" min={1} max={999} className={inputClass} value={rec.count} onChange={(e) => patchRecurrence({ count: Math.max(1, Number(e.target.value) || 1) })} />
                      </Field>
                    ) : null}
                  </div>
                ) : null}
              </>
            )}
          </fieldset>

          <div className="grid grid-cols-2 gap-3">
            <Field id={`${uid}-loc`} label="Lugar (opcional)">
              <input id={`${uid}-loc`} className={inputClass} value={location} onChange={(e) => setLocation(e.target.value)} maxLength={300} disabled={loading} />
            </Field>
            <Field id={`${uid}-rem`} label="Aviso previo (opcional)" hint="Minutos antes del inicio.">
              <input id={`${uid}-rem`} type="number" min={0} max={40320} className={inputClass} value={reminder} onChange={(e) => setReminder(e.target.value)} disabled={loading} />
            </Field>
          </div>
          <Field id={`${uid}-desc`} label="Descripción">
            <Textarea id={`${uid}-desc`} value={description} onChange={(e) => setDescription(e.target.value)} maxLength={8000} rows={3} disabled={loading} />
          </Field>
          {generalError ? <p role="alert" className="text-sm text-destructive">{generalError}</p> : null}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>Cancelar</Button>
            <Button type="submit" disabled={saving || loading || (editing && revision === null)}>
              {saving ? 'Guardando…' : editing ? 'Guardar cambios' : 'Crear evento'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
