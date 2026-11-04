import { useId, useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { errorText } from '@/modules/calendar/workspaceClient'
import { createException } from './api'
import { Field, FormError, TextInput } from './fields'
import { hhmm, minutesOf, toApiTime, weekdayName, weekdayOf } from './format'
import type { ClassSession, ExceptionInput } from './types'

interface Props {
  readonly session: ClassSession | null
  readonly onClose: () => void
  readonly onSaved: () => void
}

export function ExceptionDialog({ session, onClose, onSaved }: Props) {
  return (
    <Dialog open={session !== null} onOpenChange={(next) => (next ? undefined : onClose())}>
      <DialogContent>
        {session ? <ExceptionForm key={session.id} session={session} onClose={onClose} onSaved={onSaved} /> : null}
      </DialogContent>
    </Dialog>
  )
}

function ExceptionForm({ session, onClose, onSaved }: { session: ClassSession; onClose: () => void; onSaved: () => void }) {
  const id = useId()
  const [date, setDate] = useState('')
  const [mode, setMode] = useState<'cancelled' | 'modified'>('cancelled')
  const [start, setStart] = useState(hhmm(session.starts_local_time))
  const [end, setEnd] = useState(hhmm(session.ends_local_time))
  const [room, setRoom] = useState(session.room ?? '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!date) {
      setError('Elige la fecha de la clase afectada.')
      return
    }
    if (weekdayOf(date) !== session.weekday) {
      setError(`Esa fecha cae en otro día: esta clase es los ${weekdayName(session.weekday).toLowerCase()}.`)
      return
    }
    if (date < session.valid_from || (session.valid_until && date > session.valid_until)) {
      setError('Esa fecha queda fuera de la vigencia de la clase.')
      return
    }
    let body: ExceptionInput
    if (mode === 'cancelled') {
      body = { occurrence_date: date, kind: 'cancelled' }
    } else {
      if (!start || !end || minutesOf(end) <= minutesOf(start)) {
        setError('La hora de fin debe ser posterior a la de inicio.')
        return
      }
      body = {
        occurrence_date: date,
        kind: 'modified',
        override: {
          local_start: `${date}T${toApiTime(start)}`,
          local_end: `${date}T${toApiTime(end)}`,
          ...(room.trim() ? { room: room.trim() } : {})
        }
      }
    }
    setBusy(true)
    setError(null)
    try {
      await createException(session.id, body)
      onSaved()
    } catch (e) {
      setError(errorText(e))
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-4" noValidate>
      <DialogHeader>
        <DialogTitle>Excepción de una clase</DialogTitle>
        <DialogDescription>
          Afecta solo a un {weekdayName(session.weekday).toLowerCase()} concreto; el resto de semanas no cambia.
        </DialogDescription>
      </DialogHeader>
      <Field label="Fecha de la clase" htmlFor={`${id}-date`}>
        <TextInput id={`${id}-date`} type="date" value={date} min={session.valid_from} required onChange={(e) => setDate(e.target.value)} />
      </Field>
      <fieldset className="grid gap-2">
        <legend className="text-sm font-medium text-foreground">Qué ocurre ese día</legend>
        {(['cancelled', 'modified'] as const).map((value) => (
          <label key={value} className="flex items-center gap-2 text-sm text-foreground">
            <input
              type="radio"
              name={`${id}-mode`}
              value={value}
              checked={mode === value}
              onChange={() => setMode(value)}
              className="size-4 accent-primary"
            />
            {value === 'cancelled' ? 'Se cancela la clase' : 'Cambia la hora o el aula'}
          </label>
        ))}
      </fieldset>
      {mode === 'modified' ? (
        <>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Nueva hora de inicio" htmlFor={`${id}-start`}>
              <TextInput id={`${id}-start`} type="time" value={start} required onChange={(e) => setStart(e.target.value)} />
            </Field>
            <Field label="Nueva hora de fin" htmlFor={`${id}-end`}>
              <TextInput id={`${id}-end`} type="time" value={end} required onChange={(e) => setEnd(e.target.value)} />
            </Field>
          </div>
          <Field label="Aula ese día" htmlFor={`${id}-room`}>
            <TextInput id={`${id}-room`} value={room} maxLength={200} onChange={(e) => setRoom(e.target.value)} />
          </Field>
        </>
      ) : null}
      <FormError message={error} />
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onClose} disabled={busy}>
          Cancelar
        </Button>
        <Button type="submit" disabled={busy}>
          {busy ? 'Guardando…' : 'Guardar excepción'}
        </Button>
      </DialogFooter>
    </form>
  )
}
