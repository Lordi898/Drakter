import { app } from 'electron'
import { logError } from './log'

/** Solo se tolera sin sandbox en desarrollo y con la variable explícita. */
export function isSandboxDisabled(): boolean {
  return !app.isPackaged && process.env['DRAKTER_DEV_NO_SANDBOX'] === '1'
}

/** Debe llamarse antes de `ready`. */
export function applySandboxPolicy(): void {
  const hasSwitch = app.commandLine.hasSwitch('no-sandbox')

  if (!isSandboxDisabled()) {
    if (hasSwitch) {
      logError('sandbox', '--no-sandbox está prohibido fuera de desarrollo con DRAKTER_DEV_NO_SANDBOX=1')
      app.exit(1)
      return
    }
    app.enableSandbox()
    return
  }

  // appendSwitch en caliente llega tarde (el zygote ya arrancó): lo debe pasar el lanzador en argv.
  if (!hasSwitch) {
    logError('sandbox', 'DRAKTER_DEV_NO_SANDBOX=1 pero falta --no-sandbox en argv: el sandbox seguirá activo')
  }
}
