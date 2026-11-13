import { MessageChannelMain, type WebContents } from 'electron'
import { IPC_CHANNELS } from '../shared/bridge'
import type { BackendHost, EventsBridge } from './host-types'
import { describeError, logError } from './log'

const SCOPE = 'events-bridge'
const MAX_FRAME_BYTES = 1024 * 1024
const RETRY_MIN_MS = 500
const RETRY_MAX_MS = 30_000
const WS_SUBPROTOCOL = 'drakter.v1'

/** `onEventType`: aviso del tipo de cada evento (p. ej. enfocar ante una confirmación). */
export function createEventsBridge(host: BackendHost, onEventType?: (type: string) => void): EventsBridge {
  let socket: WebSocket | null = null
  let port: Electron.MessagePortMain | null = null
  let retryTimer: NodeJS.Timeout | null = null
  /** Punto de reanudación. Sobrevive a los reinicios: el backend avisa si `boot_id` cambió. */
  let lastSeq: number | null = null
  let lastBootId: string | null = null
  let retryDelay = RETRY_MIN_MS
  let disposed = false

  function closeSocket(): void {
    const current = socket
    socket = null
    if (!current) return
    try {
      current.close()
    } catch {
      // ya cerrado
    }
  }

  function cancelRetry(): void {
    if (retryTimer) clearTimeout(retryTimer)
    retryTimer = null
  }

  function scheduleReconnect(): void {
    if (disposed || host.getEndpoint() === null) return
    cancelRetry()
    retryTimer = setTimeout(() => {
      retryTimer = null
      connect()
    }, retryDelay)
    retryDelay = Math.min(retryDelay * 2, RETRY_MAX_MS)
  }

  function forward(text: string): void {
    if (!port) return
    try {
      port.postMessage(text)
    } catch (error) {
      logError(SCOPE, 'No se pudo enviar el evento al renderer', describeError(error))
    }
  }

  function onFrame(data: unknown): void {
    if (typeof data !== 'string') {
      logError(SCOPE, 'Frame no textual descartado')
      return
    }
    if (Buffer.byteLength(data, 'utf8') > MAX_FRAME_BYTES) {
      logError(SCOPE, 'Frame por encima de 1 MiB descartado')
      return
    }
    rememberPosition(data)
    forward(data)
  }

  /** Solo lee `seq`, `boot_id` y `type`; el renderer sigue validando el evento. */
  function rememberPosition(text: string): void {
    try {
      const envelope = JSON.parse(text) as { seq?: unknown; boot_id?: unknown; type?: unknown }
      if (onEventType && typeof envelope.type === 'string') onEventType(envelope.type)
      if (typeof envelope.boot_id !== 'string' || !Number.isSafeInteger(envelope.seq)) return
      lastSeq = envelope.seq as number
      lastBootId = envelope.boot_id
    } catch {
      // No es un sobre: se reenvía igual y el renderer lo descarta.
    }
  }

  function eventsUrl(port: number): string {
    const query = new URLSearchParams()
    if (lastSeq !== null && lastBootId !== null) {
      query.set('after_seq', String(lastSeq))
      query.set('boot_id', lastBootId)
    }
    const suffix = query.size > 0 ? `?${query}` : ''
    return `ws://127.0.0.1:${port}/api/v1/events${suffix}`
  }

  function connect(): void {
    if (disposed) return
    const endpoint = host.getEndpoint()
    if (!endpoint) return
    closeSocket()
    cancelRetry()

    let ws: WebSocket
    try {
      // El WebSocket de Node admite `headers`; el tipado DOM no lo declara.
      ws = new WebSocket(eventsUrl(endpoint.port), {
        protocols: [WS_SUBPROTOCOL],
        headers: { Authorization: `Bearer ${endpoint.uiToken}` },
      } as never)
    } catch (error) {
      logError(SCOPE, 'No se pudo abrir el WebSocket', describeError(error))
      scheduleReconnect()
      return
    }
    socket = ws

    ws.addEventListener('open', () => {
      if (socket !== ws) return
      retryDelay = RETRY_MIN_MS
    })
    ws.addEventListener('message', (event: MessageEvent) => {
      // Canal solo servidor→cliente: main no envía frames. Los pings son de protocolo.
      if (socket === ws) onFrame(event.data)
    })
    ws.addEventListener('error', () => {
      // El detalle puede incluir la URL; 'close' gestiona el reintento.
      if (socket === ws) logError(SCOPE, 'Error del WebSocket')
    })
    ws.addEventListener('close', () => {
      if (socket !== ws) return
      closeSocket()
      scheduleReconnect()
    })
  }

  function onConnection(connection: { readonly state: string }): void {
    if (disposed) return
    if (connection.state === 'ready') {
      retryDelay = RETRY_MIN_MS
      connect()
    } else {
      cancelRetry()
      closeSocket()
    }
  }

  function closePort(): void {
    const current = port
    port = null
    if (!current) return
    try {
      current.close()
    } catch {
      // ya cerrado
    }
  }

  const unsubscribe = host.onConnection(onConnection)
  if (host.getEndpoint()) connect()

  return {
    attach(contents: WebContents): void {
      if (disposed || contents.isDestroyed()) return
      closePort()
      const { port1, port2 } = new MessageChannelMain()
      port = port1
      port1.start()
      contents.postMessage(IPC_CHANNELS.eventsPort, null, [port2])
      contents.once('destroyed', () => {
        if (port === port1) closePort()
        else {
          try {
            port1.close()
          } catch {
            // ya cerrado
          }
        }
      })
    },
    dispose(): void {
      if (disposed) return
      disposed = true
      unsubscribe()
      cancelRetry()
      closeSocket()
      closePort()
    },
  }
}
