import { homedir } from 'node:os'
import { realpath } from 'node:fs/promises'
import { extname, join, resolve, sep } from 'node:path'
import { pathToFileURL } from 'node:url'
import { app, net, protocol } from 'electron'
import { RENDERER_HEADER_CSP } from '../shared/csp'
import { FLOATING_HEADER_CSP } from '../shared/floating'
import { describeError, logError } from './log'

const SCHEME = 'app'
const HOST = 'drakter'
/** Página flotante (CONTRACT §4.1): origen propio, CSP propia (§11.6). */
const FLOATING_HOST = 'floating'

const MIME: Record<string, string> = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.wasm': 'application/wasm',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.woff2': 'font/woff2',
  '.riv': 'application/octet-stream'
}

/** Antes de `ready`. */
export function registerRendererScheme(): void {
  protocol.registerSchemesAsPrivileged([
    {
      scheme: SCHEME,
      privileges: { standard: true, secure: true, supportFetchAPI: true, stream: true }
    }
  ])
}

function plain(status: number, text: string): Response {
  return new Response(text, { status, headers: { 'X-Content-Type-Options': 'nosniff' } })
}

/** Devuelve la ruta real dentro de la raíz, o null si no existe o se sale de ella. */
async function resolveInside(root: string, pathname: string): Promise<string | null> {
  let decoded: string
  try {
    decoded = decodeURIComponent(pathname)
  } catch {
    return null
  }
  if (decoded.includes('\0')) return null
  const relative = decoded === '/' ? 'index.html' : decoded.replace(/^\/+/, '')
  const candidate = resolve(root, relative)
  try {
    const real = await realpath(candidate)
    return real.startsWith(root + sep) ? real : null
  } catch {
    return null
  }
}

/** Personaje de Rive del usuario: `DRAKTER_CHARACTER_RIV` o el .riv por defecto (docs/usage/personaje.md). */
const CHARACTER_PATH = '/__character/drakter.riv'
function characterRivPath(): string {
  const configured = process.env['DRAKTER_CHARACTER_RIV']
  if (configured) return resolve(configured)
  const data = process.env['XDG_DATA_HOME'] || join(homedir(), '.local', 'share')
  return join(data, 'drakter', 'character', 'drakter.riv')
}

/** `desktop/floating/` en desarrollo; `resources/floating/` empaquetado. */
function floatingRoot(): string {
  if (app.isPackaged) return join(process.resourcesPath, 'floating')
  // Solo en desarrollo: probar con una página doble (p. ej. la del arnés headless de D2).
  const override = process.env['DRAKTER_FLOATING_ROOT']
  return override ? resolve(override) : join(__dirname, '../../floating')
}

/**
 * Tras `ready`. `serveRenderer`: el host `drakter` solo se sirve si la ventana principal
 * carga de `app://` (en desarrollo viene del servidor de Vite); `floating` siempre.
 */
export function registerRendererProtocol(serveRenderer = true): void {
  const rootPromise = realpath(join(__dirname, '../renderer'))
  // Sin la carpeta (p. ej. aún no copiada) la raíz no existe y todo da 404.
  const floatingPromise = realpath(floatingRoot()).catch(() => null)

  protocol.handle(SCHEME, async (request) => {
    try {
      const url = new URL(request.url)
      const floating = url.host === FLOATING_HOST
      if (!(floating || (serveRenderer && url.host === HOST))) return plain(403, 'Forbidden')
      if (request.method !== 'GET' && request.method !== 'HEAD') return plain(403, 'Forbidden')

      let file: string | null
      if (floating) {
        const root = await floatingPromise
        file = root === null ? null : await resolveInside(root, url.pathname)
      } else if (url.pathname === CHARACTER_PATH) {
        // Ruta fija y no controlada por la petición: solo ese archivo, y solo si es un .riv.
        file = await realpath(characterRivPath()).catch(() => null)
        if (file !== null && extname(file).toLowerCase() !== '.riv') file = null
        // Sin .riv es lo normal (se usa el SVG): 204 en vez de 404, que Chromium anota como error de consola.
        if (file === null) return new Response(null, { status: 204 })
      } else {
        file = await resolveInside(await rootPromise, url.pathname)
      }
      if (file === null) return plain(404, 'Not found')

      const upstream = await net.fetch(pathToFileURL(file).href, { method: request.method })
      if (!upstream.ok) return plain(404, 'Not found')

      const ext = extname(file).toLowerCase()
      const headers = new Headers({
        'Content-Type': MIME[ext] ?? 'application/octet-stream',
        'X-Content-Type-Options': 'nosniff'
      })
      const length = upstream.headers.get('Content-Length')
      if (length) headers.set('Content-Length', length)
      if (ext === '.html') headers.set('Content-Security-Policy', floating ? FLOATING_HEADER_CSP : RENDERER_HEADER_CSP)
      return new Response(request.method === 'HEAD' ? null : upstream.body, { status: 200, headers })
    } catch (reason) {
      logError('protocol', 'Fallo sirviendo el renderer', describeError(reason))
      return plain(500, 'Internal error')
    }
  })
}
