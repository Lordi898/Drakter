import { useSyncExternalStore } from 'react'
import {
  ApiError,
  cancelTurn,
  createChatSession,
  describeError,
  listSessionMessages,
  sendChatMessage
} from '@/services/api'
import { notify } from '@/services/notify'
import type { ServerEvent } from '@/services/protocol'
import { startBackendLink, subscribeLinkStatus, subscribeServerEvents } from '@/services/ws'

export type ChatMessageStatus = 'sending' | 'streaming' | 'complete' | 'failed' | 'interrupted'

export interface ToolActivity {
  readonly id: string
  readonly name: string
  readonly state: 'running' | 'ok' | 'failed'
}

export interface ChatMessage {
  readonly id: string
  readonly role: 'user' | 'agent'
  readonly content: string
  readonly status: ChatMessageStatus
  readonly turnId: string | null
  readonly error?: string
  /** En mensajes `failed` del agente: si el backend dijo que reintentar tiene sentido. */
  readonly retryable?: boolean
  readonly tools: readonly ToolActivity[]
}

export const MAX_MESSAGE_CHARS = 8000
const MAX_KEPT = 500
const MAX_ENDED_TURNS = 200
const TURN_FAILED = 'El agente no pudo completar esta respuesta.'
const BUSY = 'Drakter sigue respondiendo. Espera a que termine o cancela el turno.'

/*
 * Supuestos sobre el protocolo (hermes CONTRACT §4):
 * - Una burbuja del agente por turno, identificada por turn_id (id local `agent:<turn>`).
 * - `message_completed.text` es autoritativo y cierra el turno; puede promover un mensaje
 *   `interrupted` (corte de enlace o cancelación) a `complete`.
 * - Tras un corte de enlace, el replay por after_seq reanuda los deltas perdidos, así que
 *   un mensaje `interrupted` por enlace sigue recibiendo deltas. Tras cancelar, no.
 * - `seq` y la deduplicación los resuelve ws.ts.
 */

let messages: readonly ChatMessage[] = []
let activeTurn: string | null = null
let sessionId: string | null = null
let sessionPromise: Promise<string> | null = null
let wasOpen = false
let cancelling = false
let rehydrating = false

const endedTurns = new Set<string>()
const endedOrder: string[] = []
const cancelledTurns = new Set<string>()
const listeners = new Set<() => void>()

function emit(): void {
  listeners.forEach((listener) => listener())
}

function setMessages(next: readonly ChatMessage[]): void {
  messages = next.length > MAX_KEPT ? next.slice(next.length - MAX_KEPT) : next
  emit()
}

function setActiveTurn(next: string | null): void {
  if (activeTurn === next) return
  activeTurn = next
  emit()
}

function endTurn(turnId: string): void {
  if (!endedTurns.has(turnId)) {
    endedTurns.add(turnId)
    endedOrder.push(turnId)
    if (endedOrder.length > MAX_ENDED_TURNS) {
      const oldest = endedOrder.shift()
      if (oldest !== undefined) {
        endedTurns.delete(oldest)
        cancelledTurns.delete(oldest)
      }
    }
  }
  if (activeTurn === turnId) setActiveTurn(null)
}

function agentId(turnId: string): string {
  return `agent:${turnId}`
}

function withoutError(message: ChatMessage): ChatMessage {
  const { error: _error, retryable: _retryable, ...rest } = message
  void _error
  void _retryable
  return rest
}

function failTools(tools: readonly ToolActivity[]): readonly ToolActivity[] {
  return tools.map((tool) => (tool.state === 'running' ? { ...tool, state: 'failed' as const } : tool))
}

function clean(text: string, max: number): string {
  // eslint-disable-next-line no-control-regex
  return text.replace(/[\u0000-\u001f\u007f]+/g, ' ').trim().slice(0, max)
}

/** Burbuja del agente de un turno; la crea (en `streaming`) si no existe. `guard` decide si se puede tocar. */
function upsertAgent(
  turnId: string,
  guard: (existing: ChatMessage) => boolean,
  mutate: (message: ChatMessage) => ChatMessage
): boolean {
  const id = agentId(turnId)
  const index = messages.findIndex((m) => m.id === id)
  const existing = messages[index]
  if (existing) {
    if (!guard(existing)) return false
    setMessages(messages.map((m, i) => (i === index ? mutate(m) : m)))
    return true
  }
  const created: ChatMessage = { id, role: 'agent', content: '', status: 'streaming', turnId, tools: [] }
  setMessages([...messages, mutate(created)])
  return true
}

function upsertTool(turnId: string, tool: ToolActivity): void {
  upsertAgent(
    turnId,
    (m) => m.status === 'streaming' || m.status === 'interrupted',
    (m) => {
      const known = m.tools.some((t) => t.id === tool.id)
      return { ...m, tools: known ? m.tools.map((t) => (t.id === tool.id ? tool : t)) : [...m.tools, tool] }
    }
  )
}

function handleEvent(event: ServerEvent): void {
  switch (event.type) {
    case 'agent.message_delta': {
      const { turn_id, delta } = event.payload
      if (cancelledTurns.has(turn_id)) return
      const applied = upsertAgent(
        turn_id,
        (m) => m.status === 'streaming' || m.status === 'interrupted',
        (m) => ({ ...m, content: m.content + delta, status: 'streaming' })
      )
      if (applied && !endedTurns.has(turn_id)) setActiveTurn(turn_id)
      return
    }
    case 'agent.message_completed': {
      const { turn_id, text } = event.payload
      upsertAgent(
        turn_id,
        (m) => m.status !== 'failed',
        (m) => ({ ...withoutError(m), content: text, status: 'complete', turnId: turn_id })
      )
      endTurn(turn_id)
      return
    }
    case 'agent.tool_started': {
      const { turn_id, call_id, tool } = event.payload
      if (endedTurns.has(turn_id)) return
      upsertTool(turn_id, { id: call_id, name: clean(tool, 100), state: 'running' })
      setActiveTurn(turn_id)
      return
    }
    case 'agent.tool_completed': {
      const { turn_id, call_id, tool, error } = event.payload
      const state = error ? 'failed' : 'ok'
      const owner = messages.find((m) => m.role === 'agent' && m.tools.some((t) => t.id === call_id))
      if (owner) {
        setMessages(
          messages.map((m) =>
            m === owner ? { ...m, tools: m.tools.map((t) => (t.id === call_id ? { ...t, state } : t)) } : m
          )
        )
      } else if (!endedTurns.has(turn_id)) {
        upsertTool(turn_id, { id: call_id, name: clean(tool, 100), state })
      }
      return
    }
    case 'agent.error': {
      const { turn_id, message, retryable } = event.payload
      if (turn_id !== null) {
        failTurn(turn_id, retryable)
      } else if (!retryable) {
        notify({
          tone: 'error',
          title: 'El agente ha tenido un problema',
          body: clean(message, 200) || 'Error no especificado.',
          desktop: true
        })
      }
      return
    }
    case 'agent.replay_truncated':
      void rehydrate()
      return
    default:
      return
  }
}

function failTurn(turnId: string, retryable: boolean): void {
  endTurn(turnId)
  const id = agentId(turnId)
  const existing = messages.find((m) => m.id === id)
  if (existing && (existing.status === 'complete' || existing.status === 'failed')) return
  const failed: ChatMessage = {
    id,
    role: 'agent',
    content: existing?.content ?? '',
    status: 'failed',
    turnId,
    error: TURN_FAILED,
    retryable,
    tools: failTools(existing?.tools ?? [])
  }
  setMessages(existing ? messages.map((m) => (m === existing ? failed : m)) : [...messages, failed])
}

function interruptStreaming(turnId: string | null): void {
  let touched = false
  const next = messages.map((m): ChatMessage => {
    if (m.role === 'agent' && m.status === 'streaming' && (turnId === null || m.turnId === turnId)) {
      touched = true
      return { ...m, status: 'interrupted', tools: failTools(m.tools) }
    }
    return m
  })
  if (touched) setMessages(next)
}

/** El replay ya no cubre lo perdido: se relee el historial de la sesión y se sustituye la lista. */
async function rehydrate(): Promise<void> {
  const id = sessionId
  if (id === null || rehydrating) {
    interruptStreaming(null)
    setActiveTurn(null)
    return
  }
  rehydrating = true
  try {
    const stored = await listSessionMessages(id)
    const storedTurns = new Set(stored.map((m) => m.turn_id).filter((t): t is string => t !== null && t !== ''))
    const fromServer: ChatMessage[] = stored.map((m) => ({
      id: m.id,
      role: m.role,
      content: m.text,
      status: 'complete',
      turnId: m.turn_id,
      tools: []
    }))
    // Lo local que el servidor aún no refleja (envíos en curso, fallos, respuesta en vuelo) se conserva.
    const local = messages.filter(
      (m) =>
        (m.status === 'sending' || m.status === 'failed' || m.status === 'streaming') &&
        !(m.role === 'agent' && m.turnId !== null && storedTurns.has(m.turnId))
    )
    setMessages([...fromServer, ...local])
  } catch {
    interruptStreaming(null)
    setActiveTurn(null)
  } finally {
    rehydrating = false
  }
}

// Suscripciones: una sola vez, al cargar el módulo.
subscribeServerEvents(handleEvent)
subscribeLinkStatus((status) => {
  if (status === 'open') {
    wasOpen = true
    return
  }
  if (!wasOpen) return
  wasOpen = false
  // Enlace perdido: lo que llegaba queda cortado; el replay o un `message_completed` posterior pueden reanudarlo.
  interruptStreaming(null)
  setActiveTurn(null)
})

// ---- Envío -------------------------------------------------------------------

function patchMessage(id: string, change: (m: ChatMessage) => ChatMessage): void {
  setMessages(messages.map((m) => (m.id === id ? change(m) : m)))
}

function ensureSession(): Promise<string> {
  if (sessionId !== null) return Promise.resolve(sessionId)
  if (!sessionPromise) {
    sessionPromise = createChatSession()
      .then((info) => {
        sessionId = info.id
        return info.id
      })
      .finally(() => {
        sessionPromise = null
      })
  }
  return sessionPromise
}

async function post(id: string, content: string) {
  const request = { text: content, client_message_id: id }
  try {
    return await sendChatMessage(await ensureSession(), request)
  } catch (error) {
    // Sesión desconocida (p. ej. backend reiniciado): se crea otra y se reintenta una sola vez.
    if (!(error instanceof ApiError && error.status === 404)) throw error
    sessionId = null
    return sendChatMessage(await ensureSession(), request)
  }
}

async function deliver(id: string, content: string): Promise<void> {
  startBackendLink()
  try {
    const { turn_id: turnId } = await post(id, content)
    patchMessage(id, (m) => ({ ...withoutError(m), status: 'complete', turnId }))
    // Los eventos del turno pueden haber llegado antes que esta respuesta: la burbuja ya existe por turn_id.
    const bubble = messages.find((m) => m.id === agentId(turnId))
    const settled = bubble !== undefined && bubble.status !== 'streaming'
    if (!endedTurns.has(turnId) && !settled) setActiveTurn(turnId)
  } catch (error) {
    const message =
      error instanceof ApiError && error.code === 'agent_busy'
        ? BUSY
        : describeError(error, 'No se pudo enviar el mensaje.')
    patchMessage(id, (m) => ({ ...m, status: 'failed', error: message }))
  }
}

async function submit(content: string): Promise<void> {
  const id = crypto.randomUUID()
  setMessages([...messages, { id, role: 'user', content, status: 'sending', turnId: null, tools: [] }])
  await deliver(id, content)
}

export async function sendMessage(text: string): Promise<void> {
  const content = text.trim()
  if (content.length === 0) throw new Error('Escribe un mensaje antes de enviarlo.')
  if (content.length > MAX_MESSAGE_CHARS) {
    throw new Error(`El mensaje es demasiado largo (máximo ${MAX_MESSAGE_CHARS} caracteres).`)
  }
  await submit(content)
}

export async function retryMessage(id: string): Promise<void> {
  const index = messages.findIndex((m) => m.id === id)
  const target = messages[index]
  if (!target || target.status !== 'failed') return

  if (target.role === 'user') {
    // Mismo client_message_id: si el servidor ya lo recibió, no se duplica.
    patchMessage(id, (m) => ({ ...withoutError(m), status: 'sending', turnId: null }))
    await deliver(id, target.content)
    return
  }

  if (target.retryable === false) return
  let source: ChatMessage | undefined = messages.find(
    (m) => m.role === 'user' && target.turnId !== null && m.turnId === target.turnId
  )
  if (!source) {
    for (let i = index - 1; i >= 0 && !source; i -= 1) {
      const candidate = messages[i]
      if (candidate && candidate.role === 'user') source = candidate
    }
  }
  if (!source) return
  setMessages(messages.filter((m) => m.id !== id))
  await submit(source.content)
}

export async function cancelActiveTurn(): Promise<void> {
  const turnId = activeTurn
  if (turnId === null || cancelling) return
  cancelling = true
  try {
    await cancelTurn(turnId)
  } catch (error) {
    // 404/409: el turno ya había terminado; se cierra en local igualmente.
    if (!(error instanceof ApiError && (error.status === 404 || error.status === 409))) {
      notify({ tone: 'warning', title: 'No se pudo cancelar', body: describeError(error, 'Inténtalo de nuevo.') })
      return
    }
  } finally {
    cancelling = false
  }
  // El contrato no define evento terminal de cancelación: se cierra aquí. Un message_completed posterior lo sustituye.
  cancelledTurns.add(turnId)
  interruptStreaming(turnId)
  endTurn(turnId)
}

export function dismissChatError(id: string): void {
  const target = messages.find((m) => m.id === id)
  if (!target || target.status !== 'failed') return
  if (target.role === 'user' || target.content.length === 0) {
    setMessages(messages.filter((m) => m.id !== id))
    return
  }
  patchMessage(id, (m) => ({ ...withoutError(m), status: 'interrupted' }))
}

// ---- Hooks --------------------------------------------------------------------

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export function useChatMessages(): readonly ChatMessage[] {
  return useSyncExternalStore(subscribe, () => messages)
}

export function useActiveTurn(): string | null {
  return useSyncExternalStore(subscribe, () => activeTurn)
}
