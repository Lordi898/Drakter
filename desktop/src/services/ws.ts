import { clearBackendSession, loadBackendSession } from '@/services/session'
import {
  WS_AUTH_PREFIX,
  WS_SUBPROTOCOL,
  chatEventsPath,
  parseServerEvent,
  type ServerEvent
} from '@/services/protocol'

export type LinkStatus = 'idle' | 'connecting' | 'open' | 'reconnecting'

const PING_INTERVAL_MS = 20_000
const PONG_TIMEOUT_MS = 10_000
const BACKOFF_MIN_MS = 500
const BACKOFF_MAX_MS = 30_000
const MAX_FRAME_CHARS = 1_000_000

const eventListeners = new Set<(event: ServerEvent) => void>()
const statusListeners = new Set<(status: LinkStatus) => void>()

let status: LinkStatus = 'idle'
let started = false
let socket: WebSocket | null = null
let attempt = 0
let everOpened = false
/** Se incrementa en cada conexión nueva y en stop: descarta respuestas de intentos obsoletos. */
let generation = 0
let connecting = false
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let pingTimer: ReturnType<typeof setInterval> | null = null
let pongTimer: ReturnType<typeof setTimeout> | null = null

/** Mayor `seq` visto, solo en memoria. Base de `after_seq` y de la deduplicación. */
let lastSeq: number | null = null
let lastInstance: string | null = null
/** Estado del heartbeat de la conexión actual / de la sesión de backend. */
let pongSeen = false
let pingSent = false
let heartbeatDisabled = false

function setStatus(next: LinkStatus): void {
  if (status === next) return
  status = next
  for (const listener of [...statusListeners]) {
    try {
      listener(next)
    } catch {
      console.warn('Un oyente del estado de conexión falló.')
    }
  }
}

function dispatch(event: ServerEvent): void {
  if (lastSeq !== null && event.seq <= lastSeq) return
  lastSeq = event.seq
  for (const listener of [...eventListeners]) {
    try {
      listener(event)
    } catch {
      console.warn('Un oyente de eventos falló.')
    }
  }
}

function clearHeartbeat(): void {
  if (pingTimer !== null) clearInterval(pingTimer)
  if (pongTimer !== null) clearTimeout(pongTimer)
  pingTimer = null
  pongTimer = null
}

function clearReconnectTimer(): void {
  if (reconnectTimer !== null) clearTimeout(reconnectTimer)
  reconnectTimer = null
}

/** Cierra el socket actual sin que sus manejadores vuelvan a actuar. */
function dropSocket(): void {
  clearHeartbeat()
  const current = socket
  socket = null
  if (!current) return
  current.onopen = null
  current.onmessage = null
  current.onerror = null
  current.onclose = null
  try {
    current.close()
  } catch {
    // ya cerrado
  }
}

function scheduleReconnect(): void {
  if (!started) return
  clearReconnectTimer()
  setStatus('reconnecting')
  const ceiling = Math.min(BACKOFF_MAX_MS, BACKOFF_MIN_MS * 2 ** attempt)
  const delay = ceiling / 2 + Math.random() * (ceiling / 2)
  attempt += 1
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null
    void connect()
  }, delay)
}

/** Fallo o cierre inesperado: el backend pudo reiniciar con otro puerto/token. */
function onLost(): void {
  dropSocket()
  clearBackendSession()
  scheduleReconnect()
}

function startHeartbeat(ws: WebSocket): void {
  clearHeartbeat()
  pongSeen = false
  pingSent = false
  if (heartbeatDisabled) return
  pingTimer = setInterval(() => {
    if (socket !== ws || ws.readyState !== WebSocket.OPEN) return
    try {
      ws.send('ping')
      pingSent = true
    } catch {
      onLost()
      return
    }
    if (pongTimer === null) {
      pongTimer = setTimeout(() => {
        pongTimer = null
        // /chat/events no promete `pong`: solo cuenta si ya se vio uno en esta conexión.
        if (socket === ws && pongSeen) onLost()
      }, PONG_TIMEOUT_MS)
    }
  }, PING_INTERVAL_MS)
}

function handleMessage(data: unknown): void {
  if (typeof data !== 'string') return
  if (data === 'pong') {
    pongSeen = true
    if (pongTimer !== null) clearTimeout(pongTimer)
    pongTimer = null
    return
  }
  if (data.length > MAX_FRAME_CHARS) {
    console.warn('Se descartó un mensaje demasiado grande del backend.')
    return
  }
  let parsed: unknown
  try {
    parsed = JSON.parse(data)
  } catch {
    console.warn('Se descartó un mensaje no válido del backend.')
    return
  }
  const event = parseServerEvent(parsed)
  if (event === null) {
    console.warn('Se descartó un evento desconocido o malformado del backend.')
    return
  }
  dispatch(event)
}

async function connect(): Promise<void> {
  if (!started || connecting || socket) return
  connecting = true
  const myGeneration = ++generation
  setStatus(everOpened || attempt > 0 ? 'reconnecting' : 'connecting')

  let session: Awaited<ReturnType<typeof loadBackendSession>>
  try {
    session = await loadBackendSession()
  } finally {
    connecting = false
  }
  if (!started || myGeneration !== generation) return
  if (!session) {
    scheduleReconnect()
    return
  }

  let ws: WebSocket
  if (lastInstance !== session.instanceId) {
    // Otro backend (reinicio con otro puerto/token): su secuencia no es continuación de la anterior.
    lastInstance = session.instanceId
    lastSeq = null
    heartbeatDisabled = false
  }
  try {
    // El token va solo en el subprotocolo, nunca en la URL.
    ws = new WebSocket(session.wsBase + chatEventsPath(lastSeq), [WS_SUBPROTOCOL, WS_AUTH_PREFIX + session.token])
  } catch {
    onLost()
    return
  }
  socket = ws
  ws.onopen = () => {
    if (socket !== ws) return
    attempt = 0
    everOpened = true
    setStatus('open')
    startHeartbeat(ws)
  }
  ws.onmessage = (message: MessageEvent) => {
    if (socket === ws) handleMessage(message.data)
  }
  ws.onerror = () => {
    // El cierre llega justo después y gestiona la reconexión.
  }
  ws.onclose = (closeEvent: CloseEvent) => {
    if (socket !== ws) return
    if (closeEvent.code === 1003 && pingSent && !pongSeen) heartbeatDisabled = true
    onLost()
  }
}

function onOnline(): void {
  if (!started || status === 'open' || connecting || socket) return
  clearReconnectTimer()
  attempt = 0
  void connect()
}

export function startBackendLink(): void {
  if (started) return
  started = true
  window.addEventListener('online', onOnline)
  void connect()
}

export function stopBackendLink(): void {
  started = false
  generation += 1
  connecting = false
  attempt = 0
  everOpened = false
  lastSeq = null
  lastInstance = null
  clearReconnectTimer()
  dropSocket()
  if (typeof window !== 'undefined') window.removeEventListener('online', onOnline)
  setStatus('idle')
}

export function subscribeServerEvents(listener: (event: ServerEvent) => void): () => void {
  eventListeners.add(listener)
  return () => {
    eventListeners.delete(listener)
  }
}

export function subscribeLinkStatus(listener: (status: LinkStatus) => void): () => void {
  statusListeners.add(listener)
  return () => {
    statusListeners.delete(listener)
  }
}

export function getLinkStatus(): LinkStatus {
  return status
}
