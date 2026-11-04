import { useId, useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { errorText } from '@/modules/calendar/workspaceApi'
import { cn } from '@/lib/utils'
import { createSubject, updateSubject } from './api'
import { Field, FormError, TextInput } from './fields'
import { SUBJECT_PALETTE } from './palette'
import type { Subject } from './types'

interface Props {
  readonly open: boolean
  /** Asignatura a editar; null para crear. */
  readonly subject: Subject | null
  readonly onClose: () => void
  readonly onSaved: (subject: Subject) => void
}

export function SubjectDialog({ open, subject, onClose, onSaved }: Props) {
  return (
    <Dialog open={open} onOpenChange={(next) => (next ? undefined : onClose())}>
      <DialogContent>
        {/* La clave reinicia el formulario al cambiar de asignatura. */}
        <SubjectForm key={subject?.id ?? 'new'} subject={subject} onClose={onClose} onSaved={onSaved} />
      </DialogContent>
    </Dialog>
  )
}

function SubjectForm({ subject, onClose, onSaved }: Omit<Props, 'open'>) {
  const id = useId()
  const [name, setName] = useState(subject?.name ?? '')
  const [teacher, setTeacher] = useState(subject?.teacher ?? '')
  const [description, setDescription] = useState(subject?.description ?? '')
  const [color, setColor] = useState<string | null>(subject?.color ?? null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!name.trim()) {
      setError('Escribe el nombre de la asignatura.')
      return
    }
    setBusy(true)
    setError(null)
    const body = {
      name: name.trim(),
      teacher: teacher.trim() || null,
      description: description.trim() || null,
      color
    }
    try {
      const saved = subject ? await updateSubject(subject.id, subject.revision, body) : await createSubject(body)
      onSaved(saved)
    } catch (e) {
      setError(errorText(e))
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-4" noValidate>
      <DialogHeader>
        <DialogTitle>{subject ? 'Editar asignatura' : 'Nueva asignatura'}</DialogTitle>
        <DialogDescription>El color identifica la asignatura en el horario y en el calendario.</DialogDescription>
      </DialogHeader>
      <Field label="Nombre" htmlFor={`${id}-name`}>
        <TextInput id={`${id}-name`} value={name} maxLength={200} required autoFocus onChange={(e) => setName(e.target.value)} />
      </Field>
      <Field label="Profesor o profesora" htmlFor={`${id}-teacher`}>
        <TextInput id={`${id}-teacher`} value={teacher} maxLength={200} onChange={(e) => setTeacher(e.target.value)} />
      </Field>
      <Field label="Descripción" htmlFor={`${id}-desc`}>
        <Textarea id={`${id}-desc`} value={description} maxLength={4000} rows={3} onChange={(e) => setDescription(e.target.value)} />
      </Field>
      <fieldset className="grid gap-1.5">
        <legend className="text-sm font-medium text-foreground">Color</legend>
        <div role="radiogroup" aria-label="Color" className="flex flex-wrap gap-2">
          {SUBJECT_PALETTE.map((option) => {
            const selected = color?.toLowerCase() === option.hex
            return (
              <button
                key={option.hex}
                type="button"
                role="radio"
                aria-checked={selected}
                aria-label={option.name}
                title={option.name}
                onClick={() => setColor(selected ? null : option.hex)}
                style={{ backgroundColor: option.hex }}
                className={cn(
                  'size-8 rounded-md border border-border outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50',
                  selected && 'ring-2 ring-foreground ring-offset-2 ring-offset-background'
                )}
              />
            )
          })}
        </div>
        <p className="text-xs text-muted-foreground">Pulsa de nuevo el color elegido para quitarlo.</p>
      </fieldset>
      <FormError message={error} />
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onClose} disabled={busy}>
          Cancelar
        </Button>
        <Button type="submit" disabled={busy}>
          {busy ? 'Guardando…' : subject ? 'Guardar cambios' : 'Crear asignatura'}
        </Button>
      </DialogFooter>
    </form>
  )
}
