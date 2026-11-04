/**
 * Protocolo renderer ↔ backend: ÚNICO archivo que conoce rutas y formas de red.
 *
 * Fuente: `backend/app/integrations/hermes/CONTRACT.md` §4 (rama drakter/agente-hermes)
 * y `backend/CONTRACT.md`. Los campos marcados SUPUESTO no constan en el contrato.
 *
 * Aprobar o rechazar NO está aquí a propósito: lo hace el proceso principal con un
 * diálogo nativo. El renderer no conoce esas rutas ni tiene forma de llamarlas.
 *
 * Todo lo que llega por red es dato no confiable: se valida aquí y se muestra
 * siempre como texto plano, nunca como HTML ni como instrucción.
 */

export const WS_SUBPROTOCOL = 'drakter.v1'
export const WS_AUTH_PREFIX = 'drakter.auth.'
export const EVENT_VERSION = 1

export const API_PATHS = {
  authCheck: '/api/v1/auth/check',
  agentStatus: '/api/v1/agent/status',
  chatSessions: '/api/v1/chat/sessions',
  sessionMessages: (sessionId: string) =>
    `/api/v1/chat/sessions/${encodeURIComponent(sessionId)}/messages`,
  cancelTurn: (turnId: string) => `/api/v1/chat/turns/${encodeURIComponent(turnId)}/cancel`
} as const

/** Ruta WS con reanudación. `afterSeq` nulo: solo eventos nuevos. */
export function chatEventsPath(afterSeq: number | null): string {
  return afterSeq === null ? '/api/v1/chat/events' : `/api/v1/chat/events?after_seq=${afterSeq}`
}

export const AGENT_STATES = ['idle', 'thinking', 'executing', 'speaking', 'error', 'offline'] as const
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

export interface ApiErrorDetail {
  readonly field: string | null
  readonly code: string
  readonly message: string
}

// ---- Eventos WebSocket ------------------------------------------------------

/** `summary` lo calcula el backend, nunca el modelo. */
export interface PendingConfirmation {
  readonly session_id: string
  readonly turn_id: string
  readonly action_id: string
  readonly summary: string
  readonly expires_at: string
}

export interface EventPayloads {
  'agent.status_changed': { readonly state: AgentState }
  /** ROADMAP §5.4; el backend aún no lo emite. */
  'agent.expression_changed': { readonly expression: string }
  'agent.message_delta': {
    readonly session_id: string
    readonly turn_id: string
    readonly delta: string
  }
  'agent.message_completed': {
    readonly session_id: string
    readonly turn_id: string
    readonly message_id: string
    readonly text: string
  }
  'agent.tool_started': {
    readonly session_id: string
    readonly turn_id: string
    readonly tool: string
    readonly call_id: string
  }
  'agent.tool_completed': {
    readonly session_id: string
    readonly turn_id: string
    readonly tool: string
    readonly call_id: string
    readonly error?: boolean
  }
  'agent.confirmation_required': PendingConfirmation
  'agent.error': {
    readonly session_id: string | null
    readonly turn_id: string | null
    readonly code: string
    readonly message: string
    readonly retryable: boolean
  }
  'agent.replay_truncated': Readonly<Record<string, unknown>>
}

export type EventType = keyof EventPayloads

export interface EventEnvelope<T extends EventType = EventType> {
  readonly event_id: string
  /** Secuencia global del backend: base de `after_seq` y de la deduplicación. */
  readonly seq: number
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
const isOptionalBoolean = (value: unknown): boolean => value === undefined || isBoolean(value)
const isDate = (value: unknown): boolean => isString(value) && !Number.isNaN(Date.parse(value))

function has(payload: Json, fields: Readonly<Record<string, (value: unknown) => boolean>>): boolean {
  return Object.entries(fields).every(([name, check]) => check(payload[name]))
}

export function isAgentState(value: unknown): value is AgentState {
  return (AGENT_STATES as readonly unknown[]).includes(value)
}

const TURN = { session_id: isString, turn_id: isString }
const TOOL_CALL = { ...TURN, tool: isString, call_id: isString }
const CONFIRMATION = { ...TURN, action_id: isString, summary: isString, expires_at: isDate }

export function isPendingConfirmation(value: unknown): value is PendingConfirmation {
  return isRecord(value) && has(value, CONFIRMATION)
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
  'agent.message_delta': (p) => has(p, { ...TURN, delta: isString }),
  'agent.message_completed': (p) => has(p, { ...TURN, message_id: isString, text: isString }),
  'agent.tool_started': (p) => has(p, TOOL_CALL),
  'agent.tool_completed': (p) => has(p, { ...TOOL_CALL, error: isOptionalBoolean }),
  'agent.confirmation_required': (p) => has(p, CONFIRMATION),
  'agent.error': (p) =>
    has(p, {
      session_id: isStringOrNull,
      turn_id: isStringOrNull,
      code: isString,
      message: isString,
      retryable: isBoolean
    }),
  'agent.replay_truncated': () => true
}

/** Devuelve el evento validado, o `null` si es desconocido, de otra versión o malformado. */
export function parseServerEvent(raw: unknown): ServerEvent | null {
  if (!isRecord(raw)) return null
  const { event_id, seq, timestamp, type, version, payload } = raw
  if (!isString(event_id) || !isCount(seq) || !isString(timestamp) || version !== EVENT_VERSION) return null
  if (!isString(type) || !Object.hasOwn(PAYLOAD_CHECKS, type) || !isRecord(payload)) return null
  return PAYLOAD_CHECKS[type as EventType](payload) ? (raw as unknown as ServerEvent) : null
}
