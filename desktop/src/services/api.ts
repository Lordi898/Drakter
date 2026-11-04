import type { ApiCallResult, DrakterApi } from '../../electron/shared/bridge'
import {
  isAgentState,
  isConfirmationTicket,
  isStoredChatMessage,
  type AgentStatusInfo,
  type ApiErrorDetail,
  type ChatSessionInfo,
  type ConfirmationTicket,
  type PendingConfirmation,
  type SendMessageRequest,
  type SendMessageResponse,
  type StoredChatMessage
} from '@/services/protocol'

/**
 * Cliente único del backend para el renderer. Todo pasa por `window.api` (D-14):
 * aquí no hay red, token ni puerto. La respuesta es dato no confiable.
 */
const SAFE_CODE = /^[A-Za-z0-9_.-]{1,64}$/

const CODE_MESSAGES: Readonly<Record<string, string>> = {
  backend_unavailable: 'El servicio local de Drakter no está disponible.',
  timeout: 'El servicio local tardó demasiado en responder.',
  invalid_request: 'La solicitud no es válida.',
  response_too_large: 'La respuesta del servicio local es demasiado grande.',
  confirmation_required: 'Esta acción necesita tu confirmación antes de ejecutarse.',
  confirmation_expired: 'La confirmación ha caducado. No se ha ejecutado nada.',
  confirmation_unavailable: 'No se puede confirmar ahora mismo. No se ha ejecutado nada.',
  confirmation_already_resolved: 'Esa confirmación ya se había resuelto.',
  agent_busy: 'Drakter sigue respondiendo. Espera a que termine o cancela el turno.',
  agent_unavailable: 'El agente no está disponible en este momento.',
  agent_timeout: 'El agente tardó demasiado en responder.',
  agent_disconnected: 'Se perdió la conexión con el agente.',
  provider_auth: 'El proveedor del modelo rechazó las credenciales.',
  provider_error: 'El proveedor del modelo ha fallado.',
  no_active_turn: 'No hay ninguna respuesta en curso.',
  rate_limited: 'Demasiadas solicitudes seguidas. Espera un momento.',
  not_found: 'No se encontró lo solicitado.',
  validation_error: 'La solicitud no es válida.',
  path_not_allowed: 'Esa ruta no está permitida.',
  file_too_large: 'El archivo es demasiado grande.',
  permission_denied: 'No tienes permiso para esta acción.'
}

const STATUS_MESSAGES: Readonly<Record<number, string>> = {
  400: 'La solicitud no es válida.',
  401: 'La sesión con el servicio local ha caducado.',
  403: 'No tienes permiso para esta acción.',
  404: 'No se encontró lo solicitado.',
  409: 'Esa acción ya no es posible en el estado actual.',
  410: 'Esto ya no está disponible.',
  412: 'Los datos han cambiado; vuelve a cargarlos.',
  413: 'El contenido es demasiado grande.',
  422: 'La solicitud no es válida.',
  429: 'Demasiadas solicitudes seguidas. Espera un momento.',
  503: 'El servicio no está disponible en este momento.'
}

function messageFor(status: number, code: string): string {
  const byCode = CODE_MESSAGES[code]
  if (byCode) return byCode
  if (status === 0) return 'No se pudo contactar con el servicio local de Drakter.'
  const byStatus = STATUS_MESSAGES[status]
  if (byStatus) return byStatus
  if (status >= 500) return 'El servicio local de Drakter ha fallado. Inténtalo de nuevo.'
  return 'No se pudo completar la solicitud.'
}

function safeCode(value: unknown, fallback: string): string {
  return typeof value === 'string' && SAFE_CODE.test(value) ? value : fallback
}

function parseDetails(value: unknown): readonly ApiErrorDetail[] {
  if (!Array.isArray(value)) return []
  const out: ApiErrorDetail[] = []
  for (const item of value.slice(0, 20)) {
    if (typeof item !== 'object' || item === null) continue
    const { field, code, message } = item as Record<string, unknown>
    if (typeof code !== 'string' || typeof message !== 'string') continue
    out.push({
      field: typeof field === 'string' ? field.slice(0, 100) : null,
      code: safeCode(code, 'unknown'),
      message: message.slice(0, 200)
    })
  }
  return out
}

/**
 * Error de la API. `message` es SIEMPRE un texto propio en español decidido por
 * `code`, nunca el del servidor. `confirmation` solo se rellena en un 409
 * `confirmation_required` con ticket válido.
 */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly requestId: string | null
  readonly details: readonly ApiErrorDetail[]
  readonly confirmation: ConfirmationTicket | null

  constructor(
    status: number,
    code: string,
    message: string,
    requestId: string | null = null,
    details: readonly ApiErrorDetail[] = [],
    confirmation: ConfirmationTicket | null = null
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.requestId = requestId
    this.details = details
    this.confirmation = confirmation
  }
}

export type { ConfirmationTicket }

/** Texto legible para el usuario a partir de cualquier error. */
export function describeError(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}

const confirmationListeners = new Set<(ticket: ConfirmationTicket) => void>()

/** Avisa de cada 409 `confirmation_required` recibido por cualquier módulo. */
export function subscribeConfirmationRequired(listener: (ticket: ConfirmationTicket) => void): () => void {
  confirmationListeners.add(listener)
  return () => {
    confirmationListeners.delete(listener)
  }
}

export interface ApiRequestInit {
  readonly method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  readonly body?: unknown
}

function getApi(): DrakterApi | null {
  return typeof window !== 'undefined' && typeof window.api !== 'undefined' ? window.api : null
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}

function errorFromFailure(result: Extract<ApiCallResult, { ok: false }>): ApiError {
  if (result.status === 0) {
    const code = safeCode(result.code, 'backend_unavailable')
    return new ApiError(0, code, messageFor(0, code))
  }
  const envelope = asRecord(asRecord(result.body)['error'])
  const code = safeCode(envelope['code'], 'http_error')
  const requestId = typeof envelope['request_id'] === 'string' ? safeCode(envelope['request_id'], '') || null : null

  // DECISIÓN 2: se comprueba ANTES de cualquier texto de "ya no es posible".
  if (result.status === 409 && code === 'confirmation_required') {
    const ticket = asRecord(result.body)['confirmation']
    if (isConfirmationTicket(ticket)) {
      const error = new ApiError(409, code, messageFor(409, code), requestId, parseDetails(envelope['details']), ticket)
      for (const listener of [...confirmationListeners]) {
        try {
          listener(ticket)
        } catch {
          console.warn('Un oyente de confirmaciones falló.')
        }
      }
      return error
    }
  }
  return new ApiError(result.status, code, messageFor(result.status, code), requestId, parseDetails(envelope['details']))
}

export async function apiRequest<T>(path: string, init: ApiRequestInit = {}): Promise<T> {
  if (!path.startsWith('/') || path.startsWith('//') || path.includes('\\') || path.includes('://')) {
    throw new ApiError(0, 'invalid_request', CODE_MESSAGES['invalid_request'] ?? 'La solicitud no es válida.')
  }
  const api = getApi()
  if (!api) throw new ApiError(0, 'backend_unavailable', messageFor(0, 'backend_unavailable'))

  let result: ApiCallResult
  try {
    result = await api.call(init.method ?? 'GET', path, init.body)
  } catch {
    throw new ApiError(0, 'backend_unavailable', messageFor(0, 'backend_unavailable'))
  }
  if (typeof result !== 'object' || result === null) {
    throw new ApiError(502, 'bad_response', 'La respuesta del servicio local no es válida.')
  }
  if (result.ok === true && result.status >= 200 && result.status < 300) return result.data as T
  if (result.ok === true) throw new ApiError(result.status, 'http_error', messageFor(result.status, 'http_error'))
  throw errorFromFailure(result)
}

function badResponse(): ApiError {
  return new ApiError(502, 'bad_response', 'La respuesta del servicio local no es válida.')
}

export async function createChatSession(): Promise<ChatSessionInfo> {
  const body = asRecord(await apiRequest<unknown>('/api/v1/chat/sessions', { method: 'POST', body: {} }))
  if (typeof body['id'] !== 'string') throw badResponse()
  return { id: body['id'] }
}

export async function sendChatMessage(
  sessionId: string,
  request: SendMessageRequest
): Promise<SendMessageResponse> {
  const body = asRecord(
    await apiRequest<unknown>(`/api/v1/chat/sessions/${encodeURIComponent(sessionId)}/messages`, {
      method: 'POST',
      body: request
    })
  )
  if (typeof body['turn_id'] !== 'string' || typeof body['message_id'] !== 'string') throw badResponse()
  return { turn_id: body['turn_id'], message_id: body['message_id'] }
}

export async function cancelTurn(turnId: string): Promise<void> {
  await apiRequest<unknown>(`/api/v1/chat/turns/${encodeURIComponent(turnId)}/cancel`, { method: 'POST' })
}

export async function listSessionMessages(sessionId: string): Promise<readonly StoredChatMessage[]> {
  const body = asRecord(
    await apiRequest<unknown>(`/api/v1/chat/sessions/${encodeURIComponent(sessionId)}/messages`)
  )
  if (!Array.isArray(body['items'])) throw badResponse()
  return body['items'].filter(isStoredChatMessage)
}

export async function getAgentStatus(): Promise<AgentStatusInfo> {
  const body = asRecord(await apiRequest<unknown>('/api/v1/agent/status'))
  if (!isAgentState(body['state'])) throw badResponse()
  const text = (value: unknown): string => (typeof value === 'string' ? value.slice(0, 200) : '')
  return {
    state: body['state'],
    provider: text(body['provider']),
    model: text(body['model']),
    detail: typeof body['detail'] === 'string' ? body['detail'].slice(0, 200) : null
  }
}

/** `GET /api/v1/confirmations?status=pending`. SUPUESTO: elementos con `id` o `action_id`. */
export async function listPendingConfirmations(): Promise<readonly PendingConfirmation[]> {
  const body = asRecord(await apiRequest<unknown>('/api/v1/confirmations?status=pending'))
  if (!Array.isArray(body['items'])) throw badResponse()
  const out: PendingConfirmation[] = []
  for (const raw of body['items']) {
    const item = asRecord(raw)
    const id = typeof item['action_id'] === 'string' ? item['action_id'] : item['id']
    const count = item['affected_count']
    if (
      typeof id !== 'string' ||
      typeof item['summary'] !== 'string' ||
      typeof item['expires_at'] !== 'string' ||
      Number.isNaN(Date.parse(item['expires_at'])) ||
      !(count === undefined || count === null || (Number.isSafeInteger(count) && (count as number) >= 0))
    ) {
      continue
    }
    out.push({
      action_id: id,
      ...(typeof item['tool'] === 'string' ? { tool: item['tool'] } : {}),
      summary: item['summary'],
      affected_count: count === undefined ? null : (count as number | null),
      expires_at: item['expires_at']
    })
  }
  return out
}
