/**
 * Transporte de los módulos de almacén y relaciones. El puente aún no expone el
 * backend: cuando el proceso principal publique `backendRequest`, esto funciona
 * sin más cambios. Mientras tanto las pantallas muestran el estado desconectado.
 */
export type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'DELETE'

export interface BackendErrorBody {
  readonly code: string
  readonly message: string
  readonly details?: readonly { field: string | null; code: string; message: string }[]
}

export class BackendUnavailable extends Error {
  constructor() {
    super('El backend no está conectado')
    this.name = 'BackendUnavailable'
  }
}

export class BackendError extends Error {
  readonly code: string
  readonly status: number

  constructor(status: number, body: BackendErrorBody) {
    super(body.message)
    this.name = 'BackendError'
    this.code = body.code
    this.status = status
  }
}

interface BridgeResponse {
  readonly status: number
  readonly body: unknown
}

type BackendBridge = {
  backendRequest?: (request: { method: HttpMethod; path: string; body?: unknown }) => Promise<BridgeResponse>
  pickDirectory?: () => Promise<string | null>
}

function bridge(): BackendBridge {
  return (window.drakter ?? {}) as unknown as BackendBridge
}

export function isBackendAvailable(): boolean {
  return typeof bridge().backendRequest === 'function'
}

/** Selección nativa de carpeta. `null` si el puente aún no la ofrece o se cancela. */
export async function pickDirectory(): Promise<string | null> {
  const pick = bridge().pickDirectory
  return typeof pick === 'function' ? pick() : null
}

export function canPickDirectory(): boolean {
  return typeof bridge().pickDirectory === 'function'
}

export async function backendRequest<T>(method: HttpMethod, path: string, body?: unknown): Promise<T> {
  const request = bridge().backendRequest
  if (typeof request !== 'function') throw new BackendUnavailable()
  const response = await request({ method, path: `/api/v1${path}`, ...(body === undefined ? {} : { body }) })
  if (response.status >= 400) {
    const envelope = response.body as { error?: BackendErrorBody } | null
    throw new BackendError(
      response.status,
      envelope?.error ?? { code: 'unknown_error', message: 'El backend respondió con un error' }
    )
  }
  return response.body as T
}

export function query(params: Record<string, string | number | boolean | null | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') search.set(key, String(value))
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}
