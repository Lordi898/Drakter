/**
 * Protocolo renderer ↔ backend: formas de datos y validación.
 *
 * Fuente: `contracts/` (rama drakter/contratos, manda sobre todo lo demás),
 * `contracts/python/drakter_contracts/events.py` y
 * `backend/app/integrations/hermes/CONTRACT.md`. SUPUESTO marca lo no contratado.
 *
 * El renderer no tiene credenciales ni red (D-14): todo va por `window.api`.
 * Aprobar o rechazar no existe aquí: lo hace main con un diálogo nativo.
 *
 * Todo lo que llega por red es dato no confiable: se valida aquí y se muestra
 * siempre como texto plano, nunca como HTML ni como instrucción.
 */

export const EVENT_VERSION = 1

export const AGENT_STATES = [
  'idle',
  'listening',
  'thinking',
  'speaking',
  'executing',
  'success',
  'error',
  'interrupted',
  'offline'
] as const
export type AgentState = (typeof AGENT_STATES)[number]

// ---- REST ------------------------------------------------------------------

/** SUPUESTO: de `ChatSession` solo se usa `id`. */
export interface ChatSessionInfo {
  readonly id: string
}

export interface SendMessageRequest {
  readonly text: string
  readonly client_message_id: string
}

/** 202: la respuesta llega por WebSocket. */
export interface SendMessageResponse {
  readonly turn_id: string
  readonly message_id: string
}

export interface AgentStatusInfo {
  readonly state: AgentState
  readonly provider: string
  readonly model: string
  readonly detail: string | null
}

/** SUPUESTO: forma de cada elemento de `GET /chat/sessions/{id}/messages`. */
export interface StoredChatMessage {
  readonly id: string
  readonly role: 'user' | 'agent'
  readonly text: string
  readonly turn_id: string | null
}

/** Cuerpo `confirmation` de un 409 `confirmation_required` (contracts/errors.py). */
export interface ConfirmationTicket {
  readonly id: string
  readonly summary: string
  readonly affected_count: number | null
  readonly expires_at: string
  readonly params_hash?: string
}

export interface ApiErrorDetail {
  readonly field: string | null
  readonly code: string
  readonly message: string
}

// ---- Eventos WebSocket ------------------------------------------------------

/** `summary` y `affected_count` los calcula el backend, nunca el modelo. */
export interface PendingConfirmation {
  readonly action_id: string
  readonly session_id?: string | null
  readonly turn_id?: string | null
  readonly tool?: string
  readonly summary: string
  readonly affected_count?: number | null
  readonly expires_at: string
}

export const CONFIRMATION_STATUSES = ['approved', 'rejected', 'expired', 'executed', 'failed'] as const

interface TurnRef {
  readonly session_id: string
  readonly turn_id: string
}

interface ToolCall extends TurnRef {
  readonly tool: string
  readonly call_id: string
  readonly source?: 'drakter' | 'hermes'
}

export interface EventPayloads {
  'agent.status_changed': {
    readonly state: AgentState
    readonly previous?: AgentState | null
    readonly turn_id?: string | null
    readonly reason?: string | null
  }
  'agent.expression_changed': {
    readonly expression: string
    readonly intensity?: number | null
    readonly turn_id?: string | null
  }
  'agent.turn_started': TurnRef & { readonly input_source?: 'text' | 'voice' }
  'agent.turn_finished': TurnRef & {
    readonly outcome: 'completed' | 'failed' | 'cancelled' | 'interrupted'
  }
  'agent.message_started': TurnRef & { readonly message_id: string }
  'agent.message_delta': TurnRef & { readonly delta: string }
  'agent.message_completed': TurnRef & { readonly message_id: string; readonly text: string }
  'agent.tool_started': ToolCall
  'agent.tool_completed': ToolCall & { readonly error?: boolean }
  'agent.error': {
    readonly session_id?: string | null
    readonly turn_id?: string | null
    readonly code: string
    readonly message: string
    readonly retryable?: boolean
  }
  'confirmation.requested': PendingConfirmation
  'confirmation.resolved': {
    readonly action_id: string
    readonly status: (typeof CONFIRMATION_STATUSES)[number]
    readonly error_code?: string | null
  }
  'notification.created': {
    readonly notification_id: string
    readonly kind: string
    readonly title: string
    readonly severity?: 'info' | 'success' | 'warning' | 'error'
  }
  'system.resync_required': {
    readonly reason: 'buffer_overflow' | 'boot_changed' | 'client_lagging'
  }
}

export type EventType = keyof EventPayloads

export interface EventEnvelope<T extends EventType = EventType> {
  readonly event_id: string
  /** Monótono por `boot_id`. Un hueco o un `boot_id` nuevo obligan a releer por REST. */
  readonly seq: number
  readonly boot_id: string
  readonly timestamp: string
  readonly type: T
  readonly version: number
  readonly correlation_id?: string | null
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
const isOptionalBoolean = (value: unknown): boolean => value === undefined || isBoolean(value)
const isDate = (value: unknown): boolean => isString(value) && !Number.isNaN(Date.parse(value))

function has(payload: Json, fields: Readonly<Record<string, (value: unknown) => boolean>>): boolean {
  return Object.entries(fields).every(([name, check]) => check(payload[name]))
}

export function isAgentState(value: unknown): value is AgentState {
  return (AGENT_STATES as readonly unknown[]).includes(value)
}

const isOptionalString = (value: unknown): boolean => value === undefined || isStringOrNull(value)
const isOptionalCount = (value: unknown): boolean => value === undefined || value === null || isCount(value)

const TURN = { session_id: isString, turn_id: isString }
const TOOL_CALL = { ...TURN, tool: isString, call_id: isString }
const CONFIRMATION = {
  action_id: isString,
  session_id: isOptionalString,
  turn_id: isOptionalString,
  tool: isOptionalString,
  summary: isString,
  affected_count: isOptionalCount,
  expires_at: isDate
}
const RESYNC_REASONS = new Set(['buffer_overflow', 'boot_changed', 'client_lagging'])
const NOTIFICATION_SEVERITIES = new Set(['info', 'success', 'warning', 'error'])
const TURN_OUTCOMES = new Set(['completed', 'failed', 'cancelled', 'interrupted'])

export function isPendingConfirmation(value: unknown): value is PendingConfirmation {
  return isRecord(value) && has(value, CONFIRMATION)
}

export function isConfirmationTicket(value: unknown): value is ConfirmationTicket {
  return (
    isRecord(value) &&
    has(value, {
      id: isString,
      summary: isString,
      affected_count: (v) => v === null || v === undefined || isCount(v),
      expires_at: isDate,
      params_hash: (v) => v === undefined || isString(v)
    })
  )
}

export function isStoredChatMessage(value: unknown): value is StoredChatMessage {
  return (
    isRecord(value) &&
    has(value, {
      id: isString,
      text: isString,
      turn_id: isStringOrNull,
      role: (v) => v === 'user' || v === 'agent'
    })
  )
}

const PAYLOAD_CHECKS: { readonly [T in EventType]: (payload: Json) => boolean } = {
  'agent.status_changed': (p) => isAgentState(p['state']),
  'agent.expression_changed': (p) => has(p, { expression: isString }),
  'agent.turn_started': (p) => has(p, TURN),
  'agent.turn_finished': (p) => has(p, { ...TURN, outcome: (v) => TURN_OUTCOMES.has(v as string) }),
  'agent.message_started': (p) => has(p, { ...TURN, message_id: isString }),
  'agent.message_delta': (p) => has(p, { ...TURN, delta: isString }),
  'agent.message_completed': (p) => has(p, { ...TURN, message_id: isString, text: isString }),
  'agent.tool_started': (p) => has(p, TOOL_CALL),
  'agent.tool_completed': (p) => has(p, { ...TOOL_CALL, error: isOptionalBoolean }),
  'agent.error': (p) =>
    has(p, {
      session_id: isOptionalString,
      turn_id: isOptionalString,
      code: isString,
      message: isString,
      retryable: isOptionalBoolean
    }),
  'confirmation.requested': (p) => has(p, CONFIRMATION),
  'confirmation.resolved': (p) =>
    has(p, {
      action_id: isString,
      status: (v) => (CONFIRMATION_STATUSES as readonly unknown[]).includes(v)
    }),
  'notification.created': (p) =>
    has(p, {
      notification_id: isString,
      kind: isString,
      title: isString,
      severity: (v) => v === undefined || NOTIFICATION_SEVERITIES.has(v as string)
    }),
  'system.resync_required': (p) => RESYNC_REASONS.has(p['reason'] as string)
}

/** Tipos del catálogo v1 que esta capa no consume: se ignoran sin avisar. */
export function isKnownEventType(type: string): type is EventType {
  return Object.hasOwn(PAYLOAD_CHECKS, type)
}

/**
 * Devuelve el evento validado, o `null` si es de un tipo que aquí no se consume,
 * de otra versión o malformado. `version` es por tipo; hoy todos van en 1.
 */
export function parseServerEvent(raw: unknown): ServerEvent | null {
  if (!isRecord(raw)) return null
  const { event_id, seq, boot_id, timestamp, type, version, payload } = raw
  if (!isString(event_id) || !isCount(seq) || !isString(boot_id) || !isString(timestamp)) return null
  if (version !== EVENT_VERSION || !isString(type) || !isKnownEventType(type) || !isRecord(payload)) return null
  return PAYLOAD_CHECKS[type](payload) ? (raw as unknown as ServerEvent) : null
}
