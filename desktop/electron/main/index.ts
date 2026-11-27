import { app, BrowserWindow, Menu, type WebContents } from 'electron'
import { createBackendHost } from './backendProcess'
import { createEventsBridge } from './eventsBridge'
import { isFloatingEventType, registerFloating, type FloatingController } from './floating'
import { registerIpcHandlers } from './ipc'
import { describeError, logError } from './log'
import { applyPermissionPolicy } from './permissions'
import { isTrustedRendererUrl, RENDERER_URL } from './renderer-url'
import { registerRendererProtocol, registerRendererScheme } from './rendererProtocol'
import { applySandboxPolicy } from './sandbox'
import { activateVoice, createTray, setTrayFloating } from './tray'
import { createMainWindow, focusMainWindow, markQuitting } from './window'

process.on('uncaughtException', (error) => {
  logError('main', 'Excepción no capturada', describeError(error))
})
process.on('unhandledRejection', (reason) => {
  logError('main', 'Promesa rechazada sin gestionar', describeError(reason))
})

const ACTIVATE_ARG = 'activate'

// Voz v2: WebRTC con voice/ en 127.0.0.1. La vía probada (WP8a) es el argv (scripts/drakter,
// `npm run dev`/`start`); esto es el respaldo para arranques sin lanzador, antes de `ready`.
if (!app.commandLine.hasSwitch('allow-loopback-in-peer-connection')) {
  app.commandLine.appendSwitch('allow-loopback-in-peer-connection')
}
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
  // Primero: cualquier salida (bandeja, señal, app.quit) deja cerrar la ventana de verdad.
  app.on('before-quit', markQuitting)
  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit()
  })

  const backend = createBackendHost()
  // `drakter activate` (atajo Super+J) llega como segunda instancia: activa la voz sin enfocar.
  app.on('second-instance', (_event, argv) => {
    if (argv.includes(ACTIVATE_ARG)) void activateVoice(backend, 'hotkey')
    else focusMainWindow()
  })
  // Modo flotante (CONTRACT §4.2): se crea tras `ready`; hasta entonces no hay eventos que darle.
  let floating: FloatingController | null = null
  // Las confirmaciones nunca se hacen por voz (V-34): se enfoca la ventana para decidir en pantalla.
  // Con el modo flotante activo, main abre él mismo el diálogo nativo sin padre (la principal sigue oculta).
  const events = createEventsBridge(backend, (envelope) => {
    const floatingActive = floating?.getState().active === true
    if (envelope.type === 'confirmation.requested' && !floatingActive) focusMainWindow()
    if (floating && isFloatingEventType(envelope.type)) floating.onEvent(envelope)
  })
  stopBackendBeforeQuit(async () => {
    events.dispose()
    floating?.dispose()
    await backend.stop()
  })

  void app.whenReady().then(() => {
    // Empaquetada no hay menú por defecto: daría acceso a recargar y a DevTools.
    if (app.isPackaged) Menu.setApplicationMenu(null)
    applyPermissionPolicy()
    registerRendererProtocol(RENDERER_URL.startsWith('app:'))
    registerIpcHandlers(backend, events)
    backend.start()
    createMainWindow()
    createTray(backend)
    const controller = registerFloating(backend)
    floating = controller
    const toggleFloating = (): void => void controller.set('toggle', 'tray')
    setTrayFloating(toggleFloating, false)
    controller.onState((state) => setTrayFloating(toggleFloating, state.active))
    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) createMainWindow()
    })
  })
}

if (app.requestSingleInstanceLock()) start()
else app.quit()
