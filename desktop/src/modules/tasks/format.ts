import type { HistoryEntry, Priority, Task, TaskStatus } from './types'
import { PRIORITY_LABELS, TASK_STATUS_LABELS } from './types'

const dateFormat = new Intl.DateTimeFormat('es', { day: 'numeric', month: 'short', year: 'numeric' })
const dateTimeFormat = new Intl.DateTimeFormat('es', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit'
})

/** `due_date` es una fecha sin hora (AAAA-MM-DD): se muestra tal cual, sin convertir de zona. */
export function formatDueDate(value: string): string {
  const [year, month, day] = value.split('-').map(Number)
  if (year === undefined || month === undefined || day === undefined) return value
  return dateFormat.format(new Date(year, month - 1, day))
}

/** Los instantes se guardan en UTC y se muestran en la zona local. */
export function formatInstant(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : dateTimeFormat.format(date)
}

function todayLocal(): string {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${month}-${day}`
}

export function isOpen(status: TaskStatus): boolean {
  return status !== 'completed' && status !== 'cancelled'
}

export function isOverdue(task: Pick<Task, 'status' | 'due_date' | 'due_at'>): boolean {
  if (!isOpen(task.status)) return false
  if (task.due_date !== null) return task.due_date < todayLocal()
  if (task.due_at !== null) return new Date(task.due_at).getTime() < Date.now()
  return false
}

/** Texto de la fecha límite de una tarea, o `null` si no tiene. */
export function dueLabel(task: Pick<Task, 'due_date' | 'due_at'>): string | null {
  if (task.due_date !== null) return formatDueDate(task.due_date)
  if (task.due_at !== null) return formatInstant(task.due_at)
  return null
}

const FIELD_LABELS: Readonly<Record<string, string>> = {
  title: 'el título',
  description: 'la descripción',
  status: 'el estado',
  priority: 'la prioridad',
  start_at: 'la fecha de inicio',
  due_at: 'el vencimiento',
  due_date: 'la fecha límite',
  estimated_minutes: 'la estimación',
  parent_task_id: 'la tarea principal',
  project_id: 'el proyecto',
  subject_id: 'la asignatura',
  position: 'la posición',
  completed_at: 'la fecha de cierre',
  archived_at: 'el archivado',
  tags: 'las etiquetas'
}

function formatValue(field: string, value: unknown): string {
  if (value === null || value === undefined || value === '') return 'vacío'
  if (field === 'status' && typeof value === 'string') {
    return TASK_STATUS_LABELS[value as TaskStatus] ?? value
  }
  if (field === 'priority' && typeof value === 'string') {
    return PRIORITY_LABELS[value as Priority] ?? value
  }
  if (field === 'due_date' && typeof value === 'string') return formatDueDate(value)
  if ((field === 'due_at' || field === 'start_at' || field.endsWith('_at')) && typeof value === 'string') {
    return formatInstant(value)
  }
  if (field === 'estimated_minutes' && typeof value === 'number') return `${value} min`
  if (Array.isArray(value)) return value.length === 0 ? 'ninguna' : value.join(', ')
  if (typeof value === 'string') return value.length > 60 ? `${value.slice(0, 57)}…` : value
  return String(value)
}

function isChange(value: unknown): value is { from?: unknown; to?: unknown } {
  return typeof value === 'object' && value !== null && ('from' in value || 'to' in value)
}

export function actorLabel(actor: HistoryEntry['actor_type']): string {
  switch (actor) {
    case 'user':
      return 'Tú'
    case 'agent':
      return 'Drakter'
    case 'automation':
      return 'Una automatización'
    case 'system':
      return 'El sistema'
  }
}

// Pretéritos de las frases de historial en segunda persona, para «Tú …».
const SECOND_PERSON: Readonly<Record<string, string>> = {
  creó: 'creaste',
  modificó: 'modificaste',
  completó: 'completaste',
  reabrió: 'reabriste',
  archivó: 'archivaste',
  restauró: 'restauraste',
  eliminó: 'eliminaste',
  cambió: 'cambiaste',
  añadió: 'añadiste',
  quitó: 'quitaste',
  intentó: 'intentaste',
  pidió: 'pediste',
  realizó: 'realizaste',
  pudo: 'pudiste'
}

/** Conjuga la frase (en tercera persona) para el actor: «Tú creaste», «Drakter creó». */
export function forActor(actor: HistoryEntry['actor_type'], phrase: string): string {
  if (actor !== 'user') return phrase
  return phrase.replace(/^(no )?(\p{L}+)/u, (whole, no: string | undefined, verb: string) =>
    verb in SECOND_PERSON ? `${no ?? ''}${SECOND_PERSON[verb]}` : whole
  )
}

const ACTION_LABELS: Readonly<Record<string, string>> = {
  'task.create': 'creó la tarea',
  'task.update': 'modificó la tarea',
  'task.complete': 'completó la tarea',
  'task.reopen': 'reabrió la tarea',
  'task.archive': 'archivó la tarea',
  'task.unarchive': 'restauró la tarea',
  'task.delete': 'eliminó la tarea',
  'task.tags': 'cambió las etiquetas',
  'task.dependency_add': 'añadió una dependencia',
  'task.dependency_remove': 'quitó una dependencia'
}

export interface HistoryLine {
  readonly id: string
  readonly when: string
  readonly actor: string
  readonly isAgent: boolean
  readonly summary: string
  readonly details: readonly string[]
}

export function describeHistory(entry: HistoryEntry): HistoryLine {
  const base = ACTION_LABELS[entry.action] ?? `realizó la acción «${entry.action}»`
  let summary = base
  if (entry.result === 'denied') summary = `intentó una acción sin permiso (${base})`
  else if (entry.result === 'failed') summary = `no pudo completar: ${base}`
  else if (entry.result === 'confirmation_required') summary = `pidió confirmación para ${base}`

  const details: string[] = []
  for (const [field, change] of Object.entries(entry.changes ?? {})) {
    const label = FIELD_LABELS[field] ?? field
    if (typeof change === 'object' && change !== null && 'changed' in change) {
      details.push(`${label[0]?.toUpperCase() ?? ''}${label.slice(1)}: modificado`)
    } else if (isChange(change)) {
      details.push(`${label[0]?.toUpperCase() ?? ''}${label.slice(1)}: ${formatValue(field, change.from)} → ${formatValue(field, change.to)}`)
    } else {
      details.push(`${label[0]?.toUpperCase() ?? ''}${label.slice(1)}: ${formatValue(field, change)}`)
    }
  }
  return {
    id: entry.id,
    when: formatInstant(entry.occurred_at),
    actor: actorLabel(entry.actor_type),
    isAgent: entry.actor_type === 'agent',
    summary: forActor(entry.actor_type, summary),
    details
  }
}
