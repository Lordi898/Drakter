import { clearBackendSession, loadBackendSession } from '@/services/session'
import {
  API_PATHS,
  isAgentState,
  isStoredChatMessage,
  type AgentStatusInfo,
  type ApiErrorDetail,
  type ChatSessionInfo,
  type SendMessageRequest,
  type SendMessageResponse,
  type StoredChatMessage
} from '@/services/protocol'

const TIMEOUT_MS = 15_000
const SAFE_CODE = /^[A-Za-z0-9_.-]{1,64}$/

const STATUS_MESSAGES: Readonly<Record<number, string>> = {
  400: 'La solicitud no es válida.',
  401: 'La sesión con el servicio local ha caducado. Drakter está reconectando.',
  403: 'No tienes permiso para esta acción.',
  404: 'No se encontró lo solicitado.',
  409: 'Esa acción ya no es posible en el estado actual.',
  413: 'El contenido es demasiado grande.',
  422: 'La solicitud no es válida.',
  429: 'Demasiadas solicitudes seguidas. Espera un momento.'
}

function messageFor(status: number): string {
  if (status === 0) return 'No se pudo contactar con el servicio local de Drakter.'
  const known = STATUS_MESSAGES[status]
  if (known) return known
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
 * Error de la API. `message` es SIEMPRE un texto propio en español, nunca el del
 * servidor (dato no confiable); `code`, `requestId` y `details` son para diagnóstico.
 */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly requestId: string | null
  readonly details: readonly ApiErrorDetail[]

  constructor(
    status: number,
    code: string,
    message: string,
    requestId: string | null = null,
    details: readonly ApiErrorDetail[] = []
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.requestId = requestId
    this.details = details
  }
}

/** Texto legible para el usuario a partir de cualquier error. */
export function describeError(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}

export interface ApiRequestInit {
  readonly method?: 'GET' | 'POST'
  readonly body?: unknown
}

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text()
  if (text.length === 0) return undefined
  try {
    return JSON.parse(text) as unknown
  } catch {
    return undefined
  }
}

function errorFromBody(status: number, body: unknown): ApiError {
  const envelope =
    typeof body === 'object' && body !== null ? (body as { error?: unknown }).error : undefined
  const fields =
    typeof envelope === 'object' && envelope !== null ? (envelope as Record<string, unknown>) : {}
  const requestId = typeof fields['request_id'] === 'string' ? safeCode(fields['request_id'], '') || null : null
  return new ApiError(
    status,
    safeCode(fields['code'], 'http_error'),
    messageFor(status),
    requestId,
    parseDetails(fields['details'])
  )
}

export async function apiRequest<T>(path: string, init: ApiRequestInit = {}): Promise<T> {
  // Solo rutas relativas al backend: una URL absoluta enviaría el token a otro origen.
  if (!path.startsWith('/') || path.startsWith('//') || path.includes('\\')) {
    throw new ApiError(0, 'invalid_path', 'La ruta de la solicitud no es válida.')
  }
  const session = await loadBackendSession()
  if (!session) throw new ApiError(0, 'no_session', 'Drakter no está conectado al servicio local.')

  const url = session.baseUrl + path
  if (new URL(url).origin !== new URL(session.baseUrl).origin) {
    throw new ApiError(0, 'invalid_path', 'La ruta de la solicitud no es válida.')
  }

  const headers: Record<string, string> = {
    Authorization: `Bearer ${session.token}`,
    Accept: 'application/json'
  }
  const hasBody = init.body !== undefined
  if (hasBody) headers['Content-Type'] = 'application/json'

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)
  let response: Response
  try {
    response = await fetch(url, {
      method: init.method ?? 'GET',
      headers,
      ...(hasBody ? { body: JSON.stringify(init.body) } : {}),
      signal: controller.signal,
      credentials: 'omit',
      cache: 'no-store',
      redirect: 'error'
    })
  } catch (error) {
    if (controller.signal.aborted) {
      throw new ApiError(0, 'timeout', 'El servicio local tardó demasiado en responder.')
    }
    void error
    throw new ApiError(0, 'network', messageFor(0))
  } finally {
    clearTimeout(timer)
  }

  if (response.status === 401) clearBackendSession()
  if (!response.ok) throw errorFromBody(response.status, await readJson(response).catch(() => undefined))

  const body = await readJson(response)
  return body as T
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {}
}

function badResponse(): ApiError {
  return new ApiError(502, 'bad_response', 'La respuesta del servicio local no es válida.')
}

export async function createChatSession(): Promise<ChatSessionInfo> {
  const body = asRecord(await apiRequest<unknown>(API_PATHS.chatSessions, { method: 'POST', body: {} }))
  if (typeof body['id'] !== 'string') throw badResponse()
  return { id: body['id'] }
}

export async function sendChatMessage(
  sessionId: string,
  request: SendMessageRequest
): Promise<SendMessageResponse> {
  const body = asRecord(
    await apiRequest<unknown>(API_PATHS.sessionMessages(sessionId), { method: 'POST', body: request })
  )
  if (typeof body['turn_id'] !== 'string' || typeof body['message_id'] !== 'string') throw badResponse()
  return { turn_id: body['turn_id'], message_id: body['message_id'] }
}

export async function cancelTurn(turnId: string): Promise<void> {
  await apiRequest<unknown>(API_PATHS.cancelTurn(turnId), { method: 'POST' })
}

export async function listSessionMessages(sessionId: string): Promise<readonly StoredChatMessage[]> {
  const body = asRecord(await apiRequest<unknown>(API_PATHS.sessionMessages(sessionId)))
  const items = body['items']
  if (!Array.isArray(items)) throw badResponse()
  return items.filter(isStoredChatMessage)
}

export async function getAgentStatus(): Promise<AgentStatusInfo> {
  const body = asRecord(await apiRequest<unknown>(API_PATHS.agentStatus))
  if (!isAgentState(body['state'])) throw badResponse()
  const text = (value: unknown): string => (typeof value === 'string' ? value.slice(0, 200) : '')
  return {
    state: body['state'],
    provider: text(body['provider']),
    model: text(body['model']),
    detail: typeof body['detail'] === 'string' ? body['detail'].slice(0, 200) : null
  }
}
