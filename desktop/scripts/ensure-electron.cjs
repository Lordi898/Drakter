#!/usr/bin/env node
// Descarga el binario de Electron si falta. Idempotente.
// Electron 45 ya no trae `postinstall` (descarga perezosa al primer arranque), así que
// `npm ci` deja el paquete sin binario; este paso lo cierra en postinstall y desde los scripts.
// Se salta con ELECTRON_SKIP_BINARY_DOWNLOAD=1 (p. ej. en CI, que solo hace typecheck y build).
const { spawnSync } = require('node:child_process')
const { existsSync } = require('node:fs')
const path = require('node:path')

if (process.env.ELECTRON_SKIP_BINARY_DOWNLOAD) process.exit(0)

const installer = path.join(__dirname, '..', 'node_modules', 'electron', 'install.js')
if (!existsSync(installer)) {
  console.error('ensure-electron: falta node_modules/electron (ejecuta `npm ci` en desktop/)')
  process.exit(1)
}
// install.js sale en seguida si el binario ya está instalado.
const r = spawnSync(process.execPath, [installer], { stdio: 'inherit' })
process.exit(r.status ?? 1)
