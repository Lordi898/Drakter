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

import type {
  AgentState,
  ConfirmationOut,
  ConfirmationRequested,
  ConfirmationResolved,
  ConfirmationTicket,
  AgentStatusOut,
  ChatSession,
  EventType as ContractEventType,
  MessageAccepted,
  MessageCreate,
  MessageOut,
  Page,
  TypedEvent
} from '../../../contracts/ts'

export type { AgentState, ConfirmationOut, ConfirmationTicket, MessageOut, Page }
export type ChatSessionInfo = Pick<ChatSession, 'id'>
export type SendMessageRequest = MessageCreate
export type SendMessageResponse = MessageAccepted
export type AgentStatusInfo = AgentStatusOut

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
] as const satisfies readonly AgentState[]

// ---- REST ------------------------------------------------------------------

export interface ApiErrorDetail {
  readonly field: string | null
  readonly code: string
  readonly message: string
}

// ---- Eventos WebSocket ------------------------------------------------------

/**
 * Forma común de lo pendiente, llegue por `confirmation.requested`, por un ticket
 * 409 o por `ConfirmationOut`. `summary` y `affected_count` los calcula el backend.
 */
export type PendingConfirmation = Pick<ConfirmationRequested, 'action_id' | 'summary' | 'expires_at'> &
  Partial<Pick<ConfirmationRequested, 'session_id' | 'turn_id' | 'tool' | 'affected_count'>>

export const CONFIRMATION_STATUSES = [
  'approved',
  'rejected',
  'expired',
  'executed',
  'failed'
] as const satisfies readonly ConfirmationResolved['status'][]

/** Tipos del contrato que esta capa consume y valida; el resto se ignora en `ws.ts`. */
export type EventType = Extract<
  ContractEventType,
  | 'agent.status_changed'
  | 'agent.expression_changed'
  | 'agent.turn_started'
  | 'agent.turn_finished'
  | 'agent.message_started'
  | 'agent.message_delta'
  | 'agent.message_completed'
  | 'agent.tool_started'
  | 'agent.tool_completed'
  | 'agent.error'
  | 'confirmation.requested'
  | 'confirmation.resolved'
  | 'notification.created'
  | 'system.resync_required'
>

/** Unión discriminada generada: `switch (event.type)` estrecha `payload`. */
export type ServerEvent = Extract<TypedEvent, { type: EventType }>

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

/** Los listados del contrato no traen `session_id` ni `tool`, sino `tool_name`. */
export function isConfirmationOut(value: unknown): value is ConfirmationOut {
  return (
    isRecord(value) &&
    has(value, {
      id: isString,
      tool_name: isString,
      summary: isString,
      affected_count: (v) => v === null || v === undefined || isCount(v),
      expires_at: isDate,
      status: isString
    })
  )
}

export function isConfirmationTicket(value: unknown): value is ConfirmationTicket {
  return (
    isRecord(value) &&
    has(value, {
      id: isString,
      summary: isString,
      affected_count: (v) => v === null || v === undefined || isCount(v),
      expires_at: isDate,
      params_hash: isString
    })
  )
}

export function isMessageOut(value: unknown): value is MessageOut {
  return (
    isRecord(value) &&
    has(value, {
      id: isString,
      text: isString,
      turn_id: (v) => v === undefined || isStringOrNull(v),
      role: (v) => v === 'user' || v === 'assistant' || v === 'system',
      status: (v) => v === 'streaming' || v === 'complete' || v === 'cancelled' || v === 'failed'
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
