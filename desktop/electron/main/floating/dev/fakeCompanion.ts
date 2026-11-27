/**
 * Doble de desarrollo de lo nuevo de la API v2 (CONTRACT §3), para trabajar contra el prototipo
 * del spike 02 (Version 1) mientras E1 entrega la extensión definitiva.
 *
 * Solo sin empaquetar y con `DRAKTER_FLOATING_FAKE_COMPANION=1`:
 * - acepta `Version >= 1`;
 * - `SetFloatingFocus(on)` → el foco de la ventana flotante lo pide Electron (`focus`/`blur`);
 * - `Shortcut('ask','press')`: con el gesto `ask/tap` del prototipo o con `SIGUSR2` al proceso main.
 * `ForcePassthrough` y `ActivateWindow` son del helper de manos: main no los usa.
 */
import { app } from 'electron'
import type { CompanionClient } from '../companion'
import { logError } from '../../log'

export interface FakeCompanionHooks {
  /** Pide (o suelta) el foco de teclado para la ventana flotante. */
  focusFloating(on: boolean): boolean
}

export function isFakeCompanionEnabled(): boolean {
  return !app.isPackaged && process.env['DRAKTER_FLOATING_FAKE_COMPANION'] === '1'
}

export function installFakeCompanion(client: CompanionClient, hooks: FakeCompanionHooks): boolean {
  if (!isFakeCompanionEnabled()) return false
  logError('floating:fake', 'Doble de la extensión v2 activo (solo desarrollo)')
  client.minVersion = 1
  client.shim = {
    setFloatingFocus: (on) => Promise.resolve(hooks.focusFloating(on))
  }
  const emitAsk = (tUs: number): void => client.emit('shortcut', 'ask', 'press', tUs)
  client.on('gesture', (name, phase, tUs) => {
    if (name === 'ask' && phase === 'tap') emitAsk(tUs)
  })
  process.on('SIGUSR2', () => emitAsk(Math.round(performance.now() * 1000)))
  return true
}
