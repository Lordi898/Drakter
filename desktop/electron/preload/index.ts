import { contextBridge, ipcRenderer } from 'electron'
import {
  IPC_CHANNELS,
  type ApiChannel,
  type BackendConnection,
  type DrakterApi,
  type DrakterBridge
} from '../shared/bridge'

type Listener = (event: unknown) => void

const listeners: Record<ApiChannel, Set<Listener>> = { events: new Set(), connection: new Set() }

/** Un oyente que falla no debe dejar sin eventos a los demás. */
function emit(channel: ApiChannel, event: unknown): void {
  for (const listener of [...listeners[channel]]) {
    try {
      listener(event)
    } catch (error) {
      console.warn('Un oyente del puente ha fallado.', error)
    }
  }
}

let eventsRequested = false

/** El puerto se queda en este mundo aislado: la página solo recibe los datos. */
ipcRenderer.on(IPC_CHANNELS.eventsPort, (message) => {
  const port = message.ports[0]
  if (port === undefined) return
  port.onmessage = (frame: MessageEvent) => {
    if (typeof frame.data !== 'string') return
    try {
      emit('events', JSON.parse(frame.data) as unknown)
    } catch {
      console.warn('Se descartó un evento no válido del backend.')
    }
  }
  port.start()
})

ipcRenderer.on(IPC_CHANNELS.connectionChanged, (_message, connection: BackendConnection) => {
  emit('connection', connection)
})

function subscribe(channel: ApiChannel, callback: Listener): () => void {
  if (channel !== 'events' && channel !== 'connection') throw new TypeError('Canal no válido')
  // Cada llamada del mundo principal llega como función nueva: se envuelve una sola vez.
  const listener: Listener = (event) => callback(event)
  listeners[channel].add(listener)
  if (channel === 'events' && !eventsRequested) {
    eventsRequested = true
    void ipcRenderer.invoke(IPC_CHANNELS.openEvents).catch((error: unknown) => {
      eventsRequested = false
      console.warn('No se pudo abrir el canal de eventos.', error)
    })
  }
  return () => {
    listeners[channel].delete(listener)
  }
}

const api: DrakterApi = {
  call: (op, args) => ipcRenderer.invoke(IPC_CHANNELS.apiCall, { op, args }),
  subscribe,
  requestApproval: (actionId) => ipcRenderer.invoke(IPC_CHANNELS.requestApproval, actionId),
  getConnection: () => ipcRenderer.invoke(IPC_CHANNELS.getConnection)
}

const bridge: DrakterBridge = {
  api,
  getAppInfo: () => ipcRenderer.invoke(IPC_CHANNELS.getAppInfo),
  showDesktopNotification: (request) =>
    ipcRenderer.invoke(IPC_CHANNELS.showDesktopNotification, request),
  reportRendererError: (report) => ipcRenderer.invoke(IPC_CHANNELS.reportRendererError, report)
}

contextBridge.exposeInMainWorld('drakter', bridge)
