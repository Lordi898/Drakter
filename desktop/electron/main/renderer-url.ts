import { join } from 'node:path'
import { pathToFileURL } from 'node:url'
import { app } from 'electron'

/** La variable solo se atiende sin empaquetar: en producción nada externo elige qué se carga. */
function resolveRendererUrl(): string {
  const devUrl = app.isPackaged ? undefined : process.env['ELECTRON_RENDERER_URL']
  return devUrl ?? pathToFileURL(join(__dirname, '../renderer/index.html')).href
}

/** Quita consulta y hash. No sirve `URL.origin`: en file:// siempre vale "null". */
function withoutQueryOrHash(url: string): string | null {
  if (!URL.canParse(url)) return null
  const parsed = new URL(url)
  parsed.search = ''
  parsed.hash = ''
  return parsed.href
}

export const RENDERER_URL = resolveRendererUrl()

const trustedDocument = withoutQueryOrHash(RENDERER_URL)

/** Solo el documento propio, comparado por origen y ruta. */
export function isTrustedRendererUrl(url: string): boolean {
  return trustedDocument !== null && withoutQueryOrHash(url) === trustedDocument
}
