/**
 * Llamadas de main al backend para el modo flotante (CONTRACT §7 y §11.3), con el token `ui`.
 * No pasan por `operations.ts`: el renderer no puede pedirlas.
 */
import { randomUUID } from 'node:crypto'
import { BackendRequestError, parseReplyBody, requestBackend, type HttpReply } from '../apiProxy'
import type { BackendHost } from '../host-types'
import { describeError, logError } from '../log'

const SCOPE = 'floating:backend'
const TIMEOUT_MS = 5000
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

type Method = 'GET' | 'POST'

/** `null` si el backend no está listo o no respondió. Nunca rechaza. */
async function send(host: BackendHost, method: Method, path: string, body?: unknown): Promise<HttpReply | null> {
  const endpoint = host.getEndpoint()
  if (endpoint === null) return null
  try {
    return await requestBackend(endpoint, endpoint.uiToken, method, path, body, TIMEOUT_MS)
  } catch (error) {
    const detail = error instanceof BackendRequestError ? error.code : describeError(error)
    logError(SCOPE, `${method} ${path} fallido`, detail)
    return null
  }
}

const ok = (reply: HttpReply | null): boolean => reply !== null && reply.status >= 200 && reply.status < 300

export interface PresenceBody {
  readonly active: boolean
  readonly ready: boolean
  readonly companion: string
  readonly bridge_version: 1
  readonly monitor?: {
    readonly index: number
    readonly geometry: { x: number; y: number; w: number; h: number }
    readonly workarea: { x: number; y: number; w: number; h: number }
    readonly scale: number
    readonly primary: boolean
  } | null
}

let presenceMissingLogged = false

export async function postPresence(host: BackendHost, body: PresenceBody): Promise<void> {
  const reply = await send(host, 'POST', '/api/v1/overlay/presence', body)
  if (reply !== null && reply.status === 404 && !presenceMissingLogged) {
    presenceMissingLogged = true
    logError(SCOPE, 'El backend aún no tiene /api/v1/overlay/presence (404)')
  }
}

/** Lo que la página manda al cerebro (§11.3). 404 = guía terminada: se ignora. */
export async function postOverlayEvent(host: BackendHost, event: Readonly<Record<string, unknown>>): Promise<void> {
  const reply = await send(host, 'POST', '/api/v1/overlay/events', event)
  if (reply === null || ok(reply) || reply.status === 404) return
  logError(SCOPE, `overlay/events ${String(event['type'])} → ${reply.status}`)
}

export async function cancelTurn(host: BackendHost, turnId: string): Promise<void> {
  if (!UUID.test(turnId)) return
  await send(host, 'POST', `/api/v1/chat/turns/${turnId.toLowerCase()}/cancel`)
}

/** Ajustes del avatar flotante (`floating_avatar_size`, `floating_sound`); por defecto `default` y `true`. */
export async function readFloatingSettings(host: BackendHost): Promise<{ size: string; sound: boolean }> {
  const fallback = { size: 'default', sound: true }
  const reply = await send(host, 'GET', '/api/v1/settings')
  if (!ok(reply) || reply === null) return fallback
  const body = parseReplyBody(reply.text)
  const items = typeof body === 'object' && body !== null && Array.isArray((body as { items?: unknown }).items)
    ? ((body as { items: unknown[] }).items)
    : []
  const value = (key: string): unknown => {
    const item = items.find((i) => typeof i === 'object' && i !== null && (i as { key?: unknown }).key === key)
    return item ? (item as { value?: unknown }).value : undefined
  }
  const size = value('floating_avatar_size')
  const sound = value('floating_sound')
  return {
    size: size === 'small' || size === 'cursor' || size === 'default' ? size : fallback.size,
    sound: sound === false || sound === 'false' ? false : fallback.sound
  }
}

async function createSession(host: BackendHost): Promise<string | null> {
  const reply = await send(host, 'POST', '/api/v1/chat/sessions', {})
  if (!ok(reply) || reply === null) return null
  const body = parseReplyBody(reply.text)
  const id = typeof body === 'object' && body !== null ? (body as { id?: unknown }).id : undefined
  return typeof id === 'string' && UUID.test(id) ? id.toLowerCase() : null
}

export type SendMessageResult = { ok: true; sessionId: string } | { ok: false; code: 'busy' | 'failed' }

/** Mensaje escrito en la barra de pregunta → chat (sesión activa o una nueva). */
export async function sendChatMessage(host: BackendHost, sessionId: string | null, text: string): Promise<SendMessageResult> {
  const post = (id: string): Promise<HttpReply | null> =>
    send(host, 'POST', `/api/v1/chat/sessions/${id}/messages`, {
      text,
      client_message_id: randomUUID(),
      input_source: 'text'
    })
  let id = sessionId && UUID.test(sessionId) ? sessionId.toLowerCase() : await createSession(host)
  if (id === null) return { ok: false, code: 'failed' }
  let reply = await post(id)
  if (reply !== null && reply.status === 409 && reply.text.includes('agent_busy')) return { ok: false, code: 'busy' }
  // Sesión cerrada o desconocida: una nueva, una sola vez.
  if (!ok(reply) && sessionId !== null) {
    id = await createSession(host)
    if (id === null) return { ok: false, code: 'failed' }
    reply = await post(id)
  }
  return ok(reply) ? { ok: true, sessionId: id } : { ok: false, code: 'failed' }
}
