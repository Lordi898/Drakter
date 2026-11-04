import { api, ifMatch, toQuery } from '../tasks/client'
import type { HistoryEntry, Page } from '../tasks/types'
import type {
  Project,
  ProjectCreate,
  ProjectListParams,
  ProjectProgress,
  ProjectUpdate
} from './types'

/** Rutas REST de proyectos. Las que cambian un proyecto llevan `If-Match` con su revisión. */

export function listProjects(params: ProjectListParams = {}): Promise<Page<Project>> {
  return api<Page<Project>>({ method: 'GET', path: `/projects${toQuery({ ...params })}` })
}

export function getProject(id: string): Promise<Project> {
  return api<Project>({ method: 'GET', path: `/projects/${id}` })
}

export function createProject(data: ProjectCreate): Promise<Project> {
  return api<Project>({ method: 'POST', path: '/projects', body: data })
}

export function updateProject(id: string, patch: ProjectUpdate, revision: number): Promise<Project> {
  return api<Project>({
    method: 'PATCH',
    path: `/projects/${id}`,
    body: patch,
    headers: ifMatch(revision)
  })
}

export function archiveProject(id: string, revision: number): Promise<Project> {
  return api<Project>({ method: 'POST', path: `/projects/${id}/archive`, headers: ifMatch(revision) })
}

export function unarchiveProject(id: string, revision: number): Promise<Project> {
  return api<Project>({ method: 'POST', path: `/projects/${id}/unarchive`, headers: ifMatch(revision) })
}

/** Siempre pide confirmación: el cliente recibe `ConfirmationNeeded` y no se borra nada sin aprobarla. */
export function deleteProject(id: string, revision: number): Promise<void> {
  return api<void>({ method: 'DELETE', path: `/projects/${id}`, headers: ifMatch(revision) })
}

export function projectProgress(id: string): Promise<ProjectProgress> {
  return api<ProjectProgress>({ method: 'GET', path: `/projects/${id}/progress` })
}

export function projectActivity(id: string, limit = 30, cursor?: string): Promise<Page<HistoryEntry>> {
  return api<Page<HistoryEntry>>({
    method: 'GET',
    path: `/projects/${id}/activity${toQuery({ limit, cursor })}`
  })
}
