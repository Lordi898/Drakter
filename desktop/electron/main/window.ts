import { join } from 'node:path'
import { BrowserWindow, dialog } from 'electron'
import { describeError, logError } from './log'
import { RENDERER_URL } from './renderer-url'

const CHASSIS_COLOR = '#0c2747'
const CRASH_LOOP_WINDOW_MS = 30_000
const ERR_ABORTED = -3

let mainWindow: BrowserWindow | null = null

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
      nodeIntegration: false,
      webSecurity: true,
      webviewTag: false,
      allowRunningInsecureContent: false,
      experimentalFeatures: false
    }
  })
  mainWindow = window

  window.once('ready-to-show', () => window.show())
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
