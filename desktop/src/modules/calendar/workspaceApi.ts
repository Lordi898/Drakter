/**
 * Ayudas de hábitos, calendario y asignaturas sobre el cliente común.
 * Aquí no hay fetch ni token: todo pasa por `apiRequest`, y aprobar lo decide el
 * diálogo nativo de main. El renderer solo pide la revisión.
 */
import { ApiError, apiRequest, describeError, type ApiRequestInit } from '@/services/api'
import { getExtendedBridge, type ReviewOutcome } from '@/services/session'

export { ApiError }

export interface ConfirmationTicket {
  readonly id: string
  readonly summary: string
  readonly affected_count: number | null
  readonly expires_at: string
  readonly params_hash: string
}

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
  options: { readonly query?: Query; readonly body?: unknown; readonly revision?: number } = {}
): Promise<T> {
  const init = {
    method: method as ApiRequestInit['method'],
    ...(options.body === undefined ? {} : { body: options.body }),
    ...(options.revision === undefined ? {} : { headers: { 'If-Match': `"${options.revision}"` } })
  }
  return apiRequest<T>(`/api/v1${withQuery(path, options.query)}`, init)
}

/** Un 409 `confirmation_required` no es un fallo: trae lo que hay que revisar. */
export function confirmationOf(error: unknown): ConfirmationTicket | null {
  if (!(error instanceof ApiError) || error.code !== 'confirmation_required') return null
  const ticket = (error as ApiError & { confirmation?: ConfirmationTicket | null }).confirmation
  return ticket ?? null
}

export async function reviewConfirmation(id: string): Promise<ReviewOutcome> {
  const bridge = getExtendedBridge()
  if (!bridge?.reviewConfirmation) return 'unavailable'
  return (await bridge.reviewConfirmation(id)).outcome
}

/** Sin sesión o sin respuesta del servicio local: se muestra ese estado, nunca datos falsos. */
export function isBackendUnavailable(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 0 || error.status === 401 || error.status === 503)
}

export function errorText(error: unknown, fallback = 'No se pudo completar la acción.'): string {
  return describeError(error, fallback)
}
