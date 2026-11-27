/**
 * Preload de la página flotante (docs/floating/CONTRACT.md §4.3): solo `window.drakterFloat`.
 * Sin red ni acceso al backend; main valida cada comando y cada argumento.
 */
import { contextBridge, ipcRenderer, type IpcRendererEvent } from 'electron'
import {
  FLOAT_CHANNELS,
  FLOAT_CONFIG,
  FLOAT_INVOKE_CMDS,
  FLOAT_PUSH_CHANNELS,
  type DrakterFloat,
  type FloatInvokeCmd,
  type FloatPushChannel
} from '../shared/floating'

const COMMANDS: ReadonlySet<string> = new Set(FLOAT_INVOKE_CMDS)
const PUSH: ReadonlySet<string> = new Set(FLOAT_PUSH_CHANNELS)

function invoke(cmd: FloatInvokeCmd, args: unknown): Promise<unknown> {
  if (typeof cmd !== 'string' || !COMMANDS.has(cmd)) return Promise.reject(new Error('Comando no permitido'))
  return ipcRenderer.invoke(FLOAT_CHANNELS.invoke, cmd, args ?? {})
}

function on(ch: FloatPushChannel, cb: (...a: unknown[]) => void): void {
  if (typeof ch !== 'string' || !PUSH.has(ch) || typeof cb !== 'function') throw new TypeError('Canal no válido')
  ipcRenderer.on(FLOAT_CHANNELS[ch], (_event: IpcRendererEvent, ...args: unknown[]) => {
    try {
      cb(...args)
    } catch (error) {
      console.warn('Un oyente de drakterFloat ha fallado.', error)
    }
  })
}

const api: DrakterFloat = {
  config: FLOAT_CONFIG,
  invoke,
  on
}

contextBridge.exposeInMainWorld('drakterFloat', api)
