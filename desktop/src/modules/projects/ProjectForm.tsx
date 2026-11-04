import { useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { notify } from '@/services/notify'
import { ApiError } from '@/services/api'
import { Field, TextInput } from '../tasks/Field'
import {
  MAX_DESCRIPTION,
  MAX_NAME,
  MAX_OBJECTIVE,
  PRIORITIES,
  PRIORITY_LABELS,
  PROJECT_STATUSES,
  PROJECT_STATUS_LABELS,
  type Priority,
  type Project,
  type ProjectCreate,
  type ProjectStatus,
  type ProjectUpdate
} from './types'

interface Values {
  name: string
  description: string
  objective: string
  status: ProjectStatus
  priority: Priority
  start_date: string
  target_date: string
  manual_progress: string
}

function initial(project: Project | null): Values {
  return {
    name: project?.name ?? '',
    description: project?.description ?? '',
    objective: project?.objective ?? '',
    status: project?.status ?? 'planned',
    priority: project?.priority ?? 'medium',
    start_date: project?.start_date ?? '',
    target_date: project?.target_date ?? '',
    manual_progress: project?.manual_progress === null || project === null ? '' : String(project.manual_progress)
  }
}

type Errors = Partial<Record<keyof Values, string>>

function validate(v: Values): Errors {
  const errors: Errors = {}
  if (v.name.trim() === '') errors.name = 'Ponle un nombre al proyecto.'
  if (v.start_date !== '' && v.target_date !== '' && v.start_date > v.target_date) {
    errors.target_date = 'La fecha objetivo no puede ser anterior al inicio.'
  }
  if (v.manual_progress !== '') {
    const n = Number(v.manual_progress)
    if (!Number.isInteger(n) || n < 0 || n > 100) errors.manual_progress = 'Escribe un número entero entre 0 y 100.'
  }
  return errors
}

const orNull = (text: string): string | null => (text.trim() === '' ? null : text.trim())

function toCreate(v: Values): ProjectCreate {
  const data: Record<string, unknown> = { name: v.name.trim(), status: v.status, priority: v.priority }
  if (v.description.trim() !== '') data.description = v.description.trim()
  if (v.objective.trim() !== '') data.objective = v.objective.trim()
  if (v.start_date !== '') data.start_date = v.start_date
  if (v.target_date !== '') data.target_date = v.target_date
  if (v.manual_progress !== '') data.manual_progress = Number(v.manual_progress)
  return data as unknown as ProjectCreate
}

/** Solo los campos que cambian; vacío en un campo opcional lo borra. */
function toPatch(v: Values, p: Project): ProjectUpdate {
  const patch: Record<string, unknown> = {}
  if (v.name.trim() !== p.name) patch.name = v.name.trim()
  if (orNull(v.description) !== p.description) patch.description = orNull(v.description)
  if (orNull(v.objective) !== p.objective) patch.objective = orNull(v.objective)
  if (v.status !== p.status) patch.status = v.status
  if (v.priority !== p.priority) patch.priority = v.priority
  if ((v.start_date || null) !== p.start_date) patch.start_date = v.start_date || null
  if ((v.target_date || null) !== p.target_date) patch.target_date = v.target_date || null
  const manual = v.manual_progress === '' ? null : Number(v.manual_progress)
  if (manual !== p.manual_progress) patch.manual_progress = manual
  return patch as ProjectUpdate
}

export interface ProjectFormProps {
  readonly open: boolean
  /** `null` crea un proyecto nuevo. */
  readonly project: Project | null
  readonly onClose: () => void
  /** Hace la llamada al backend; si lanza, el formulario muestra el motivo. */
  readonly onSubmit: (data: ProjectCreate | ProjectUpdate) => Promise<void>
  /** El proyecto cambió por otro lado: recargar. */
  readonly onStale: () => void
}

export function ProjectForm({ open, project, onClose, onSubmit, onStale }: ProjectFormProps) {
  return (
    <Dialog open={open} onOpenChange={(next) => (next ? undefined : onClose())}>
      <DialogContent className="max-h-[90vh] overflow-y-auto rounded-[var(--radius-sheet)] sm:max-w-xl">
        {open ? (
          <FormBody key={project?.id ?? 'nuevo'} project={project} onClose={onClose} onSubmit={onSubmit} onStale={onStale} />
        ) : null}
      </DialogContent>
    </Dialog>
  )
}

function FormBody({ project, onClose, onSubmit, onStale }: Omit<ProjectFormProps, 'open'>) {
  const [values, setValues] = useState<Values>(() => initial(project))
  const [errors, setErrors] = useState<Errors>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const set = <K extends keyof Values>(key: K, value: Values[K]) => setValues((c) => ({ ...c, [key]: value }))

  async function submit(event: FormEvent) {
    event.preventDefault()
    const found = validate(values)
    setErrors(found)
    setFormError(null)
    if (Object.keys(found).length > 0) return
    let data: ProjectCreate | ProjectUpdate
    if (project === null) data = toCreate(values)
    else {
      data = toPatch(values, project)
      if (Object.keys(data).length === 0) {
        onClose()
        return
      }
    }
    setBusy(true)
    try {
      await onSubmit(data)
      onClose()
    } catch (error) {
      if (error instanceof ApiError && error.code === 'revision_mismatch') {
        notify({
          tone: 'warning',
          title: 'El proyecto había cambiado',
          body: 'Se modificó mientras lo editabas. He recargado los datos; vuelve a intentarlo.'
        })
        onStale()
        onClose()
      } else if (error instanceof ApiError) {
        setFormError(error.code === 'conflict' ? (error.details[0]?.message ?? error.message) : error.message)
        const fieldErrors: Errors = {}
        for (const item of error.details) {
          if (item.field !== null && item.field in values) fieldErrors[item.field as keyof Values] = item.message
        }
        setErrors(fieldErrors)
      } else {
        setFormError(error instanceof Error ? error.message : 'No se pudo guardar el proyecto.')
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={(e) => void submit(e)} className="flex flex-col gap-4" noValidate>
      <DialogHeader>
        <DialogTitle>{project === null ? 'Nuevo proyecto' : 'Editar proyecto'}</DialogTitle>
        <DialogDescription>
          {project === null
            ? 'Lo esencial basta; el resto puedes añadirlo después.'
            : 'Cambia solo lo que necesites.'}
        </DialogDescription>
      </DialogHeader>

      <Field label="Nombre" error={errors.name ?? null}>
        {(c) => (
          <TextInput {...c} value={values.name} maxLength={MAX_NAME} autoFocus onChange={(e) => set('name', e.target.value)} />
        )}
      </Field>
      <Field label="Objetivo" hint="Qué quieres conseguir con este proyecto." error={errors.objective ?? null}>
        {(c) => (
          <Textarea {...c} rows={2} value={values.objective} maxLength={MAX_OBJECTIVE} onChange={(e) => set('objective', e.target.value)} />
        )}
      </Field>
      <Field label="Descripción" error={errors.description ?? null}>
        {(c) => (
          <Textarea {...c} rows={3} value={values.description} maxLength={MAX_DESCRIPTION} onChange={(e) => set('description', e.target.value)} />
        )}
      </Field>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Estado">
          {(c) => (
            <Select value={values.status} onValueChange={(v) => set('status', v as ProjectStatus)}>
              <SelectTrigger id={c.id} className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PROJECT_STATUSES.map((s) => (
                  <SelectItem key={s} value={s}>
                    {PROJECT_STATUS_LABELS[s]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </Field>
        <Field label="Prioridad">
          {(c) => (
            <Select value={values.priority} onValueChange={(v) => set('priority', v as Priority)}>
              <SelectTrigger id={c.id} className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PRIORITIES.map((p) => (
                  <SelectItem key={p} value={p}>
                    {PRIORITY_LABELS[p]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </Field>
        <Field label="Inicio">
          {(c) => <TextInput {...c} type="date" value={values.start_date} onChange={(e) => set('start_date', e.target.value)} />}
        </Field>
        <Field label="Fecha objetivo" error={errors.target_date ?? null}>
          {(c) => <TextInput {...c} type="date" value={values.target_date} onChange={(e) => set('target_date', e.target.value)} />}
        </Field>
      </div>

      <Field
        label="Progreso manual (0-100)"
        hint="Déjalo vacío para que el progreso se calcule con las tareas."
        error={errors.manual_progress ?? null}
      >
        {(c) => (
          <TextInput {...c} type="number" min={0} max={100} step={1} inputMode="numeric" value={values.manual_progress} onChange={(e) => set('manual_progress', e.target.value)} className="w-32" />
        )}
      </Field>

      {formError !== null ? (
        <p role="alert" className="text-sm text-destructive">
          {formError}
        </p>
      ) : null}

      <DialogFooter>
        <Button type="button" variant="outline" disabled={busy} onClick={onClose}>
          Cancelar
        </Button>
        <Button type="submit" disabled={busy}>
          {busy ? 'Guardando…' : project === null ? 'Crear proyecto' : 'Guardar cambios'}
        </Button>
      </DialogFooter>
    </form>
  )
}
