import type { DrakterApi, DrakterBridge } from '../../electron/shared/bridge'

declare global {
  interface Window {
    /** Servicios de escritorio. Expuesto por el preload con contextBridge. */
    readonly drakter: DrakterBridge
    /** Única interfaz con el backend (D-14). No existe en un navegador normal: comprobar en ejecución. */
    readonly api: DrakterApi
  }
}
