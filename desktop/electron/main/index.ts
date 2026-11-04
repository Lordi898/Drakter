import { app, BrowserWindow, Menu, type WebContents } from 'electron'
import { createBackendHost } from './backendProcess'
import { createEventsBridge } from './eventsBridge'
import { registerIpcHandlers } from './ipc'
import { describeError, logError } from './log'
import { applyPermissionPolicy } from './permissions'
import { isTrustedRendererUrl, RENDERER_URL } from './renderer-url'
import { registerRendererProtocol, registerRendererScheme } from './rendererProtocol'
import { applySandboxPolicy } from './sandbox'
import { createMainWindow, focusMainWindow } from './window'

process.on('uncaughtException', (error) => {
  logError('main', 'Excepción no capturada', describeError(error))
})
process.on('unhandledRejection', (reason) => {
  logError('main', 'Promesa rechazada sin gestionar', describeError(reason))
})

applySandboxPolicy()
registerRendererScheme()

function blockUntrustedNavigation(event: { url: string; preventDefault(): void }): void {
  if (!isTrustedRendererUrl(event.url)) event.preventDefault()
}

/** Se aplica a todo WebContents que se cree, no solo al de la ventana principal. */
function hardenWebContents(contents: WebContents): void {
  contents.on('will-navigate', blockUntrustedNavigation)
  contents.on('will-redirect', blockUntrustedNavigation)
  contents.on('will-attach-webview', (event) => event.preventDefault())
  contents.setWindowOpenHandler(() => ({ action: 'deny' }))
}

/** Corta el backend antes de salir: EOF por stdin, y SIGTERM/SIGKILL si no atiende. */
function stopBackendBeforeQuit(stop: () => Promise<void>): void {
  let stopped = false
  app.on('before-quit', (event) => {
    if (stopped) return
    event.preventDefault()
    stopped = true
    stop()
      .catch((reason: unknown) => logError('main', 'Parada del backend fallida', describeError(reason)))
      .finally(() => app.quit())
  })
}

function start(): void {
  app.on('web-contents-created', (_event, contents) => hardenWebContents(contents))
  app.on('child-process-gone', (_event, details) => {
    if (details.reason === 'clean-exit') return
    logError('main', `Proceso ${details.type} caído: ${details.reason} (código ${details.exitCode})`)
  })
  app.on('second-instance', focusMainWindow)
  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit()
  })

  const backend = createBackendHost()
  const events = createEventsBridge(backend)
  stopBackendBeforeQuit(async () => {
    events.dispose()
    await backend.stop()
  })

  void app.whenReady().then(() => {
    // Empaquetada no hay menú por defecto: daría acceso a recargar y a DevTools.
    if (app.isPackaged) Menu.setApplicationMenu(null)
    applyPermissionPolicy()
    if (RENDERER_URL.startsWith('app:')) registerRendererProtocol()
    registerIpcHandlers(backend, events)
    backend.start()
    createMainWindow()
    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) createMainWindow()
    })
  })
}

if (app.requestSingleInstanceLock()) start()
else app.quit()
