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
import { createSubtask, createTask, replaceTaskTags, updateTask } from './api'
import { Field, TextInput } from './Field'
import type { RunTask } from './useTaskRunner'
import {
  PRIORITIES,
  PRIORITY_LABELS,
  TASK_STATUSES,
  TASK_STATUS_LABELS,
  type EditableTaskStatus,
  type Priority,
  type Task,
  type TaskCreate,
  type TaskUpdate
} from './types'

export interface TaskFormProps {
  readonly open: boolean
  readonly onOpenChange: (open: boolean) => void
  readonly run: RunTask
  /** Si se pasa, se edita; si no, se crea. */
  readonly task?: Task
  /** Crea una subtarea de esta tarea. */
  readonly parent?: { readonly id: string; readonly title: string }
  readonly onSaved?: (task: Task) => void
}

export function TaskForm({ open, onOpenChange, ...rest }: TaskFormProps) {
  const editing = rest.task !== undefined
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto rounded-[var(--radius-sheet)]">
        <DialogHeader>
          <DialogTitle>
            {editing ? 'Editar tarea' : rest.parent ? 'Nueva subtarea' : 'Nueva tarea'}
          </DialogTitle>
          <DialogDescription>
            {rest.parent ? `Dentro de «${rest.parent.title}».` : 'Lo mínimo es el título; lo demás puedes completarlo luego.'}
          </DialogDescription>
        </DialogHeader>
        <TaskFormBody {...rest} onClose={() => onOpenChange(false)} />
      </DialogContent>
    </Dialog>
  )
}

export function parseTags(text: string): string[] {
  const seen = new Set<string>()
  for (const part of text.split(',')) {
    const name = part.trim()
    if (name !== '') seen.add(name)
  }
  return [...seen]
}

function sameList(a: readonly string[], b: readonly string[]): boolean {
  return a.length === b.length && a.every((value, index) => value === b[index])
}

function TaskFormBody({
  run,
  task,
  parent,
  onSaved,
  onClose
}: Omit<TaskFormProps, 'open' | 'onOpenChange'> & { readonly onClose: () => void }) {
  const [title, setTitle] = useState(task?.title ?? '')
  const [description, setDescription] = useState(task?.description ?? '')
  const [status, setStatus] = useState<EditableTaskStatus>(
    task === undefined || task.status === 'completed' ? 'pending' : task.status
  )
  const [priority, setPriority] = useState<Priority>(task?.priority ?? 'medium')
  const [dueDate, setDueDate] = useState(task?.due_date ?? '')
  const [minutes, setMinutes] = useState(task?.estimated_minutes?.toString() ?? '')
  const [tags, setTags] = useState(task?.tags.map((tag) => tag.name).join(', ') ?? '')
  const [titleError, setTitleError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const completed = task?.status === 'completed'

  async function submit(event: FormEvent) {
    event.preventDefault()
    const cleanTitle = title.trim()
    if (cleanTitle === '') {
      setTitleError('Escribe un título.')
      return
    }
    setTitleError(null)
    const estimated = minutes.trim() === '' ? null : Number(minutes)
    const cleanDescription = description.trim() === '' ? null : description.trim()
    const tagNames = parseTags(tags)
    setSaving(true)
    const saved = await run(async () => {
      if (task === undefined) {
        const data: Omit<TaskCreate, 'parent_task_id'> = {
          title: cleanTitle,
          description: cleanDescription,
          status,
          priority,
          due_date: dueDate === '' ? null : dueDate,
          estimated_minutes: estimated,
          tags: tagNames
        }
        return parent ? createSubtask(parent.id, data) : createTask(data)
      }
      const patch: { -readonly [K in keyof TaskUpdate]: TaskUpdate[K] } = {}
      if (cleanTitle !== task.title) patch.title = cleanTitle
      if (cleanDescription !== task.description) patch.description = cleanDescription
      if (!completed && status !== task.status) patch.status = status
      if (priority !== task.priority) patch.priority = priority
      if ((dueDate === '' ? null : dueDate) !== task.due_date) patch.due_date = dueDate === '' ? null : dueDate
      if (estimated !== task.estimated_minutes) patch.estimated_minutes = estimated
      let result = task
      if (Object.keys(patch).length > 0) result = await updateTask(task.id, patch, task.revision)
      if (!sameList(tagNames, task.tags.map((tag) => tag.name))) result = await replaceTaskTags(task.id, tagNames)
      return result
    }, task === undefined ? 'Tarea creada' : 'Cambios guardados')
    setSaving(false)
    if (saved !== undefined) {
      onSaved?.(saved)
      onClose()
    }
  }

  return (
    <form onSubmit={(event) => void submit(event)} className="flex flex-col gap-4" noValidate>
      <Field label="Título" error={titleError}>
        {(control) => (
          <TextInput
            {...control}
            value={title}
            maxLength={300}
            autoFocus
            onChange={(event) => setTitle(event.target.value)}
          />
        )}
      </Field>
      <Field label="Descripción">
        {(control) => (
          <Textarea {...control} rows={3} value={description} onChange={(event) => setDescription(event.target.value)} />
        )}
      </Field>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Estado" hint={completed ? 'Está completada: reábrela para cambiar el estado.' : undefined}>
          {(control) => (
            <Select value={status} disabled={completed} onValueChange={(value) => setStatus(value as EditableTaskStatus)}>
              <SelectTrigger id={control.id} className="w-full" aria-describedby={control['aria-describedby']}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TASK_STATUSES.filter((value) => value !== 'completed').map((value) => (
                  <SelectItem key={value} value={value}>
                    {TASK_STATUS_LABELS[value]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </Field>
        <Field label="Prioridad">
          {(control) => (
            <Select value={priority} onValueChange={(value) => setPriority(value as Priority)}>
              <SelectTrigger id={control.id} className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PRIORITIES.map((value) => (
                  <SelectItem key={value} value={value}>
                    {PRIORITY_LABELS[value]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </Field>
        <Field label="Fecha límite">
          {(control) => (
            <TextInput {...control} type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} />
          )}
        </Field>
        <Field label="Estimación (minutos)">
          {(control) => (
            <TextInput
              {...control}
              type="number"
              min={0}
              inputMode="numeric"
              value={minutes}
              onChange={(event) => setMinutes(event.target.value)}
            />
          )}
        </Field>
      </div>
      <Field label="Etiquetas" hint="Separadas por comas.">
        {(control) => <TextInput {...control} value={tags} onChange={(event) => setTags(event.target.value)} />}
      </Field>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onClose}>
          Cancelar
        </Button>
        <Button type="submit" disabled={saving}>
          {saving ? 'Guardando…' : task === undefined ? 'Crear' : 'Guardar'}
        </Button>
      </DialogFooter>
    </form>
  )
}
