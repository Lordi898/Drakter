import { apiRequest } from '@/services/api'
import type { HistoryEntry, Tag, Task, TaskCreate, TaskDetail, TaskListParams as BaseListParams, TaskUpdate } from './types'

/** Listados del contrato v1: `total` cuenta todo lo que cumple el filtro. */
export interface Page<T> {
  readonly items: readonly T[]
  readonly total: number
}

export type TaskListParams = Omit<BaseListParams, 'archived' | 'cursor'> & {
  readonly include_archived?: boolean
  readonly offset?: number
}

const BASE = '/api/v1/tasks'

/** La GUI no puede enviar cabeceras: la revisión esperada va como `?revision=N`. */
export function withRevision(path: string, revision: number): string {
  return `${path}${path.includes('?') ? '&' : '?'}revision=${revision}`
}

function toQuery(params: Readonly<Record<string, unknown>>): string {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '' || value === false) continue
    if (Array.isArray(value)) for (const item of value) query.append(key, String(item))
    else query.set(key, String(value))
  }
  const text = query.toString()
  return text === '' ? '' : `?${text}`
}

export function listTasks(params: TaskListParams = {}): Promise<Page<Task>> {
  return apiRequest<Page<Task>>(`${BASE}${toQuery({ ...params })}`)
}

export function getTask(id: string): Promise<TaskDetail> {
  return apiRequest<TaskDetail>(`${BASE}/${id}`)
}

export function createTask(data: TaskCreate): Promise<Task> {
  return apiRequest<Task>(BASE, { method: 'POST', body: data })
}

export function updateTask(id: string, patch: TaskUpdate, revision: number): Promise<Task> {
  return apiRequest<Task>(withRevision(`${BASE}/${id}`, revision), { method: 'PATCH', body: patch })
}

export function completeTask(id: string, revision: number, completeSubtasks = false): Promise<Task> {
  return apiRequest<Task>(withRevision(`${BASE}/${id}/complete`, revision), {
    method: 'POST',
    body: { complete_subtasks: completeSubtasks }
  })
}

export function reopenTask(id: string, revision: number): Promise<Task> {
  return apiRequest<Task>(withRevision(`${BASE}/${id}/reopen`, revision), { method: 'POST' })
}

export function archiveTask(id: string, revision: number): Promise<Task> {
  return apiRequest<Task>(withRevision(`${BASE}/${id}/archive`, revision), { method: 'POST' })
}

export function unarchiveTask(id: string, revision: number): Promise<Task> {
  return apiRequest<Task>(withRevision(`${BASE}/${id}/unarchive`, revision), { method: 'POST' })
}

export function deleteTask(id: string, revision: number): Promise<void> {
  return apiRequest<void>(withRevision(`${BASE}/${id}`, revision), { method: 'DELETE' })
}

export function createSubtask(parentId: string, data: Omit<TaskCreate, 'parent_task_id'>): Promise<Task> {
  return apiRequest<Task>(`${BASE}/${parentId}/subtasks`, { method: 'POST', body: data })
}

export function replaceTaskTags(id: string, names: readonly string[]): Promise<Task> {
  return apiRequest<Task>(`${BASE}/${id}/tags`, { method: 'PUT', body: { names } })
}

export function listTaskTags(): Promise<readonly Tag[]> {
  return apiRequest<readonly Tag[]>(`${BASE}/tags`)
}

export function addTaskDependency(id: string, dependsOnId: string): Promise<TaskDetail> {
  return apiRequest<TaskDetail>(`${BASE}/${id}/dependencies`, {
    method: 'POST',
    body: { depends_on_task_id: dependsOnId }
  })
}

export function removeTaskDependency(id: string, dependsOnId: string): Promise<TaskDetail> {
  return apiRequest<TaskDetail>(`${BASE}/${id}/dependencies/${dependsOnId}`, { method: 'DELETE' })
}

export function taskHistory(id: string, limit = 50, offset = 0): Promise<Page<HistoryEntry>> {
  return apiRequest<Page<HistoryEntry>>(`${BASE}/${id}/history${toQuery({ limit, offset })}`)
}
