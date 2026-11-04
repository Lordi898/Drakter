import { api, ApiError, isConfirmationRequired, type ConfirmationRequired, type Page } from './workspaceClient'
import type {
  AgendaResponse,
  EventOut,
  EventPayload,
  EventWriteResult,
  OverlapGroup,
  TimeBlockOut,
  TimeBlockPayload,
  TimeBlockWriteResult
} from './types'

/** `to` es exclusivo. La agenda llega ya en la zona pedida. */
export function fetchAgenda(from: string, to: string, timezone: string): Promise<AgendaResponse> {
  return api<AgendaResponse>('GET', '/calendar/agenda', { query: { from, to, timezone } })
}

export async function fetchOverlaps(from: string, to: string, timezone: string): Promise<OverlapGroup[]> {
  const result = await api<readonly OverlapGroup[] | Page<OverlapGroup>>('GET', '/calendar/overlaps', {
    query: { from, to, timezone }
  })
  return [...(Array.isArray(result) ? result : (result as Page<OverlapGroup>).items)]
}

export const getEvent = (id: string): Promise<EventOut> => api<EventOut>('GET', `/calendar/events/${id}`)

export const createEvent = (body: EventPayload): Promise<EventWriteResult> =>
  api<EventWriteResult>('POST', '/calendar/events', { body })

export const updateEvent = (id: string, body: EventPayload, revision: number): Promise<EventWriteResult> =>
  api<EventWriteResult>('PATCH', `/calendar/events/${id}`, { body, revision })

export const getTimeBlock = (id: string): Promise<TimeBlockOut> => api<TimeBlockOut>('GET', `/calendar/time-blocks/${id}`)

export const createTimeBlock = (body: TimeBlockPayload): Promise<TimeBlockWriteResult> =>
  api<TimeBlockWriteResult>('POST', '/calendar/time-blocks', { body })

export const updateTimeBlock = (id: string, body: TimeBlockPayload, revision: number): Promise<TimeBlockWriteResult> =>
  api<TimeBlockWriteResult>('PATCH', `/calendar/time-blocks/${id}`, { body, revision })

async function requestDeletion(path: string): Promise<ConfirmationRequired> {
  const result = await api<unknown>('DELETE', path)
  if (!isConfirmationRequired(result)) {
    throw new ApiError(500, 'unexpected_response', 'El borrado no devolvió una confirmación.')
  }
  return result
}

/** Nunca borra: devuelve la confirmación que la GUI debe aprobar. */
export const requestEventDeletion = (id: string): Promise<ConfirmationRequired> => requestDeletion(`/calendar/events/${id}`)
export const requestTimeBlockDeletion = (id: string): Promise<ConfirmationRequired> =>
  requestDeletion(`/calendar/time-blocks/${id}`)

/** Cancela una sola ocurrencia (reversible, sin confirmación). */
export function cancelOccurrence(eventId: string, occurrenceLocalStart: string): Promise<unknown> {
  return api('POST', `/calendar/events/${eventId}/exceptions`, {
    body: { occurrence_local_start: occurrenceLocalStart, kind: 'cancelled' }
  })
}
