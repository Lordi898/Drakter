import { session } from 'electron'
import { isTrustedRendererUrl, RENDERER_ORIGIN } from './renderer-url'

/** Única concesión: micrófono (sin cámara) para el documento propio. Todo lo demás, denegado. */
export function applyPermissionPolicy(): void {
  const ses = session.defaultSession

  ses.setPermissionRequestHandler((_contents, permission, callback, details) => {
    const types = 'mediaTypes' in details ? details.mediaTypes : undefined
    const allowed =
      permission === 'media' &&
      Array.isArray(types) &&
      types.length === 1 &&
      types[0] === 'audio' &&
      isTrustedRendererUrl(details.requestingUrl)
    callback(allowed)
  })

  ses.setPermissionCheckHandler((_contents, permission, requestingOrigin, details) => {
    return (
      permission === 'media' &&
      details.mediaType === 'audio' &&
      requestingOrigin.replace(/\/$/, '') === RENDERER_ORIGIN
    )
  })
}
