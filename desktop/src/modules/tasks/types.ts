/** Espejo de `backend/app/schemas/tasks.py`. */
export const TASK_STATUSES = ['pending', 'in_progress', 'on_hold', 'completed', 'cancelled'] as const
export type TaskStatus = (typeof TASK_STATUSES)[number]
export type EditableTaskStatus = Exclude<TaskStatus, 'completed'>

export const PRIORITIES = ['low', 'medium', 'high', 'urgent'] as const
export type Priority = (typeof PRIORITIES)[number]

export const TASK_STATUS_LABELS: Readonly<Record<TaskStatus, string>> = {
  pending: 'Pendiente',
  in_progress: 'En progreso',
  on_hold: 'En espera',
  completed: 'Completada',
  cancelled: 'Cancelada'
}

export const PRIORITY_LABELS: Readonly<Record<Priority, string>> = {
  low: 'Baja',
  medium: 'Media',
  high: 'Alta',
  urgent: 'Urgente'
}

export interface Tag {
  readonly id: string
  readonly name: string
  readonly color: string | null
}

export interface TaskRef {
  readonly id: string
  readonly title: string
  readonly status: TaskStatus
}

export interface Task {
  readonly id: string
  readonly title: string
  readonly description: string | null
  readonly status: TaskStatus
  readonly priority: Priority
  readonly start_at: string | null
  readonly due_at: string | null
  readonly due_date: string | null
  readonly completed_at: string | null
  readonly estimated_minutes: number | null
  readonly parent_task_id: string | null
  readonly project_id: string | null
  readonly subject_id: string | null
  readonly position: number
  readonly tags: readonly Tag[]
  readonly metadata: Readonly<Record<string, unknown>>
  readonly created_at: string
  readonly updated_at: string
  readonly archived_at: string | null
  readonly revision: number
  readonly depth: number
  readonly subtask_count: number
  readonly completed_subtask_count: number
  readonly blocked: boolean
}

export interface TaskNode extends Task {
  readonly children: readonly TaskNode[]
}

export interface TaskDetail extends Task {
  readonly subtasks: readonly TaskNode[]
  readonly dependencies: readonly TaskRef[]
  readonly dependents: readonly TaskRef[]
}

export interface TaskCreate {
  readonly title: string
  readonly description?: string | null
  readonly status?: EditableTaskStatus
  readonly priority?: Priority
  readonly start_at?: string | null
  readonly due_at?: string | null
  readonly due_date?: string | null
  readonly estimated_minutes?: number | null
  readonly parent_task_id?: string | null
  readonly project_id?: string | null
  readonly subject_id?: string | null
  readonly position?: number | null
  readonly tags?: readonly string[]
}

export type TaskUpdate = Partial<Omit<TaskCreate, 'title'>> & { readonly title?: string }

export interface TaskListParams {
  readonly status?: readonly TaskStatus[]
  readonly priority?: readonly Priority[]
  readonly project_id?: string
  readonly no_project?: boolean
  readonly subject_id?: string
  readonly parent_task_id?: string
  readonly root_only?: boolean
  readonly tag?: string
  readonly due_before?: string
  readonly due_after?: string
  readonly q?: string
  readonly archived?: 'exclude' | 'only' | 'include'
  readonly sort?: string
  readonly limit?: number
  readonly cursor?: string
}

export interface HistoryEntry {
  readonly id: string
  readonly occurred_at: string
  readonly actor_type: 'user' | 'agent' | 'automation' | 'system'
  readonly origin: 'rest' | 'mcp' | 'scheduler' | 'internal'
  readonly action: string
  readonly tool_name: string | null
  readonly entity_type: string | null
  readonly entity_id: string | null
  readonly result: 'success' | 'denied' | 'failed' | 'confirmation_required'
  readonly error_code: string | null
  readonly changes: Readonly<Record<string, unknown>> | null
}
