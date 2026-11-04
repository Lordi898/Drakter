/**
 * CSP única del renderer. La usan la meta de index.html y la cabecera de `app://`,
 * así que una no puede estrechar a la otra: el navegador aplica la intersección.
 *
 * - `'wasm-unsafe-eval'` solo permite compilar WebAssembly (rive.wasm); `eval` sigue bloqueado.
 * - `connect-src 'self'` solo alcanza archivos propios (rive.wasm, .riv): el renderer
 *   no tiene red hacia el backend, todo pasa por `window.api`.
 * - `style-src 'unsafe-inline'` lo exigen los estilos en tiempo de ejecución de Radix y Sonner.
 */
const DIRECTIVES: readonly string[] = [
  "default-src 'none'",
  "script-src 'self' 'wasm-unsafe-eval'",
  "style-src 'self' 'unsafe-inline'",
  "font-src 'self'",
  "img-src 'self' data: blob:",
  "connect-src 'self'",
  'media-src blob:',
  "base-uri 'none'",
  "form-action 'none'",
  "object-src 'none'"
]

/** Para la meta: `frame-ancestors` no es válido ahí. */
export const RENDERER_CSP = DIRECTIVES.join('; ')

/** Para la cabecera de `app://`. */
export const RENDERER_HEADER_CSP = `${RENDERER_CSP}; frame-ancestors 'none'`

/** Servidor de desarrollo: añade el preámbulo en línea de React Refresh y su WebSocket. */
export const RENDERER_DEV_CSP = RENDERER_CSP.replace(
  "script-src 'self' 'wasm-unsafe-eval'",
  "script-src 'self' 'wasm-unsafe-eval' 'unsafe-inline'"
).replace("connect-src 'self'", "connect-src 'self' ws://localhost:* ws://127.0.0.1:*")
