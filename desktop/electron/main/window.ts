import { join } from 'node:path'
import { app, BrowserWindow, dialog } from 'electron'
import { describeError, logError } from './log'
import { RENDERER_URL } from './renderer-url'
import { isSandboxDisabled } from './sandbox'

const CHASSIS_COLOR = '#0c2747'
const CRASH_LOOP_WINDOW_MS = 30_000
const ERR_ABORTED = -3

let mainWindow: BrowserWindow | null = null
/** Solo una salida explícita (Salir de la bandeja, señal, `app.quit`) cierra la ventana. */
let quitting = false

export function markQuitting(): void {
  quitting = true
}

export function getMainWindow(): BrowserWindow | null {
  return mainWindow
}

/** Sin esto, un fallo antes de ready-to-show dejaría la aplicación viva y sin ventana. */
function showFailure(window: BrowserWindow, title: string, content: string): void {
  if (!window.isDestroyed() && !window.isVisible()) window.show()
  dialog.showErrorBox(title, content)
}

function watchRendererFailures(window: BrowserWindow): void {
  let lastReloadAt: number | null = null

  window.webContents.on('render-process-gone', (_event, details) => {
    if (details.reason === 'clean-exit') return
    logError('renderer', `Proceso caído: ${details.reason} (código ${details.exitCode})`)
    if (window.isDestroyed()) return

    const now = performance.now()
    if (lastReloadAt !== null && now - lastReloadAt < CRASH_LOOP_WINDOW_MS) {
      showFailure(
        window,
        'Drakter ha dejado de responder',
        'La ventana ha fallado dos veces en menos de 30 segundos. Cierra Drakter y vuelve a abrirlo.'
      )
      return
    }
    lastReloadAt = now
    window.webContents.reload()
  })

  window.webContents.on(
    'did-fail-load',
    (_event, errorCode, errorDescription, _validatedUrl, isMainFrame) => {
      if (!isMainFrame || errorCode === ERR_ABORTED) return
      logError('renderer', `Carga fallida: ${errorDescription} (código ${errorCode})`)
      showFailure(
        window,
        'Drakter no ha podido abrir su ventana',
        `La interfaz no se ha cargado (${errorDescription}). Cierra Drakter y vuelve a abrirlo.`
      )
    }
  )
}

export function createMainWindow(): BrowserWindow {
  const window = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 980,
    minHeight: 640,
    title: 'Drakter',
    backgroundColor: CHASSIS_COLOR,
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      sandbox: true,
      devTools: !app.isPackaged,
      nodeIntegration: false,
      webSecurity: true,
      webviewTag: false,
      allowRunningInsecureContent: false,
      experimentalFeatures: false,
      // Voz v2: con la ventana oculta en la bandeja el micrófono y el audio siguen vivos.
      backgroundThrottling: false,
      autoplayPolicy: 'no-user-gesture-required'
    }
  })
  mainWindow = window

  if (isSandboxDisabled()) {
    const warningTitle = 'Drakter — SIN SANDBOX (desarrollo)'
    window.setTitle(warningTitle)
    window.on('page-title-updated', (event) => event.preventDefault())
  }

  window.once('ready-to-show', () => window.show())
  // Cerrar oculta en la bandeja: la voz sigue escuchando hasta que se sale de verdad.
  window.on('close', (event) => {
    if (quitting) return
    event.preventDefault()
    window.hide()
  })
  window.on('closed', () => {
    if (mainWindow === window) mainWindow = null
  })
  watchRendererFailures(window)

  window.loadURL(RENDERER_URL).catch((reason: unknown) => {
    logError('main', 'No se ha podido iniciar la carga de la ventana', describeError(reason))
  })
  return window
}

export function focusMainWindow(): void {
  const window = mainWindow ?? createMainWindow()
  if (window.isMinimized()) window.restore()
  window.show()
  window.focus()
}
