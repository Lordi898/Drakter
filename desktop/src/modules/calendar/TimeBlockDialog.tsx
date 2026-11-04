import { useEffect, useId, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { systemTimeZone, timeZoneList } from './dateUtils'
import { createTimeBlock, getTimeBlock, updateTimeBlock } from './api'
import { defaultRange, describeFailure, Field, inputClass, localIso, type FormFailure } from './formUtils'
import { STATUS_LABELS } from './kinds'
import type { AgendaItem, TimeBlockPayload, TimeBlockStatus } from './types'

export type TimeBlockDialogTarget =
  | { readonly mode: 'create'; readonly day: string; readonly minutes: number }
  | { readonly mode: 'edit'; readonly blockId: string }

export interface TimeBlockDialogProps {
  readonly target: TimeBlockDialogTarget | null
  readonly timezone: string
  readonly onClose: () => void
  readonly onSaved: (conflicts: readonly AgendaItem[]) => void
}

const STATUSES: readonly TimeBlockStatus[] = ['planned', 'in_progress', 'done', 'skipped', 'cancelled']

export function TimeBlockDialog({ target, timezone, onClose, onSaved }: TimeBlockDialogProps) {
  const uid = useId()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [failure, setFailure] = useState<FormFailure | null>(null)
  const [revision, setRevision] = useState<number | null>(null)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [status, setStatus] = useState<TimeBlockStatus>('planned')
  const [tz, setTz] = useState(timezone)
  const [taskId, setTaskId] = useState('')
  const [startDate, setStartDate] = useState('')
  const [startTime, setStartTime] = useState('09:00')
  const [endDate, setEndDate] = useState('')
  const [endTime, setEndTime] = useState('10:00')

  useEffect(() => {
    if (!target) return
    setFailure(null)
    setSaving(false)
    setRevision(null)
    if (target.mode === 'create') {
      const range = defaultRange(target.day, target.minutes)
      setTitle('')
      setDescription('')
      setStatus('planned')
      setTz(timezone || systemTimeZone())
      setTaskId('')
      setStartDate(range.startDate)
      setStartTime(range.startTime)
      setEndDate(range.endDate)
      setEndTime(range.endTime)
      return
    }
    let active = true
    setLoading(true)
    getTimeBlock(target.blockId)
      .then((block) => {
        if (!active) return
        setRevision(block.revision)
        setTitle(block.title)
        setDescription(block.description ?? '')
        setStatus(block.status)
        setTz(block.timezone)
        setTaskId(block.task_id ?? '')
        setStartDate(block.local_start.slice(0, 10))
        setStartTime(block.local_start.slice(11, 16))
        setEndDate(block.local_end.slice(0, 10))
        setEndTime(block.local_end.slice(11, 16))
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

  async function submit(event: React.FormEvent): Promise<void> {
    event.preventDefault()
    if (!target) return
    const cleanTitle = title.trim()
    if (!cleanTitle) return setFailure({ message: 'El título es obligatorio.', nonexistentTime: false })
    if (localIso(endDate, endTime) <= localIso(startDate, startTime)) {
      return setFailure({ message: 'El final debe ser posterior al inicio.', nonexistentTime: false })
    }
    const payload: TimeBlockPayload = {
      title: cleanTitle,
      description: description.trim() || null,
      timezone: tz,
      local_start: localIso(startDate, startTime),
      local_end: localIso(endDate, endTime),
      status,
      task_id: taskId.trim() || null
    }
    setSaving(true)
    setFailure(null)
    try {
      const result =
        target.mode === 'edit' && revision !== null
          ? await updateTimeBlock(target.blockId, payload, revision)
          : await createTimeBlock(payload)
      onSaved(result.conflicts)
    } catch (error) {
      setFailure(describeFailure(error, tz))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{editing ? 'Editar bloque de tiempo' : 'Nuevo bloque de tiempo'}</DialogTitle>
          <DialogDescription>Reserva un tramo de tu agenda. Las horas son locales en la zona elegida.</DialogDescription>
        </DialogHeader>
        <form onSubmit={(e) => void submit(e)} className="grid gap-4" aria-busy={loading}>
          <Field id={`${uid}-title`} label="Título">
            <input id={`${uid}-title`} className={inputClass} value={title} onChange={(e) => setTitle(e.target.value)} maxLength={300} required autoFocus disabled={loading} />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field id={`${uid}-sd`} label="Inicio" error={timeError}>
              <div className="flex gap-2">
                <input id={`${uid}-sd`} type="date" className={inputClass} value={startDate} onChange={(e) => setStartDate(e.target.value)} required disabled={loading} aria-invalid={timeError !== null} />
                <input aria-label="Hora de inicio" type="time" className={inputClass} value={startTime} onChange={(e) => setStartTime(e.target.value)} required disabled={loading} aria-invalid={timeError !== null} />
              </div>
            </Field>
            <Field id={`${uid}-ed`} label="Final">
              <div className="flex gap-2">
                <input id={`${uid}-ed`} type="date" className={inputClass} value={endDate} onChange={(e) => setEndDate(e.target.value)} required disabled={loading} />
                <input aria-label="Hora de final" type="time" className={inputClass} value={endTime} onChange={(e) => setEndTime(e.target.value)} required disabled={loading} aria-invalid={timeError !== null} />
              </div>
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field id={`${uid}-tz`} label="Zona horaria">
              <select id={`${uid}-tz`} className={inputClass} value={tz} onChange={(e) => setTz(e.target.value)} disabled={loading}>
                {timeZoneList(tz).map((z) => (
                  <option key={z} value={z}>{z}</option>
                ))}
              </select>
            </Field>
            <Field id={`${uid}-status`} label="Estado">
              <select id={`${uid}-status`} className={inputClass} value={status} onChange={(e) => setStatus(e.target.value as TimeBlockStatus)} disabled={loading}>
                {STATUSES.map((s) => (
                  <option key={s} value={s}>{STATUS_LABELS[s] ?? s}</option>
                ))}
              </select>
            </Field>
          </div>
          <Field id={`${uid}-task`} label="Tarea vinculada (opcional)" hint="Identificador de la tarea. El selector llegará con el módulo de tareas.">
            <input id={`${uid}-task`} className={inputClass} value={taskId} onChange={(e) => setTaskId(e.target.value)} placeholder="ID de la tarea" disabled={loading} />
          </Field>
          <Field id={`${uid}-desc`} label="Descripción">
            <Textarea id={`${uid}-desc`} value={description} onChange={(e) => setDescription(e.target.value)} maxLength={8000} rows={3} disabled={loading} />
          </Field>
          {generalError ? <p role="alert" className="text-sm text-destructive">{generalError}</p> : null}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>Cancelar</Button>
            <Button type="submit" disabled={saving || loading || (editing && revision === null)}>
              {saving ? 'Guardando…' : editing ? 'Guardar cambios' : 'Crear bloque'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
