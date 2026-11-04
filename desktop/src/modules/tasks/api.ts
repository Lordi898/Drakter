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

export function ifMatch(revision: number): Readonly<Record<string, string>> {
  return { 'If-Match': `"${revision}"` }
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
  return apiRequest<Task>(`${BASE}/${id}`, { method: 'PATCH', body: patch, headers: ifMatch(revision) })
}

export function completeTask(id: string, revision: number, completeSubtasks = false): Promise<Task> {
  return apiRequest<Task>(`${BASE}/${id}/complete`, {
    method: 'POST',
    body: { complete_subtasks: completeSubtasks },
    headers: ifMatch(revision)
  })
}

export function reopenTask(id: string, revision: number): Promise<Task> {
  return apiRequest<Task>(`${BASE}/${id}/reopen`, { method: 'POST', headers: ifMatch(revision) })
}

export function archiveTask(id: string, revision: number): Promise<Task> {
  return apiRequest<Task>(`${BASE}/${id}/archive`, { method: 'POST', headers: ifMatch(revision) })
}

export function unarchiveTask(id: string, revision: number): Promise<Task> {
  return apiRequest<Task>(`${BASE}/${id}/unarchive`, { method: 'POST', headers: ifMatch(revision) })
}

export function deleteTask(id: string, revision: number): Promise<void> {
  return apiRequest<void>(`${BASE}/${id}`, { method: 'DELETE', headers: ifMatch(revision) })
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
