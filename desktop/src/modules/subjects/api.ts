import { api, listAll, type Page } from '@/modules/calendar/workspaceApi'
import type {
  ClassSession,
  ExceptionInput,
  SessionInput,
  SessionWriteResult,
  Subject,
  SubjectInput,
  Timetable
} from './types'

/** DELETE no ejecuta: el backend responde 409 `confirmation_required` (ApiError con ticket). */
export type DeleteResult = undefined

export function listSubjects(includeArchived: boolean): Promise<Page<Subject>> {
  return listAll<Subject>('/subjects', { include_archived: includeArchived }).then((items) => ({
    items,
    next_cursor: null
  }))
}

export function createSubject(body: SubjectInput): Promise<Subject> {
  return api('POST', '/subjects', { body })
}

export function updateSubject(id: string, revision: number, body: SubjectInput): Promise<Subject> {
  return api('PATCH', `/subjects/${id}`, { body, revision })
}

export function archiveSubject(id: string): Promise<Subject> {
  return api('POST', `/subjects/${id}/archive`)
}

export function unarchiveSubject(id: string): Promise<Subject> {
  return api('POST', `/subjects/${id}/unarchive`)
}

export function deleteSubject(id: string): Promise<DeleteResult> {
  return api('DELETE', `/subjects/${id}`)
}

export function listSessions(subjectId: string): Promise<Page<ClassSession>> {
  return listAll<ClassSession>(`/subjects/${subjectId}/sessions`).then((items) => ({ items, next_cursor: null }))
}

export function createSession(subjectId: string, body: SessionInput): Promise<SessionWriteResult> {
  return api('POST', `/subjects/${subjectId}/sessions`, { body })
}

export function updateSession(id: string, revision: number, body: SessionInput): Promise<unknown> {
  return api('PATCH', `/class-sessions/${id}`, { body, revision })
}

export function deleteSession(id: string): Promise<DeleteResult> {
  return api('DELETE', `/class-sessions/${id}`)
}

export function createException(sessionId: string, body: ExceptionInput): Promise<unknown> {
  return api('POST', `/class-sessions/${sessionId}/exceptions`, { body })
}

export function getTimetable(on: string): Promise<Timetable> {
  return api('GET', '/timetable', { query: { on } })
}
