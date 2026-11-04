import { apiRequest } from '@/services/api'
import type { HistoryEntry } from '../tasks/types'
import type {
  ListPage,
  Project,
  ProjectCreate,
  ProjectListParams,
  ProjectProgress,
  ProjectUpdate
} from './types'

/** Rutas REST de proyectos. Las que cambian un proyecto llevan `If-Match` con su revisión. */

const BASE = '/api/v1/projects'

function ifMatch(revision: number): Readonly<Record<string, string>> {
  return { 'If-Match': `"${revision}"` }
}

function toQuery(params: Readonly<Record<string, unknown>>): string {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '' || value === false) continue
    if (Array.isArray(value)) {
      for (const item of value) query.append(key, String(item))
    } else {
      query.set(key, String(value))
    }
  }
  const text = query.toString()
  return text === '' ? '' : `?${text}`
}

export function listProjects(params: ProjectListParams = {}): Promise<ListPage<Project>> {
  return apiRequest<ListPage<Project>>(`${BASE}${toQuery({ ...params })}`)
}

export function getProject(id: string): Promise<Project> {
  return apiRequest<Project>(`${BASE}/${id}`)
}

export function createProject(data: ProjectCreate): Promise<Project> {
  return apiRequest<Project>(BASE, { method: 'POST', body: data })
}

export function updateProject(id: string, patch: ProjectUpdate, revision: number): Promise<Project> {
  return apiRequest<Project>(`${BASE}/${id}`, { method: 'PATCH', body: patch, headers: ifMatch(revision) })
}

export function archiveProject(id: string, revision: number): Promise<Project> {
  return apiRequest<Project>(`${BASE}/${id}/archive`, { method: 'POST', headers: ifMatch(revision) })
}

export function unarchiveProject(id: string, revision: number): Promise<Project> {
  return apiRequest<Project>(`${BASE}/${id}/unarchive`, { method: 'POST', headers: ifMatch(revision) })
}

/** Siempre pide confirmación: el error trae `confirmation` y no se borra nada sin aprobarla. */
export function deleteProject(id: string, revision: number): Promise<void> {
  return apiRequest<void>(`${BASE}/${id}`, { method: 'DELETE', headers: ifMatch(revision) })
}

export function projectProgress(id: string): Promise<ProjectProgress> {
  return apiRequest<ProjectProgress>(`${BASE}/${id}/progress`)
}

export function projectActivity(id: string, limit = 30, offset = 0): Promise<ListPage<HistoryEntry>> {
  return apiRequest<ListPage<HistoryEntry>>(`${BASE}/${id}/activity${toQuery({ limit, offset })}`)
}
