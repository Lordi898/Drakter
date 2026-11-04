import type { BackendState } from '../../electron/shared/bridge'
import { notify } from '@/services/notify'
import { isKnownEventType, parseServerEvent, type ServerEvent } from '@/services/protocol'

/**
 * Enlace con el backend visto desde el renderer. Sin red propia (D-14): todo viene
 * de `window.api.subscribe`. Aquí solo se valida, se ordena por `seq` y se avisa
 * cuando hay que releer el estado por REST (resync).
 */
export type LinkStatus = 'idle' | 'connecting' | 'open' | 'reconnecting' | 'disconnected'

const eventListeners = new Set<(event: ServerEvent) => void>()
const statusListeners = new Set<(status: LinkStatus) => void>()
const resyncListeners = new Set<() => void>()

let status: LinkStatus = 'idle'
let started = false
let unsubscribeEvents: (() => void) | null = null
let unsubscribeConnection: (() => void) | null = null
let lastBoot: string | null = null
let lastSeq: number | null = null
let warnedMalformed = false

function mapState(state: BackendState): LinkStatus {
  switch (state) {
    case 'starting':
      return 'connecting'
    case 'ready':
      return 'open'
    case 'restarting':
      return 'reconnecting'
    default:
      return 'disconnected'
  }
}

function safeEach<T>(listeners: ReadonlySet<(arg: T) => void>, arg: T): void {
  for (const listener of [...listeners]) {
    try {
      listener(arg)
    } catch {
      console.warn('Un oyente del enlace falló.')
    }
  }
}

function emitResync(): void {
  for (const listener of [...resyncListeners]) {
    try {
      listener()
    } catch {
      console.warn('Un oyente de resincronización falló.')
    }
  }
}

function setStatus(next: LinkStatus): void {
  if (status === next) return
  status = next
  safeEach(statusListeners, next)
  if (next === 'open') emitResync()
}

function applyConnection(value: unknown): void {
  if (!started || typeof value !== 'object' || value === null) return
  const state = (value as { state?: unknown }).state
  if (
    state === 'starting' ||
    state === 'ready' ||
    state === 'restarting' ||
    state === 'failed' ||
    state === 'stopped'
  ) {
    setStatus(mapState(state))
  }
}

function handleRaw(raw: unknown): void {
  const event = parseServerEvent(raw)
  if (event === null) {
    const type = typeof raw === 'object' && raw !== null ? (raw as { type?: unknown }).type : undefined
    // Tipos que esta capa no consume: se ignoran en silencio.
    if (typeof type === 'string' && !isKnownEventType(type)) return
    console.warn('Se descartó un evento malformado del backend.')
    if (!warnedMalformed) {
      warnedMalformed = true
      notify({
        tone: 'warning',
        title: 'Evento no válido',
        body: 'El servicio local envió datos que Drakter no entiende. Se han ignorado.'
      })
    }
    return
  }

  let needsResync = false
  if (lastBoot !== null && event.boot_id !== lastBoot) {
    needsResync = true
  } else if (lastSeq !== null && lastBoot === event.boot_id) {
    if (event.seq <= lastSeq) return
    if (event.seq > lastSeq + 1) needsResync = true
  }
  lastBoot = event.boot_id
  lastSeq = event.seq

  safeEach(eventListeners, event)
  if (needsResync || event.type === 'system.resync_required') emitResync()
}

export function startBackendLink(): void {
  if (started) return
  started = true
  const api = typeof window !== 'undefined' ? window.api : undefined
  if (typeof api === 'undefined') {
    setStatus('disconnected') // navegador normal: sin puente, sin ruido
    return
  }
  setStatus('connecting')
  try {
    unsubscribeConnection = api.subscribe('connection', applyConnection)
    unsubscribeEvents = api.subscribe('events', handleRaw)
    void api
      .getConnection()
      .then(applyConnection)
      .catch(() => undefined)
  } catch {
    setStatus('disconnected')
  }
}

/**
 * Vuelve a preguntar a main por el backend. Relanzarlo es cosa de main: esto solo
 * refleja su estado real, y al volver a `ready` el paso a `open` relee por REST.
 */
export async function retryBackendLink(): Promise<void> {
  if (!started) {
    startBackendLink()
    return
  }
  const api = typeof window !== 'undefined' ? window.api : undefined
  if (typeof api === 'undefined') return
  setStatus('connecting')
  try {
    applyConnection(await api.getConnection())
  } catch {
    setStatus('disconnected')
  }
}

export function stopBackendLink(): void {
  started = false
  unsubscribeEvents?.()
  unsubscribeConnection?.()
  unsubscribeEvents = null
  unsubscribeConnection = null
  lastBoot = null
  lastSeq = null
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

/** Se llama al abrir el enlace, ante un hueco de `seq`, un `boot_id` nuevo o `system.resync_required`. */
export function subscribeResync(listener: () => void): () => void {
  resyncListeners.add(listener)
  return () => {
    resyncListeners.delete(listener)
  }
}

export function getLinkStatus(): LinkStatus {
  return status
}
