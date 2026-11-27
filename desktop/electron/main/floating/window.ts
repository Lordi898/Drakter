/** Ventana flotante (CONTRACT §4.1): transparente, sin marco, del tamaño del monitor y 1 px menos de alto. */
import { join } from 'node:path'
import { app, BrowserWindow } from 'electron'
import { FLOATING_URL, FLOATING_WINDOW_TITLE } from '../../shared/floating'
import { describeError, logError } from '../log'
import type { Rect } from './companion'

export function createFloatingWindow(geometry: Rect): BrowserWindow {
  const window = new BrowserWindow({
    title: FLOATING_WINDOW_TITLE,
    width: geometry.w,
    height: Math.max(1, geometry.h - 1),
    transparent: true,
    frame: false,
    hasShadow: false,
    resizable: false,
    fullscreenable: false,
    skipTaskbar: true,
    show: false,
    focusable: true,
    backgroundColor: '#00000000',
    webPreferences: {
      preload: join(__dirname, '../preload/floating.js'),
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false,
      webSecurity: true,
      webviewTag: false,
      devTools: !app.isPackaged,
      spellcheck: false,
      backgroundThrottling: false,
      autoplayPolicy: 'no-user-gesture-required'
    }
  })
  // El título es la regla de casado de la extensión (con el pid): la página no puede cambiarlo.
  window.on('page-title-updated', (event) => event.preventDefault())
  // En desarrollo la consola de la página va al registro de main (la página no tiene log propio).
  if (!app.isPackaged) {
    window.webContents.on('console-message', (event) => logError('floating:page', event.message.slice(0, 2000)))
  }
  window.loadURL(FLOATING_URL).catch((reason: unknown) => {
    logError('floating', 'No se pudo cargar la página flotante', describeError(reason))
  })
  return window
}
