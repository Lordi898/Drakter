import { app, ipcMain, Notification, type IpcMainInvokeEvent } from 'electron'
import {
  DESKTOP_NOTIFICATION_LIMITS,
  ERROR_REPORT_LIMITS,
  IPC_CHANNELS,
  type AppInfo,
  type DesktopNotificationRequest,
  type RendererErrorReport
} from '../shared/bridge'
import { logError } from './log'
import { isTrustedRendererUrl } from './renderer-url'
import { getMainWindow } from './window'

function assertTrustedSender(event: IpcMainInvokeEvent): void {
  const frame = event.senderFrame
  const contents = getMainWindow()?.webContents
  const isMainFrame =
    frame !== null &&
    contents !== undefined &&
    event.sender.id === contents.id &&
    frame.frameTreeNodeId === contents.mainFrame.frameTreeNodeId
  if (!isMainFrame || !isTrustedRendererUrl(frame.url)) {
    throw new Error('Remitente no autorizado')
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/** Recorta sin dejar medio carácter si el corte cae dentro de un par sustituto. */
function clip(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  const lastKept = text.charCodeAt(maxLength - 1)
  const splitsPair = lastKept >= 0xd800 && lastKept <= 0xdbff
  return text.slice(0, splitsPair ? maxLength - 1 : maxLength)
}

function requireString(value: unknown, field: string): string {
  if (typeof value !== 'string') throw new TypeError(`Campo no válido: ${field}`)
  return value
}

function optionalString(value: unknown, field: string): string | undefined {
  return value === undefined ? undefined : requireString(value, field)
}

function parseNotification(payload: unknown): DesktopNotificationRequest {
  if (!isRecord(payload)) throw new TypeError('Notificación no válida')
  const title = clip(requireString(payload['title'], 'title'), DESKTOP_NOTIFICATION_LIMITS.title)
  if (title.trim() === '') throw new TypeError('Campo no válido: title')
  const body = optionalString(payload['body'], 'body')
  if (body === undefined) return { title }
  return { title, body: clip(body, DESKTOP_NOTIFICATION_LIMITS.body) }
}

function parseErrorReport(payload: unknown): RendererErrorReport {
  if (!isRecord(payload)) throw new TypeError('Informe de error no válido')
  const source = clip(requireString(payload['source'], 'source'), ERROR_REPORT_LIMITS.source)
  const message = clip(requireString(payload['message'], 'message'), ERROR_REPORT_LIMITS.message)
  const stack = optionalString(payload['stack'], 'stack')
  if (stack === undefined) return { source, message }
  return { source, message, stack: clip(stack, ERROR_REPORT_LIMITS.stack) }
}

function getAppInfo(): AppInfo {
  return {
    appVersion: app.getVersion(),
    electronVersion: process.versions.electron,
    chromeVersion: process.versions.chrome,
    nodeVersion: process.versions.node,
    platform: process.platform,
    packaged: app.isPackaged
  }
}

function showDesktopNotification(payload: unknown): void {
  const request = parseNotification(payload)
  if (Notification.isSupported()) new Notification(request).show()
}

function reportRendererError(payload: unknown): void {
  const report = parseErrorReport(payload)
  logError(`renderer:${report.source}`, report.message, report.stack)
}

function handle<T>(channel: string, listener: (payload: unknown) => T): void {
  ipcMain.handle(channel, (event, payload: unknown) => {
    assertTrustedSender(event)
    return listener(payload)
  })
}

export function registerIpcHandlers(): void {
  handle(IPC_CHANNELS.getAppInfo, getAppInfo)
  handle(IPC_CHANNELS.showDesktopNotification, showDesktopNotification)
  handle(IPC_CHANNELS.reportRendererError, reportRendererError)
}
