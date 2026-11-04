/**
 * Único punto de salida a la API de Workspace para hábitos, calendario y
 * asignaturas. Cuando exista el cliente común, solo cambia este archivo.
 *
 * El puente todavía no entrega la sesión del backend: mientras tanto se lanza
 * `BackendUnavailableError` y las pantallas lo muestran tal cual, sin datos falsos.
 */
export interface BackendSession {
  readonly baseUrl: string
  readonly token: string
}

interface SessionBridge {
  getBackendSession?: () => Promise<BackendSession>
}

export class BackendUnavailableError extends Error {
  constructor() {
    super('El espacio de trabajo no está conectado.')
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

/** Lo destructivo no se ejecuta: responde 202 con esto y la GUI pide aprobación. */
export interface ConfirmationRequired {
  readonly status: 'confirmation_required'
  readonly confirmation_id: string
  readonly summary: string
  readonly expires_at: string
  readonly affected_count: number | null
}

export interface Page<T> {
  readonly items: readonly T[]
  readonly next_cursor: string | null
}

async function session(): Promise<BackendSession> {
  const bridge = (typeof window === 'undefined' ? undefined : window.drakter) as SessionBridge | undefined
  if (!bridge?.getBackendSession) throw new BackendUnavailableError()
  return bridge.getBackendSession()
}

export type Query = Readonly<Record<string, string | number | boolean | null | undefined>>

function withQuery(path: string, query?: Query): string {
  if (!query) return path
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value !== null && value !== undefined) params.set(key, String(value))
  }
  const text = params.toString()
  return text ? `${path}?${text}` : path
}

export async function api<T>(
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE',
  path: string,
  options: { readonly query?: Query; readonly body?: unknown; readonly revision?: number } = {}
): Promise<T> {
  const { baseUrl, token } = await session()
  let response: Response
  try {
    response = await fetch(`${baseUrl}/api/v1${withQuery(path, options.query)}`, {
      method,
      headers: {
        Authorization: `Bearer ${token}`,
        ...(options.body === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...(options.revision === undefined ? {} : { 'If-Match': String(options.revision) })
      },
      ...(options.body === undefined ? {} : { body: JSON.stringify(options.body) })
    })
  } catch {
    throw new BackendUnavailableError()
  }
  if (response.status === 204) return undefined as T
  const payload: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const error = (payload as { error?: { code?: string; message?: string } } | null)?.error
    throw new ApiError(response.status, error?.code ?? 'unknown', error?.message ?? 'Error del backend')
  }
  return payload as T
}

/** Aprobación explícita del usuario desde la GUI. El agente no tiene esta vía. */
export function approveConfirmation(id: string): Promise<unknown> {
  return api('POST', `/confirmations/${id}/approve`)
}

export function rejectConfirmation(id: string): Promise<unknown> {
  return api('POST', `/confirmations/${id}/reject`)
}

export function isConfirmationRequired(value: unknown): value is ConfirmationRequired {
  return (value as ConfirmationRequired | null)?.status === 'confirmation_required'
}

export function errorText(error: unknown): string {
  return error instanceof Error ? error.message : 'Error desconocido'
}
