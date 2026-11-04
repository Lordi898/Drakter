import { ERROR_REPORT_LIMITS } from '../../electron/shared/bridge'
import { notify } from '@/services/notify'

const DEBOUNCE_MS = 5000
const recent = new Map<string, number>()
let installed = false

function normalize(error: unknown): { message: string; stack?: string } {
  if (error instanceof Error) {
    return { message: error.message || error.name, ...(error.stack ? { stack: error.stack } : {}) }
  }
  if (typeof error === 'string') return { message: error }
  try {
    return { message: JSON.stringify(error) ?? String(error) }
  } catch {
    return { message: String(error) }
  }
}

function shouldNotify(key: string): boolean {
  const now = Date.now()
  const last = recent.get(key)
  if (last !== undefined && now - last < DEBOUNCE_MS) return false
  recent.set(key, now)
  return true
}

export function reportError(source: string, error: unknown): void {
  try {
    const { message, stack } = normalize(error)
    console.error(source, error)

    const bridge = typeof window !== 'undefined' ? window.drakter : undefined
    if (bridge && typeof bridge.reportRendererError === 'function') {
      bridge
        .reportRendererError({
          source: source.slice(0, ERROR_REPORT_LIMITS.source),
          message: message.slice(0, ERROR_REPORT_LIMITS.message),
          ...(stack ? { stack: stack.slice(0, ERROR_REPORT_LIMITS.stack) } : {})
        })
        .catch(() => undefined)
    }

    if (shouldNotify(`${source}\n${message}`)) {
      notify({
        tone: 'error',
        title: 'Ha ocurrido un error',
        body: `${message.slice(0, 200).replace(/[.!?]?$/, '.')} Si se repite, reinicia Drakter.`
      })
    }
  } catch {
    // Reportar un error nunca debe provocar otro.
  }
}

export function installGlobalErrorHandlers(): void {
  if (installed) return
  installed = true
  window.addEventListener('error', (event) => {
    reportError('ventana', event.error ?? event.message)
  })
  window.addEventListener('unhandledrejection', (event) => {
    reportError('promesa', event.reason)
  })
}
