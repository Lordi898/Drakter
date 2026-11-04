import { app } from 'electron'

/** La variable solo se atiende sin empaquetar: en producción nada externo elige qué se carga. */
function resolveRendererUrl(): string {
  const devUrl = app.isPackaged ? undefined : process.env['ELECTRON_RENDERER_URL']
  return devUrl ?? 'app://drakter/index.html'
}

/** Quita consulta y hash. No sirve `URL.origin`: en esquemas no especiales siempre vale "null". */
function withoutQueryOrHash(url: string): string | null {
  if (!URL.canParse(url)) return null
  const parsed = new URL(url)
  parsed.search = ''
  parsed.hash = ''
  return parsed.href
}

export const RENDERER_URL = resolveRendererUrl()

const trustedDocument = withoutQueryOrHash(RENDERER_URL)

/** Origen del renderer, construido a mano por la misma razón que arriba. */
export const RENDERER_ORIGIN: string = (() => {
  const parsed = new URL(RENDERER_URL)
  return `${parsed.protocol}//${parsed.host}`
})()

/** Solo el documento propio, comparado por origen y ruta. */
export function isTrustedRendererUrl(url: string): boolean {
  return trustedDocument !== null && withoutQueryOrHash(url) === trustedDocument
}
