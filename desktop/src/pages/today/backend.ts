/**
 * Único punto de salida a la API para Hoy y Ajustes. Cuando el puente real de
 * `drakter/electron-host` y el cliente común estén integrados, solo cambia este archivo.
 *
 * Sin puente no se inventa nada: se lanza `BackendUnavailableError` y la pantalla lo muestra.
 * El token vive solo durante la llamada: no se guarda aquí ni en ningún store.
 * Los mensajes del servidor no se muestran: son datos, y la interfaz usa textos propios.
 */
const TIMEOUT_MS = 10_000
const HOST = '127.0.0.1'

interface RawSession {
  readonly port?: unknown
  readonly baseUrl?: unknown
  readonly token?: unknown
}

interface SessionBridge {
  getBackendSession?: () => Promise<RawSession | null>
}

export class BackendUnavailableError extends Error {
  constructor() {
    super('El servicio local de Drakter no está conectado.')
    this.name = 'BackendUnavailableError'
  }
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

function resolveBase(raw: RawSession): string | null {
  if (typeof raw.port === 'number' && Number.isInteger(raw.port)) return `http://${HOST}:${raw.port}`
  if (typeof raw.baseUrl !== 'string') return null
  try {
    const url = new URL(raw.baseUrl)
    return url.protocol === 'http:' && url.hostname === HOST ? url.origin : null
  } catch {
    return null
  }
}

async function session(): Promise<{ baseUrl: string; token: string }> {
  const bridge = (typeof window === 'undefined' ? undefined : window.drakter) as SessionBridge | undefined
  if (!bridge?.getBackendSession) throw new BackendUnavailableError()
  const raw = await bridge.getBackendSession().catch(() => null)
  const baseUrl = raw ? resolveBase(raw) : null
  if (!raw || !baseUrl || typeof raw.token !== 'string') throw new BackendUnavailableError()
  return { baseUrl, token: raw.token }
}

function messageFor(status: number): string {
  if (status === 404) return 'Esta función aún no está disponible en el servicio local.'
  if (status === 422) return 'El valor no es válido.'
  if (status === 503) return 'El servicio local no puede guardar esto todavía.'
  return 'El servicio local no ha podido completar la solicitud.'
}

export async function api<T>(
  method: 'GET' | 'POST' | 'PUT',
  path: string,
  options: { readonly query?: Readonly<Record<string, string>>; readonly body?: unknown } = {}
): Promise<T> {
  const { baseUrl, token } = await session()
  const search = options.query ? `?${new URLSearchParams(options.query).toString()}` : ''
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)
  let response: Response
  try {
    response = await fetch(`${baseUrl}/api/v1${path}${search}`, {
      method,
      headers: {
        Authorization: `Bearer ${token}`,
        ...(options.body === undefined ? {} : { 'Content-Type': 'application/json' })
      },
      ...(options.body === undefined ? {} : { body: JSON.stringify(options.body) }),
      signal: controller.signal,
      credentials: 'omit',
      cache: 'no-store',
      redirect: 'error'
    })
  } catch {
    throw new BackendUnavailableError()
  } finally {
    clearTimeout(timer)
  }
  const payload: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const code = (payload as { error?: { code?: unknown } } | null)?.error?.code
    throw new ApiError(response.status, typeof code === 'string' ? code : 'unknown', messageFor(response.status))
  }
  return payload as T
}

export function errorText(error: unknown): string {
  return error instanceof Error ? error.message : 'Ha ocurrido un error inesperado.'
}
