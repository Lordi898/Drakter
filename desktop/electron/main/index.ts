import { join } from 'node:path'
import { app, BrowserWindow } from 'electron'

// Stub: lo sustituye la pieza del proceso principal.
void app.whenReady().then(() => {
  const window = new BrowserWindow({
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false
    }
  })
  const devUrl = process.env['ELECTRON_RENDERER_URL']
  void (devUrl ? window.loadURL(devUrl) : window.loadFile(join(__dirname, '../renderer/index.html')))
})
