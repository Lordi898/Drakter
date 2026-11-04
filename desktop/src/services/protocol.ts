/**
 * Protocolo renderer ↔ backend: ÚNICO archivo que conoce rutas y formas de red.
 *
 * PROVISIONAL: al escribirlo `contracts/` no existía en `drakter/contratos`.
 * Sale de ROADMAP §5.3-5.4, backend/CONTRACT.md y el pipeline de confirmaciones
 * del dossier (C-06, BL-09, H-13). Cuando se congele el contrato, se ajusta aquí.
 *
 * Todo lo que llega por red es dato no confiable: se valida aquí y se muestra
 * siempre como texto plano, nunca como HTML ni como instrucción.
 */

export const WS_SUBPROTOCOL = 'drakter.v1'
export const WS_AUTH_PREFIX = 'drakter.auth.'
export const WS_PATH = '/ws'
export const EVENT_VERSION = 1

export const API_PATHS = {
  authCheck: '/api/v1/auth/check',
  chatMessages: '/api/v1/chat/messages',
  cancelTurn: (turnId: string) => `/api/v1/chat/turns/${encodeURIComponent(turnId)}/cancel`,
  pendingConfirmations: '/api/v1/confirmations?status=pending',
  approveConfirmation: (id: string) => `/api/v1/confirmations/${encodeURIComponent(id)}/approve`,
  rejectConfirmation: (id: string) => `/api/v1/confirmations/${encodeURIComponent(id)}/reject`
} as const

export const AGENT_STATUSES = [
  'idle',
  'listening',
  'thinking',
  'speaking',
  'executing',
  'success',
  'error',
  'interrupted'
] as const
export type AgentStatus = (typeof AGENT_STATUSES)[number]

// ---- REST ------------------------------------------------------------------

export interface SendMessageRequest {
  readonly session_id: string | null
  readonly client_message_id: string
  readonly content: string
}

/** 202: la respuesta llega por WebSocket. */
export interface SendMessageResponse {
  readonly session_id: string
  readonly turn_id: string
}

/** `summary` y `affected_count` los calcula el backend, nunca el modelo. */
export interface PendingConfirmation {
  readonly id: string
  readonly tool_name: string
  readonly summary: string
  readonly affected_count: number
  readonly risk: 'destructive' | 'bulk' | 'sensitive'
  readonly expires_at: string
}

export type ConfirmationDecision = 'approved' | 'rejected'

export interface ApiErrorDetail {
  readonly field: string | null
  readonly code: string
  readonly message: string
}

// ---- Eventos WebSocket ------------------------------------------------------

export interface EventPayloads {
  'agent.status_changed': { readonly status: AgentStatus }
  'agent.expression_changed': { readonly expression: string }
  'agent.message_delta': {
    readonly session_id: string
    readonly turn_id: string
    readonly message_id: string
    readonly seq: number
    readonly delta: string
  }
  'agent.message_completed': {
    readonly session_id: string
    readonly turn_id: string
    readonly message_id: string
    readonly content: string
  }
  'agent.tool_started': {
    readonly turn_id: string
    readonly tool_call_id: string
    readonly tool_name: string
  }
  'agent.tool_completed': {
    readonly turn_id: string
    readonly tool_call_id: string
    readonly tool_name: string
    readonly ok: boolean
  }
  'agent.error': {
    readonly turn_id: string | null
    readonly code: string
    readonly message: string
    readonly recoverable: boolean
  }
  'confirmation.requested': { readonly confirmation: PendingConfirmation }
  'confirmation.resolved': {
    readonly id: string
    readonly status: 'approved' | 'rejected' | 'expired' | 'executed' | 'failed'
  }
}

export type EventType = keyof EventPayloads

export interface EventEnvelope<T extends EventType = EventType> {
  readonly event_id: string
  readonly timestamp: string
  readonly type: T
  readonly version: number
  readonly payload: EventPayloads[T]
}

/** Unión discriminada: `switch (event.type)` estrecha `payload`. */
export type ServerEvent = { readonly [T in EventType]: EventEnvelope<T> }[EventType]

// ---- Validación --------------------------------------------------------------

type Json = Readonly<Record<string, unknown>>

function isRecord(value: unknown): value is Json {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

const isString = (value: unknown): value is string => typeof value === 'string'
const isStringOrNull = (value: unknown): value is string | null => value === null || isString(value)
const isCount = (value: unknown): value is number => Number.isSafeInteger(value) && (value as number) >= 0
const isBoolean = (value: unknown): value is boolean => typeof value === 'boolean'

function has(payload: Json, fields: Readonly<Record<string, (value: unknown) => boolean>>): boolean {
  return Object.entries(fields).every(([name, check]) => check(payload[name]))
}

export function isPendingConfirmation(value: unknown): value is PendingConfirmation {
  return (
    isRecord(value) &&
    has(value, {
      id: isString,
      tool_name: isString,
      summary: isString,
      affected_count: isCount,
      expires_at: (v) => isString(v) && !Number.isNaN(Date.parse(v)),
      risk: (v) => v === 'destructive' || v === 'bulk' || v === 'sensitive'
    })
  )
}

const TURN_MESSAGE = { session_id: isString, turn_id: isString, message_id: isString }
const TOOL_CALL = { turn_id: isString, tool_call_id: isString, tool_name: isString }
const RESOLVED = new Set(['approved', 'rejected', 'expired', 'executed', 'failed'])

const PAYLOAD_CHECKS: { readonly [T in EventType]: (payload: Json) => boolean } = {
  'agent.status_changed': (p) => (AGENT_STATUSES as readonly unknown[]).includes(p['status']),
  'agent.expression_changed': (p) => has(p, { expression: isString }),
  'agent.message_delta': (p) => has(p, { ...TURN_MESSAGE, seq: isCount, delta: isString }),
  'agent.message_completed': (p) => has(p, { ...TURN_MESSAGE, content: isString }),
  'agent.tool_started': (p) => has(p, TOOL_CALL),
  'agent.tool_completed': (p) => has(p, { ...TOOL_CALL, ok: isBoolean }),
  'agent.error': (p) =>
    has(p, { turn_id: isStringOrNull, code: isString, message: isString, recoverable: isBoolean }),
  'confirmation.requested': (p) => isPendingConfirmation(p['confirmation']),
  'confirmation.resolved': (p) => has(p, { id: isString, status: (v) => RESOLVED.has(v as string) })
}

/** Devuelve el evento validado, o `null` si es desconocido, de otra versión o malformado. */
export function parseServerEvent(raw: unknown): ServerEvent | null {
  if (!isRecord(raw)) return null
  const { event_id, timestamp, type, version, payload } = raw
  if (!isString(event_id) || !isString(timestamp) || version !== EVENT_VERSION) return null
  if (!isString(type) || !Object.hasOwn(PAYLOAD_CHECKS, type) || !isRecord(payload)) return null
  return PAYLOAD_CHECKS[type as EventType](payload) ? (raw as unknown as ServerEvent) : null
}
