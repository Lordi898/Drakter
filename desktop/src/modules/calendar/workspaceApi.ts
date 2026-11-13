/**
 * Ayudas de hábitos, calendario y asignaturas sobre el cliente común. Aquí no hay
 * red ni token: todo pasa por `apiRequest` y `window.api`, y aprobar lo decide el
 * diálogo nativo de main. El renderer solo pide la revisión.
 */
import { ApiError, apiRequest, describeError, type ConfirmationTicket } from '@/services/api'
import { reviewConfirmation as reviewInMain, type ReviewOutcome, type TrustedGesture } from '@/stores/confirmations'

export { ApiError, type ConfirmationTicket, type ReviewOutcome, type TrustedGesture }

export interface Page<T> {
  readonly items: readonly T[]
  readonly next_cursor: string | null
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
  // `revision` va en If-Match; llega al backend cuando se integre el puente de main.
  options: { readonly query?: Query; readonly body?: unknown; readonly revision?: number } = {}
): Promise<T> {
  return apiRequest<T>(`/api/v1${withQuery(path, options.query)}`, {
    method,
    ...(options.body === undefined ? {} : { body: options.body }),
    ...(options.revision === undefined ? {} : { headers: { 'If-Match': `"${options.revision}"` } })
  })
}

/** Un 409 `confirmation_required` no es un fallo: trae lo que hay que revisar. */
export function confirmationOf(error: unknown): ConfirmationTicket | null {
  return error instanceof ApiError && error.code === 'confirmation_required' ? error.confirmation : null
}

/** `proof` es el evento del clic del usuario: sin gesto real no se abre el diálogo nativo. */
export function reviewConfirmation(id: string, proof: TrustedGesture): Promise<ReviewOutcome> {
  return reviewInMain(id, proof)
}

/** Sin sesión o sin respuesta del servicio local: se muestra ese estado, nunca datos falsos. */
export function isBackendUnavailable(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 0 || error.status === 503)
}

export function errorText(error: unknown, fallback = 'No se pudo completar la acción.'): string {
  return describeError(error, fallback)
}

/** Recorre todas las páginas de un listado por cursor. */
export async function listAll<T>(path: string, query: Query = {}): Promise<readonly T[]> {
  const items: T[] = []
  let cursor: string | null = null
  do {
    const page: Page<T> = await api<Page<T>>('GET', path, { query: { ...query, limit: 200, cursor } })
    items.push(...page.items)
    cursor = page.next_cursor
  } while (cursor !== null)
  return items
}
