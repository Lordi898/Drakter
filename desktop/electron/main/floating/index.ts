/** Arranque del modo flotante en main: controlador e IPC de las dos ventanas (CONTRACT §4.3, §4.4). */
import { ipcMain, type IpcMainEvent, type IpcMainInvokeEvent } from 'electron'
import { FLOATING_CHANNELS } from '../../shared/bridge'
import { FLOAT_CHANNELS, FLOATING_ACTIONS, type FloatingAction } from '../../shared/floating'
import type { BackendHost } from '../host-types'
import { isTrustedRendererUrl } from '../renderer-url'
import { getMainWindow } from '../window'
import { FloatingController } from './controller'

export { isFloatingEventType } from './adapter'
export type { FloatingController } from './controller'

/** Mismo criterio que `ipc.ts`: marco principal de la ventana principal y documento propio. */
function fromMainWindow(event: IpcMainInvokeEvent | IpcMainEvent): boolean {
  const frame = event.senderFrame
  const contents = getMainWindow()?.webContents
  return (
    frame !== null &&
    contents !== undefined &&
    event.sender.id === contents.id &&
    frame.frameTreeNodeId === contents.mainFrame.frameTreeNodeId &&
    isTrustedRendererUrl(frame.url)
  )
}

function parseSet(payload: unknown): FloatingAction {
  const action = typeof payload === 'object' && payload !== null ? (payload as { action?: unknown }).action : undefined
  if (typeof action !== 'string' || !(FLOATING_ACTIONS as readonly string[]).includes(action)) {
    throw new TypeError('Acción no válida')
  }
  return action as FloatingAction
}

/** Tras `ready` y después de crear la ventana principal. */
export function registerFloating(backend: BackendHost): FloatingController {
  const controller = new FloatingController(backend)
  ipcMain.handle(FLOAT_CHANNELS.invoke, (event, cmd: unknown, args: unknown) => controller.handleInvoke(event, cmd, args))
  ipcMain.handle(FLOATING_CHANNELS.getState, (event) => {
    if (!fromMainWindow(event)) throw new Error('Remitente no autorizado')
    return controller.getState()
  })
  ipcMain.handle(FLOATING_CHANNELS.set, (event, payload: unknown) => {
    if (!fromMainWindow(event)) throw new Error('Remitente no autorizado')
    return controller.set(parseSet(payload), 'ui')
  })
  ipcMain.on(FLOATING_CHANNELS.levels, (event, payload: unknown) => {
    if (fromMainWindow(event)) controller.onLevels(payload)
  })
  controller.start()
  return controller
}

