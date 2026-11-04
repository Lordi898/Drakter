import { api, ifMatch, toQuery } from './client'
import type {
  HistoryEntry,
  Page,
  Tag,
  Task,
  TaskCreate,
  TaskDetail,
  TaskListParams,
  TaskUpdate
} from './types'

/** Rutas REST de tareas. Las que cambian una tarea llevan `If-Match` con su revisión. */

export function listTasks(params: TaskListParams = {}): Promise<Page<Task>> {
  return api<Page<Task>>({ method: 'GET', path: `/tasks${toQuery({ ...params })}` })
}

export function getTask(id: string): Promise<TaskDetail> {
  return api<TaskDetail>({ method: 'GET', path: `/tasks/${id}` })
}

export function createTask(data: TaskCreate): Promise<Task> {
  return api<Task>({ method: 'POST', path: '/tasks', body: data })
}

export function updateTask(id: string, patch: TaskUpdate, revision: number): Promise<Task> {
  return api<Task>({ method: 'PATCH', path: `/tasks/${id}`, body: patch, headers: ifMatch(revision) })
}

export function completeTask(id: string, revision: number, completeSubtasks = false): Promise<Task> {
  return api<Task>({
    method: 'POST',
    path: `/tasks/${id}/complete`,
    body: { complete_subtasks: completeSubtasks },
    headers: ifMatch(revision)
  })
}

export function reopenTask(id: string, revision: number): Promise<Task> {
  return api<Task>({ method: 'POST', path: `/tasks/${id}/reopen`, headers: ifMatch(revision) })
}

export function archiveTask(id: string, revision: number): Promise<Task> {
  return api<Task>({ method: 'POST', path: `/tasks/${id}/archive`, headers: ifMatch(revision) })
}

export function unarchiveTask(id: string, revision: number): Promise<Task> {
  return api<Task>({ method: 'POST', path: `/tasks/${id}/unarchive`, headers: ifMatch(revision) })
}

export function deleteTask(id: string, revision: number): Promise<void> {
  return api<void>({ method: 'DELETE', path: `/tasks/${id}`, headers: ifMatch(revision) })
}

export function createSubtask(parentId: string, data: Omit<TaskCreate, 'parent_task_id'>): Promise<Task> {
  return api<Task>({ method: 'POST', path: `/tasks/${parentId}/subtasks`, body: data })
}

export function replaceTaskTags(id: string, names: readonly string[]): Promise<Task> {
  return api<Task>({ method: 'PUT', path: `/tasks/${id}/tags`, body: { names } })
}

export function listTaskTags(): Promise<readonly Tag[]> {
  return api<readonly Tag[]>({ method: 'GET', path: '/tasks/tags' })
}

export function addTaskDependency(id: string, dependsOnId: string): Promise<TaskDetail> {
  return api<TaskDetail>({
    method: 'POST',
    path: `/tasks/${id}/dependencies`,
    body: { depends_on_task_id: dependsOnId }
  })
}

export function removeTaskDependency(id: string, dependsOnId: string): Promise<TaskDetail> {
  return api<TaskDetail>({ method: 'DELETE', path: `/tasks/${id}/dependencies/${dependsOnId}` })
}

export function taskHistory(id: string, limit = 50, cursor?: string): Promise<Page<HistoryEntry>> {
  return api<Page<HistoryEntry>>({
    method: 'GET',
    path: `/tasks/${id}/history${toQuery({ limit, cursor })}`
  })
}
