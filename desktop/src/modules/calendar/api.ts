import { api, ApiError, confirmationOf, type ConfirmationTicket } from './workspaceApi'
import type {
  AgendaResponse,
  EventOut,
  EventPayload,
  EventWriteResult,
  OverlapGroup,
  OverlapsResponse,
  TimeBlockOut,
  TimeBlockPayload,
  TimeBlockWriteResult
} from './types'

/** `to` es exclusivo. La agenda llega ya en la zona pedida. */
export function fetchAgenda(from: string, to: string, timezone: string): Promise<AgendaResponse> {
  return api<AgendaResponse>('GET', '/calendar/agenda', { query: { from, to, timezone } })
}

export async function fetchOverlaps(from: string, to: string, timezone: string): Promise<OverlapGroup[]> {
  const result = await api<OverlapsResponse>('GET', '/calendar/overlaps', { query: { from, to, timezone } })
  return [...result.items]
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

/** El backend responde 409 `confirmation_required`: se devuelve el ticket que hay que revisar. */
async function requestDeletion(path: string): Promise<ConfirmationTicket> {
  try {
    await api<unknown>('DELETE', path)
  } catch (error) {
    const ticket = confirmationOf(error)
    if (ticket) return ticket
    throw error
  }
  throw new ApiError(500, 'unexpected_response', 'El borrado no pidió confirmación.')
}

export const requestEventDeletion = (id: string): Promise<ConfirmationTicket> => requestDeletion(`/calendar/events/${id}`)
export const requestTimeBlockDeletion = (id: string): Promise<ConfirmationTicket> =>
  requestDeletion(`/calendar/time-blocks/${id}`)

/** Cancela una sola ocurrencia (reversible, sin confirmación). */
export function cancelOccurrence(eventId: string, occurrenceLocalStart: string): Promise<unknown> {
  return api('POST', `/calendar/events/${eventId}/exceptions`, {
    body: { occurrence_local_start: occurrenceLocalStart, kind: 'cancelled' }
  })
}
