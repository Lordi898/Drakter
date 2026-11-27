/**
 * Bandeja del sistema (voz v2). Con la ventana oculta la voz sigue viva; desde aquí
 * se abre, se activa la conversación, se alterna el micrófono o el modo Jarvis, o se sale de verdad.
 */
import { app, Menu, nativeImage, Tray, type NativeImage } from 'electron'
import { IPC_CHANNELS } from '../shared/bridge'
import { callNamedOperation } from './apiProxy'
import type { BackendHost } from './host-types'
import { logError } from './log'
import { focusMainWindow, getMainWindow, markQuitting } from './window'

const ICON_SIZE = 22
/** Color del chasis de la ventana (#0c2747) con borde claro para verse en paneles oscuros. */
const FILL = [0x47, 0x27, 0x0c, 0xff] as const
const RING = [0xe6, 0xd8, 0xc8, 0xff] as const

let tray: Tray | null = null

/** Círculo dibujado en memoria (BGRA): no hay recursos de icono en el repositorio. */
function drawIcon(): NativeImage {
  const buffer = Buffer.alloc(ICON_SIZE * ICON_SIZE * 4)
  const center = (ICON_SIZE - 1) / 2
  for (let y = 0; y < ICON_SIZE; y++) {
    for (let x = 0; x < ICON_SIZE; x++) {
      const distance = Math.hypot(x - center, y - center)
      const color = distance <= center - 2 ? FILL : distance <= center ? RING : null
      if (color) buffer.set(color, (y * ICON_SIZE + x) * 4)
    }
  }
  return nativeImage.createFromBitmap(buffer, { width: ICON_SIZE, height: ICON_SIZE })
}

export function activateVoice(backend: BackendHost, trigger: 'hotkey' | 'ui'): Promise<void> {
  return callNamedOperation(backend, 'voice.activate', { trigger }).then((result) => {
    if (!result.ok) logError('voice', `No se pudo activar la voz (${result.code})`)
  })
}

/** Lo informa el renderer (`voice:mic-state`); hasta entonces se supone abierto. */
let micOpen = true
let trayBackend: BackendHost | null = null
/** Modo flotante (CONTRACT §4.4): casilla «Modo flotante» → `set('toggle','tray')`. */
let floatingToggle: (() => void) | null = null
let floatingActive = false

function buildMenu(backend: BackendHost): Menu {
  return Menu.buildFromTemplate([
    { label: 'Abrir', click: () => focusMainWindow() },
    { label: 'Activar voz', click: () => void activateVoice(backend, 'ui') },
    {
      label: micOpen ? 'Silenciar micrófono' : 'Activar micrófono',
      click: () => getMainWindow()?.webContents.send(IPC_CHANNELS.voiceMicToggle)
    },
    // Alterna Drakter/Jarvis en el renderer (`ui:mode-toggle`); se muestra la ventana para verlo.
    { label: 'Alternar modo Jarvis', click: () => toggleUiMode() },
    ...(floatingToggle
      ? [{ label: 'Modo flotante', type: 'checkbox' as const, checked: floatingActive, click: () => floatingToggle?.() }]
      : []),
    { type: 'separator' },
    {
      label: 'Salir',
      click: () => {
        markQuitting()
        app.quit()
      }
    }
  ])
}

function toggleUiMode(): void {
  focusMainWindow()
  getMainWindow()?.webContents.send(IPC_CHANNELS.uiModeToggle)
}

export function setTrayMicOpen(open: boolean): void {
  if (open === micOpen) return
  micOpen = open
  if (tray && trayBackend) tray.setContextMenu(buildMenu(trayBackend))
}

export function setTrayFloating(toggle: () => void, active: boolean): void {
  if (floatingToggle === toggle && floatingActive === active) return
  floatingToggle = toggle
  floatingActive = active
  if (tray && trayBackend) tray.setContextMenu(buildMenu(trayBackend))
}

export function createTray(backend: BackendHost): Tray {
  if (tray) return tray
  trayBackend = backend
  tray = new Tray(drawIcon())
  tray.setToolTip('Drakter')
  tray.setContextMenu(buildMenu(backend))
  tray.on('click', () => focusMainWindow())
  return tray
}
