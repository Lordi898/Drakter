/** Espejo de `backend/app/schemas/projects.py`. */
import type { Priority } from '../tasks/types'

export { PRIORITIES, PRIORITY_LABELS } from '../tasks/types'
export type { Priority }

export const PROJECT_STATUSES = ['planned', 'active', 'paused', 'completed', 'cancelled'] as const
export type ProjectStatus = (typeof PROJECT_STATUSES)[number]

export const PROJECT_STATUS_LABELS: Readonly<Record<ProjectStatus, string>> = {
  planned: 'Planificado',
  active: 'Activo',
  paused: 'En pausa',
  completed: 'Completado',
  cancelled: 'Cancelado'
}

export type ProgressSource = 'tasks' | 'manual'

export const MAX_NAME = 200
export const MAX_OBJECTIVE = 2_000
export const MAX_DESCRIPTION = 10_000

export interface ProjectProgress {
  readonly project_id: string
  readonly total: number
  readonly completed: number
  readonly open: number
  readonly cancelled: number
  readonly overdue: number
  /** Siempre calculado por el backend. */
  readonly percent: number
  readonly computed_percent: number
  readonly source: ProgressSource
}

export interface Project {
  readonly id: string
  readonly name: string
  readonly description: string | null
  readonly objective: string | null
  readonly status: ProjectStatus
  readonly priority: Priority
  /** Fechas sin hora (AAAA-MM-DD). */
  readonly start_date: string | null
  readonly target_date: string | null
  readonly completed_at: string | null
  readonly manual_progress: number | null
  readonly metadata: Readonly<Record<string, unknown>>
  readonly created_at: string
  readonly updated_at: string
  readonly archived_at: string | null
  readonly revision: number
  readonly progress: ProjectProgress
}

export interface ProjectCreate {
  readonly name: string
  readonly description?: string | null
  readonly objective?: string | null
  readonly status?: ProjectStatus
  readonly priority?: Priority
  readonly start_date?: string | null
  readonly target_date?: string | null
  readonly manual_progress?: number | null
  readonly metadata?: Readonly<Record<string, unknown>>
}

export type ProjectUpdate = Partial<ProjectCreate>

export type ArchivedFilter = 'exclude' | 'only' | 'include'

export const PROJECT_SORT_FIELDS = [
  'name',
  'created_at',
  'updated_at',
  'target_date',
  'priority',
  'status'
] as const

export interface ProjectListParams {
  readonly status?: readonly ProjectStatus[]
  readonly priority?: readonly Priority[]
  readonly q?: string
  readonly archived?: ArchivedFilter
  /** Campo de `PROJECT_SORT_FIELDS`; prefijo `-` para orden descendente. */
  readonly sort?: string
  readonly limit?: number
  readonly cursor?: string
}
