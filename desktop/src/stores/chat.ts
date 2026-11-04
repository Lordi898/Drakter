import { useSyncExternalStore } from 'react'
import { ApiError, cancelTurn, describeError, sendChatMessage } from '@/services/api'
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
  readonly tools: readonly ToolActivity[]
}

export const MAX_MESSAGE_CHARS = 8000
const MAX_KEPT = 500
const MAX_ENDED_TURNS = 200
const TURN_FAILED = 'El agente no pudo completar esta respuesta.'

/*
 * Supuestos sobre el protocolo (provisional):
 * - Un turno produce un mensaje del agente: `message_completed` cierra el turno.
 * - `message_completed.content` es autoritativo (sustituye a los deltas, incluso si
 *   falta alguno o no hubo ninguno) y puede promover un mensaje `interrupted` a `complete`.
 * - Los eventos de un turno pueden llegar antes que la respuesta HTTP del POST.
 */

let messages: readonly ChatMessage[] = []
let activeTurn: string | null = null
let sessionId: string | null = null
let wasOpen = false
let cancelling = false

const lastSeq = new Map<string, number>()
const endedTurns = new Set<string>()
const endedOrder: string[] = []
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
      if (oldest !== undefined) endedTurns.delete(oldest)
    }
  }
  if (activeTurn === turnId) setActiveTurn(null)
}

function placeholderId(turnId: string): string {
  return `pending-${turnId}`
}

function withoutError(message: ChatMessage): ChatMessage {
  const { error: _error, ...rest } = message
  void _error
  return rest
}

function failTools(tools: readonly ToolActivity[]): readonly ToolActivity[] {
  return tools.map((tool) => (tool.state === 'running' ? { ...tool, state: 'failed' as const } : tool))
}

function clean(text: string, max: number): string {
  // eslint-disable-next-line no-control-regex
  return text.replace(/[\u0000-\u001f\u007f]+/g, ' ').trim().slice(0, max)
}

/**
 * Busca el mensaje del agente por id; si no existe, adopta el marcador del turno
 * (creado por herramientas o errores previos a los deltas) para no duplicar burbuja.
 */
function upsertAgent(
  messageId: string,
  turnId: string,
  guard: (existing: ChatMessage) => boolean,
  mutate: (message: ChatMessage) => ChatMessage
): void {
  let list = messages
  let index = list.findIndex((m) => m.role === 'agent' && m.id === messageId)
  if (index < 0 && messageId !== placeholderId(turnId)) {
    index = list.findIndex((m) => m.role === 'agent' && m.id === placeholderId(turnId))
    const adopted = list[index]
    if (adopted) list = list.map((m, i) => (i === index ? { ...m, id: messageId } : m))
  }
  const existing = list[index]
  if (existing) {
    if (!guard(existing)) return
  } else {
    list = [...list, { id: messageId, role: 'agent', content: '', status: 'streaming', turnId, tools: [] }]
    index = list.length - 1
  }
  setMessages(list.map((m, i) => (i === index ? mutate(m) : m)))
}

function currentAgentTarget(turnId: string): string {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const m = messages[i]
    if (m && m.role === 'agent' && m.turnId === turnId && m.status === 'streaming') return m.id
  }
  return placeholderId(turnId)
}

function upsertTool(turnId: string, tool: ToolActivity): void {
  upsertAgent(
    currentAgentTarget(turnId),
    turnId,
    () => true,
    (m) => {
      const known = m.tools.some((t) => t.id === tool.id)
      return {
        ...m,
        tools: known ? m.tools.map((t) => (t.id === tool.id ? tool : t)) : [...m.tools, tool]
      }
    }
  )
}

function handleEvent(event: ServerEvent): void {
  switch (event.type) {
    case 'agent.message_delta': {
      const { turn_id, message_id, seq, delta } = event.payload
      const last = lastSeq.get(message_id) ?? -1
      if (seq <= last) return
      const before = messages
      upsertAgent(
        message_id,
        turn_id,
        (m) => m.status === 'streaming',
        (m) => ({ ...m, content: m.content + delta, status: 'streaming' })
      )
      if (messages === before) return // ignorado (mensaje ya terminado)
      lastSeq.set(message_id, seq)
      if (!endedTurns.has(turn_id)) setActiveTurn(turn_id)
      return
    }
    case 'agent.message_completed': {
      const { turn_id, message_id, content } = event.payload
      upsertAgent(
        message_id,
        turn_id,
        (m) => m.status !== 'failed',
        (m) => ({ ...withoutError(m), content, status: 'complete', turnId: turn_id })
      )
      lastSeq.delete(message_id)
      endTurn(turn_id)
      return
    }
    case 'agent.tool_started': {
      const { turn_id, tool_call_id, tool_name } = event.payload
      if (endedTurns.has(turn_id)) return
      upsertTool(turn_id, { id: tool_call_id, name: clean(tool_name, 100), state: 'running' })
      setActiveTurn(turn_id)
      return
    }
    case 'agent.tool_completed': {
      const { turn_id, tool_call_id, tool_name, ok } = event.payload
      const state = ok ? 'ok' : 'failed'
      const owner = messages.find((m) => m.role === 'agent' && m.tools.some((t) => t.id === tool_call_id))
      if (owner) {
        setMessages(
          messages.map((m) =>
            m === owner ? { ...m, tools: m.tools.map((t) => (t.id === tool_call_id ? { ...t, state } : t)) } : m
          )
        )
      } else if (!endedTurns.has(turn_id)) {
        upsertTool(turn_id, { id: tool_call_id, name: clean(tool_name, 100), state })
      }
      return
    }
    case 'agent.error': {
      const { turn_id, message, recoverable } = event.payload
      if (turn_id === null) {
        if (!recoverable) {
          notify({
            tone: 'error',
            title: 'El agente ha tenido un problema',
            body: clean(message, 200) || 'Error no especificado.',
            desktop: true
          })
        }
        return
      }
      failTurn(turn_id)
      return
    }
    default:
      return
  }
}

function failTurn(turnId: string): void {
  endTurn(turnId)
  let touched = false
  const next = messages.map((m): ChatMessage => {
    if (m.role === 'agent' && m.turnId === turnId && (m.status === 'streaming' || m.status === 'interrupted')) {
      touched = true
      lastSeq.delete(m.id)
      return { ...m, status: 'failed', error: TURN_FAILED, tools: failTools(m.tools) }
    }
    return m
  })
  if (touched) {
    setMessages(next)
  } else if (!messages.some((m) => m.role === 'agent' && m.turnId === turnId)) {
    setMessages([
      ...messages,
      { id: placeholderId(turnId), role: 'agent', content: '', status: 'failed', turnId, error: TURN_FAILED, tools: [] }
    ])
  }
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

// Suscripciones: una sola vez, al cargar el módulo.
subscribeServerEvents(handleEvent)
subscribeLinkStatus((status) => {
  if (status === 'open') {
    wasOpen = true
    return
  }
  if (!wasOpen) return
  wasOpen = false
  // Link perdido: lo que estaba llegando queda cortado; un `message_completed` posterior puede completarlo.
  interruptStreaming(null)
  setActiveTurn(null)
})

// ---- Envío -------------------------------------------------------------------

function patchMessage(id: string, change: (m: ChatMessage) => ChatMessage): void {
  setMessages(messages.map((m) => (m.id === id ? change(m) : m)))
}

async function deliver(id: string, content: string): Promise<void> {
  startBackendLink()
  try {
    const response = await sendChatMessage({ session_id: sessionId, client_message_id: id, content })
    sessionId = response.session_id
    const turnId = response.turn_id
    patchMessage(id, (m) => ({ ...withoutError(m), status: 'complete', turnId }))
    // Los eventos del turno pueden haber llegado antes que esta respuesta.
    const settled = messages.some(
      (m) => m.role === 'agent' && m.turnId === turnId && m.status !== 'streaming'
    )
    if (!endedTurns.has(turnId) && !settled) setActiveTurn(turnId)
  } catch (error) {
    patchMessage(id, (m) => ({
      ...m,
      status: 'failed',
      error: describeError(error, 'No se pudo enviar el mensaje.')
    }))
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
