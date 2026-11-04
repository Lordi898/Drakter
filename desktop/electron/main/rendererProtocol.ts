import { realpath } from 'node:fs/promises'
import { extname, join, resolve, sep } from 'node:path'
import { pathToFileURL } from 'node:url'
import { net, protocol } from 'electron'
import { describeError, logError } from './log'

const SCHEME = 'app'
const HOST = 'drakter'

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

// connect-src 'self' solo alcanza app://drakter (p. ej. rive.wasm): el renderer no tiene red hacia el backend.
const CSP = [
  "default-src 'none'",
  "script-src 'self' 'wasm-unsafe-eval'",
  "style-src 'self' 'unsafe-inline'",
  "font-src 'self'",
  "img-src 'self' data: blob:",
  "connect-src 'self'",
  'media-src blob:',
  "base-uri 'none'",
  "form-action 'none'",
  "object-src 'none'",
  "frame-ancestors 'none'"
].join('; ')

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

/** Tras `ready`. */
export function registerRendererProtocol(): void {
  const rootPromise = realpath(join(__dirname, '../renderer'))

  protocol.handle(SCHEME, async (request) => {
    try {
      const url = new URL(request.url)
      if (url.host !== HOST) return plain(403, 'Forbidden')
      if (request.method !== 'GET' && request.method !== 'HEAD') return plain(403, 'Forbidden')

      const root = await rootPromise
      const file = await resolveInside(root, url.pathname)
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
      if (ext === '.html') headers.set('Content-Security-Policy', CSP)
      return new Response(request.method === 'HEAD' ? null : upstream.body, { status: 200, headers })
    } catch (reason) {
      logError('protocol', 'Fallo sirviendo el renderer', describeError(reason))
      return plain(500, 'Internal error')
    }
  })
}
