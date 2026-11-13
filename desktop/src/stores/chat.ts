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
import type { MessageOut, ServerEvent } from '@/services/protocol'
import { startBackendLink, subscribeLinkStatus, subscribeResync, subscribeServerEvents } from '@/services/ws'

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
  /** Solo en mensajes del usuario dictados por voz. */
  readonly viaVoice?: boolean
  readonly error?: string
  /** En mensajes `failed` del agente: si el backend dijo que reintentar tiene sentido. */
  readonly retryable?: boolean
  readonly tools: readonly ToolActivity[]
}

export const MAX_MESSAGE_CHARS = 8000
const MAX_KEPT = 500
const MAX_ENDED_TURNS = 200
const STORED_STATUS: Record<MessageOut['status'], ChatMessageStatus> = {
  streaming: 'streaming',
  complete: 'complete',
  cancelled: 'interrupted',
  failed: 'failed'
}
const TURN_FAILED = 'El agente no pudo completar esta respuesta.'

/*
 * Contrato de eventos (contracts/ v1):
 * - `agent.turn_finished` es el terminal real del turno (completed/failed/cancelled/interrupted).
 * - `agent.message_started` aporta `message_id`; un turno puede tener varios mensajes. Los deltas
 *   no llevan `message_id`: van al mensaje en curso del turno, o a un marcador `agent:<turn>` que
 *   `message_started`/`message_completed` adoptan sin perder lo recibido.
 * - `seq`, huecos y boot_id los resuelve ws.ts, que avisa con resync.
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

function placeholderId(turnId: string): string {
  return agentId(turnId)
}

/** Mensaje del agente en curso en un turno (el último `streaming`; un `interrupted` por enlace puede reanudarse). */
function currentBubble(turnId: string): ChatMessage | undefined {
  let resumable: ChatMessage | undefined
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const m = messages[i]
    if (!m || m.role !== 'agent' || m.turnId !== turnId) continue
    if (m.status === 'streaming') return m
    if (m.status === 'interrupted' && !endedTurns.has(turnId) && !resumable) resumable = m
  }
  return resumable
}

function addBubble(message: ChatMessage): void {
  setMessages([...messages, message])
}

function patchBubble(id: string, change: (m: ChatMessage) => ChatMessage): void {
  setMessages(messages.map((m) => (m.id === id && m.role === 'agent' ? change(m) : m)))
}

function newBubble(id: string, turnId: string): ChatMessage {
  return { id, role: 'agent', content: '', status: 'streaming', turnId, tools: [] }
}

function upsertTool(turnId: string, tool: ToolActivity): void {
  const target = currentBubble(turnId)
  const apply = (m: ChatMessage): ChatMessage => {
    const known = m.tools.some((t) => t.id === tool.id)
    return { ...m, tools: known ? m.tools.map((t) => (t.id === tool.id ? tool : t)) : [...m.tools, tool] }
  }
  if (target) patchBubble(target.id, apply)
  else addBubble(apply(newBubble(placeholderId(turnId), turnId)))
}

function finishTurn(turnId: string, outcome: 'completed' | 'failed' | 'cancelled' | 'interrupted'): void {
  endTurn(turnId)
  const mine = (m: ChatMessage): boolean =>
    m.role === 'agent' && m.turnId === turnId && (m.status === 'streaming' || m.status === 'interrupted')
  if (outcome === 'failed') {
    failTurn(turnId, false)
    return
  }
  const next = messages.map((m): ChatMessage => {
    if (!mine(m)) return m
    if (outcome === 'completed') return { ...m, status: 'complete' }
    return { ...m, status: 'interrupted', tools: failTools(m.tools) }
  })
  setMessages(next)
}

/** La voz usa la sesión del backend (`current_session()`): el renderer la adopta de los eventos. */
function adoptSession(id: string): void {
  if (sessionId === id) return
  const hadSession = sessionId !== null
  sessionId = id
  if (hadSession || messages.length === 0) void rehydrate()
}

function onUserMessage(p: {
  message_id: string
  session_id: string
  turn_id: string
  text: string
  input_source: 'text' | 'voice'
}): void {
  adoptSession(p.session_id)
  const viaVoice = p.input_source === 'voice'
  // Ya existe por message_id (optimista o rehidratado): solo se completa con el turno.
  const byId = messages.find((m) => m.role === 'user' && m.id === p.message_id)
  // Optimista aún sin turno (la respuesta REST no ha llegado): mismo texto, enviándose.
  const pending = byId
    ? undefined
    : messages.find((m) => m.role === 'user' && m.status === 'sending' && m.turnId === null && m.content === p.text)
  // Optimista de texto que ya tiene turno (id = client_message_id). No aplica a la voz: no hay
  // optimista, y una corrección por voz (steer) llega con el turn_id del turno que corrige.
  const byTurn = viaVoice ? undefined : messages.find((m) => m.role === 'user' && m.turnId === p.turn_id)
  const known = byId ?? pending ?? byTurn
  if (known) {
    if (known.turnId === null || (viaVoice && !known.viaVoice)) {
      setMessages(messages.map((m) => (m === known ? { ...m, turnId: p.turn_id, ...(viaVoice ? { viaVoice } : {}) } : m)))
    }
    return
  }
  setMessages([
    ...messages,
    {
      id: p.message_id,
      role: 'user',
      content: p.text,
      status: 'complete',
      turnId: p.turn_id,
      ...(viaVoice ? { viaVoice } : {}),
      tools: []
    }
  ])
}

function handleEvent(event: ServerEvent): void {
  switch (event.type) {
    case 'chat.user_message':
      onUserMessage(event.payload)
      return
    case 'agent.turn_started': {
      const { turn_id, session_id } = event.payload
      adoptSession(session_id)
      if (!endedTurns.has(turn_id)) setActiveTurn(turn_id)
      return
    }
    case 'agent.turn_finished':
      finishTurn(event.payload.turn_id, event.payload.outcome)
      return
    case 'agent.message_started': {
      const { turn_id, message_id } = event.payload
      if (endedTurns.has(turn_id)) return
      if (messages.some((m) => m.role === 'agent' && m.id === message_id)) return
      const holder = messages.find((m) => m.role === 'agent' && m.id === placeholderId(turn_id) && m.status === 'streaming')
      if (holder) setMessages(messages.map((m) => (m === holder ? { ...m, id: message_id } : m)))
      else addBubble(newBubble(message_id, turn_id))
      setActiveTurn(turn_id)
      return
    }
    case 'agent.message_delta': {
      const { turn_id, delta } = event.payload
      if (endedTurns.has(turn_id)) return
      const target = currentBubble(turn_id)
      const apply = (m: ChatMessage): ChatMessage => ({ ...m, content: m.content + delta, status: 'streaming' })
      if (target) patchBubble(target.id, apply)
      else addBubble(apply(newBubble(placeholderId(turn_id), turn_id)))
      setActiveTurn(turn_id)
      return
    }
    case 'agent.message_completed': {
      const { turn_id, message_id, text } = event.payload
      const exact = messages.find((m) => m.role === 'agent' && m.id === message_id)
      const holder =
        exact ?? messages.find((m) => m.role === 'agent' && m.id === placeholderId(turn_id)) ?? currentBubble(turn_id)
      const done = (m: ChatMessage): ChatMessage => ({
        ...withoutError(m),
        id: message_id,
        content: text,
        status: 'complete',
        turnId: turn_id
      })
      if (holder) {
        if (holder.status === 'failed') return
        setMessages(messages.map((m) => (m === holder ? done(m) : m)))
      } else {
        addBubble(done(newBubble(message_id, turn_id)))
      }
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
      if (typeof turn_id === 'string') {
        failTurn(turn_id, retryable === true)
      } else {
        notify({
          tone: retryable === true ? 'warning' : 'error',
          title: 'El agente ha tenido un problema',
          body: clean(message, 200) || 'Error no especificado.',
          desktop: retryable !== true
        })
      }
      return
    }
    default:
      return
  }
}

function failTurn(turnId: string, retryable: boolean): void {
  endTurn(turnId)
  const mine = messages.filter((m) => m.role === 'agent' && m.turnId === turnId)
  const open = mine.filter((m) => m.status === 'streaming' || m.status === 'interrupted')
  if (open.length === 0) {
    if (mine.length > 0) return // ya terminó (completa o fallida)
    addBubble({
      ...newBubble(placeholderId(turnId), turnId),
      status: 'failed',
      error: TURN_FAILED,
      retryable
    })
    return
  }
  setMessages(
    messages.map((m): ChatMessage =>
      open.includes(m)
        ? { ...m, status: 'failed', error: TURN_FAILED, retryable, tools: failTools(m.tools) }
        : m
    )
  )
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

/** Tras un resync se relee el historial de la sesión (si hay) y se sustituye la lista. */
async function rehydrate(): Promise<void> {
  const id = sessionId
  if (id === null || rehydrating) return
  rehydrating = true
  try {
    const stored = await listSessionMessages(id)
    const voiceIds = new Set(messages.flatMap((m) => (m.viaVoice ? [m.id] : [])))
    const storedTurns = new Set(stored.flatMap((m) => (m.turn_id ? [m.turn_id] : [])))
    const fromServer: ChatMessage[] = stored
      .filter((m) => m.role !== 'system')
      .map((m) => ({
        id: m.id,
        role: m.role === 'user' ? 'user' : 'agent',
        content: m.text,
        status: STORED_STATUS[m.status],
        turnId: m.turn_id ?? null,
        ...(voiceIds.has(m.id) ? { viaVoice: true } : {}),
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
    console.warn('No se pudo releer el historial del chat.')
  } finally {
    rehydrating = false
  }
}

// Suscripciones: una sola vez, al cargar el módulo.
subscribeServerEvents(handleEvent)
subscribeResync(() => void rehydrate())
subscribeLinkStatus((status) => {
  if (status === 'open') {
    wasOpen = true
    return
  }
  if (!wasOpen) return
  wasOpen = false
  // Enlace perdido: lo que llegaba queda cortado; el resync o el terminal del turno lo aclaran después.
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
    const bubbles = messages.filter((m) => m.role === 'agent' && m.turnId === turnId)
    const settled = bubbles.length > 0 && bubbles.every((m) => m.status !== 'streaming')
    if (!endedTurns.has(turnId) && !settled) setActiveTurn(turnId)
  } catch (error) {
    if (error instanceof ApiError && error.confirmation !== null) {
      // Pide confirmación: no es un fallo del envío. El aviso llega por el store de confirmaciones.
      patchMessage(id, (m) => ({ ...withoutError(m), status: 'complete' }))
      return
    }
    const message = describeError(error, 'No se pudo enviar el mensaje.')
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
  // El terminal real es agent.turn_finished; aquí se cierra ya en local por si tarda.
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
