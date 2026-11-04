/**
 * Ayudas de hábitos, calendario y asignaturas sobre el cliente común. Aquí no hay
 * red ni token: todo pasa por `apiRequest` y `window.api`, y aprobar lo decide el
 * diálogo nativo de main. El renderer solo pide la revisión.
 */
import { ApiError, apiRequest, describeError, type ConfirmationTicket } from '@/services/api'

export { ApiError, type ConfirmationTicket }

export type ReviewOutcome = 'approved' | 'rejected' | 'expired' | 'conflict' | 'failed' | 'unavailable'

export interface Page<T> {
  readonly items: readonly T[]
  readonly total: number
}

export type Query = Readonly<Record<string, string | number | boolean | null | undefined>>
type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

function withQuery(path: string, query?: Query): string {
  if (!query) return path
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value !== null && value !== undefined) params.set(key, String(value))
  }
  const text = params.toString()
  return text ? `${path}?${text}` : path
}

export function api<T>(
  method: Method,
  path: string,
  // `revision` (If-Match) se ignora: `window.api.call` no admite cabeceras todavía.
  options: { readonly query?: Query; readonly body?: unknown; readonly revision?: number } = {}
): Promise<T> {
  return apiRequest<T>(`/api/v1${withQuery(path, options.query)}`, {
    method,
    ...(options.body === undefined ? {} : { body: options.body })
  })
}

/** Un 409 `confirmation_required` no es un fallo: trae lo que hay que revisar. */
export function confirmationOf(error: unknown): ConfirmationTicket | null {
  return error instanceof ApiError && error.code === 'confirmation_required' ? error.confirmation : null
}

export async function reviewConfirmation(id: string): Promise<ReviewOutcome> {
  if (typeof window === 'undefined' || typeof window.api === 'undefined') return 'unavailable'
  try {
    return await window.api.requestApproval(id)
  } catch {
    return 'unavailable'
  }
}

/** Sin sesión o sin respuesta del servicio local: se muestra ese estado, nunca datos falsos. */
export function isBackendUnavailable(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 0 || error.status === 503)
}

export function errorText(error: unknown, fallback = 'No se pudo completar la acción.'): string {
  return describeError(error, fallback)
}
