import { useId, useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { errorText } from '@/modules/calendar/workspaceClient'
import { createSession, updateSession } from './api'
import { Field, FormError, TextInput } from './fields'
import { hhmm, localTimezone, minutesOf, toApiTime, todayIso, WEEKDAYS } from './format'
import type { ClassSession, ConflictItem, SessionInput } from './types'

interface Props {
  readonly open: boolean
  readonly subjectId: string
  /** Sesión a editar; null para crear. */
  readonly session: ClassSession | null
  readonly onClose: () => void
  readonly onSaved: (conflicts: readonly ConflictItem[]) => void
}

export function SessionDialog({ open, subjectId, session, onClose, onSaved }: Props) {
  return (
    <Dialog open={open} onOpenChange={(next) => (next ? undefined : onClose())}>
      <DialogContent>
        <SessionForm key={session?.id ?? 'new'} subjectId={subjectId} session={session} onClose={onClose} onSaved={onSaved} />
      </DialogContent>
    </Dialog>
  )
}

function SessionForm({ subjectId, session, onClose, onSaved }: Omit<Props, 'open'>) {
  const id = useId()
  const [weekday, setWeekday] = useState(String(session?.weekday ?? 1))
  const [start, setStart] = useState(session ? hhmm(session.starts_local_time) : '09:00')
  const [end, setEnd] = useState(session ? hhmm(session.ends_local_time) : '10:00')
  const [room, setRoom] = useState(session?.room ?? '')
  const [timezone, setTimezone] = useState(session?.timezone ?? localTimezone())
  const [validFrom, setValidFrom] = useState(session?.valid_from ?? todayIso())
  const [validUntil, setValidUntil] = useState(session?.valid_until ?? '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!start || !end || minutesOf(end) <= minutesOf(start)) {
      setError('La hora de fin debe ser posterior a la de inicio.')
      return
    }
    if (!validFrom) {
      setError('Indica desde qué fecha rige la clase.')
      return
    }
    if (validUntil && validUntil < validFrom) {
      setError('La fecha final no puede ser anterior a la inicial.')
      return
    }
    if (!timezone.trim()) {
      setError('Indica la zona horaria.')
      return
    }
    setBusy(true)
    setError(null)
    const body: SessionInput = {
      weekday: Number(weekday),
      starts_local_time: toApiTime(start),
      ends_local_time: toApiTime(end),
      timezone: timezone.trim(),
      valid_from: validFrom,
      valid_until: validUntil || null,
      room: room.trim() || null
    }
    try {
      if (session) {
        const result = await updateSession(session.id, session.revision, body)
        const conflicts = (result as { conflicts?: readonly ConflictItem[] } | null)?.conflicts
        onSaved(conflicts ?? [])
      } else {
        const result = await createSession(subjectId, body)
        onSaved(result.conflicts)
      }
    } catch (e) {
      setError(errorText(e))
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-4" noValidate>
      <DialogHeader>
        <DialogTitle>{session ? 'Editar clase' : 'Nueva clase semanal'}</DialogTitle>
        <DialogDescription>
          Se repite cada semana mientras esté vigente. Las horas son locales a la zona indicada.
        </DialogDescription>
      </DialogHeader>
      <Field label="Día de la semana" htmlFor={`${id}-day`}>
        <Select value={weekday} onValueChange={setWeekday}>
          <SelectTrigger id={`${id}-day`} className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {WEEKDAYS.map((name, index) => (
              <SelectItem key={name} value={String(index + 1)}>
                {name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Empieza" htmlFor={`${id}-start`}>
          <TextInput id={`${id}-start`} type="time" value={start} required onChange={(e) => setStart(e.target.value)} />
        </Field>
        <Field label="Termina" htmlFor={`${id}-end`}>
          <TextInput id={`${id}-end`} type="time" value={end} required onChange={(e) => setEnd(e.target.value)} />
        </Field>
      </div>
      <Field label="Aula" htmlFor={`${id}-room`}>
        <TextInput id={`${id}-room`} value={room} maxLength={200} onChange={(e) => setRoom(e.target.value)} />
      </Field>
      <Field label="Zona horaria" htmlFor={`${id}-tz`} hint="Nombre IANA, por ejemplo Europe/Madrid.">
        <TextInput id={`${id}-tz`} value={timezone} maxLength={64} required onChange={(e) => setTimezone(e.target.value)} />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Vigente desde" htmlFor={`${id}-from`}>
          <TextInput id={`${id}-from`} type="date" value={validFrom} required onChange={(e) => setValidFrom(e.target.value)} />
        </Field>
        <Field label="Hasta (opcional)" htmlFor={`${id}-until`}>
          <TextInput id={`${id}-until`} type="date" value={validUntil} onChange={(e) => setValidUntil(e.target.value)} />
        </Field>
      </div>
      <FormError message={error} />
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onClose} disabled={busy}>
          Cancelar
        </Button>
        <Button type="submit" disabled={busy}>
          {busy ? 'Guardando…' : session ? 'Guardar cambios' : 'Añadir clase'}
        </Button>
      </DialogFooter>
    </form>
  )
}
