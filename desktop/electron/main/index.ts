import { app, BrowserWindow, Menu, session, type WebContents } from 'electron'
import { registerIpcHandlers } from './ipc'
import { describeError, logError } from './log'
import { isTrustedRendererUrl } from './renderer-url'
import { createMainWindow, focusMainWindow } from './window'

process.on('uncaughtException', (error) => {
  logError('main', 'Excepción no capturada', describeError(error))
})
process.on('unhandledRejection', (reason) => {
  logError('main', 'Promesa rechazada sin gestionar', describeError(reason))
})

app.enableSandbox()

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

function denyAllPermissions(): void {
  session.defaultSession.setPermissionRequestHandler((_contents, _permission, callback) => {
    callback(false)
  })
  session.defaultSession.setPermissionCheckHandler(() => false)
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

  void app.whenReady().then(() => {
    // Empaquetada no hay menú por defecto: daría acceso a recargar y a DevTools.
    if (app.isPackaged) Menu.setApplicationMenu(null)
    denyAllPermissions()
    registerIpcHandlers()
    createMainWindow()
    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) createMainWindow()
    })
  })
}

if (app.requestSingleInstanceLock()) start()
else app.quit()
