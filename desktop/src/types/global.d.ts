import type { DrakterBridge } from '../../electron/shared/bridge'

declare global {
  interface Window {
    /** Expuesto por el preload con contextBridge. */
    readonly drakter: DrakterBridge
  }
}
