// Construye el backend con PyInstaller (onedir) para la plataforma actual. No cross-compila.
// Uso: node electron-builder.build-backend.mjs   (desde desktop/)
import { spawnSync } from 'node:child_process'
import { existsSync, rmSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const PYINSTALLER_VERSION = '6.22.3'
const PYTHON_VERSION = '3.12'

const here = dirname(fileURLToPath(import.meta.url))
const backendDir = resolve(here, '..', 'backend')
const specFile = join(here, 'electron-builder.backend.spec')

const osName = { linux: 'linux', win32: 'win' }[process.platform]
if (!osName) {
  console.error(`Plataforma no soportada para empaquetar el backend: ${process.platform}`)
  process.exit(1)
}

const distPath = join(backendDir, 'dist', osName)
const workPath = join(backendDir, 'build', osName)
// Evita empaquetar un build viejo o de otra ejecucion.
rmSync(join(distPath, 'drakter-backend'), { recursive: true, force: true })

const args = [
  'run',
  '--project', backendDir,
  '--frozen',
  '--python', PYTHON_VERSION,
  '--with', `pyinstaller==${PYINSTALLER_VERSION}`,
  'pyinstaller',
  '--noconfirm',
  '--clean',
  '--distpath', distPath,
  '--workpath', workPath,
  specFile
]

const result = spawnSync('uv', args, { stdio: 'inherit', shell: false, cwd: backendDir })

if (result.error) {
  if (result.error.code === 'ENOENT') {
    console.error('No se encontro `uv` en el PATH. Instalalo (https://docs.astral.sh/uv/) y reintenta.')
  } else {
    console.error(`No se pudo ejecutar uv: ${result.error.message}`)
  }
  process.exit(1)
}
if (result.status !== 0) {
  console.error(`PyInstaller fallo (codigo ${result.status ?? result.signal}).`)
  process.exit(result.status ?? 1)
}

const exe = join(distPath, 'drakter-backend', process.platform === 'win32' ? 'drakter-backend.exe' : 'drakter-backend')
if (!existsSync(exe)) {
  console.error(`Build terminado pero falta ${exe}`)
  process.exit(1)
}
console.log(`Backend listo: ${exe}`)
