/**
 * Acceso al backend para tareas y proyectos. Todo pasa por `WorkspaceTransport`:
 * el renderer no ve el token. El proceso principal aporta el transporte real.
 */
export interface TransportResponse {
  readonly status: number
  readonly body: unknown
}

export interface TransportRequest {
  readonly method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  /** Ruta bajo `/api/v1`, con su query. */
  readonly path: string
  readonly body?: unknown
  readonly headers?: Readonly<Record<string, string>>
}

export interface WorkspaceTransport {
  request(request: TransportRequest): Promise<TransportResponse>
}

export interface ConfirmationTicket {
  readonly id: string
  readonly tool_name: string
  readonly summary: string
  readonly affected_count: number
  readonly expires_at: string
}

interface ErrorEnvelope {
  readonly error?: {
    readonly code?: string
    readonly message?: string
    readonly details?: ReadonlyArray<{ readonly field?: string | null; readonly message: string }>
  }
  readonly confirmation?: ConfirmationTicket
}

export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly fields: ReadonlyArray<{ readonly field?: string | null; readonly message: string }>

  constructor(code: string, message: string, status: number, fields: ApiError['fields'] = []) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.fields = fields
  }
}

/** No es un fallo: la operación espera una aprobación desde la interfaz. */
export class ConfirmationNeeded extends Error {
  readonly ticket: ConfirmationTicket

  constructor(ticket: ConfirmationTicket) {
    super(ticket.summary)
    this.name = 'ConfirmationNeeded'
    this.ticket = ticket
  }
}

let transport: WorkspaceTransport | null = null

/** Lo llama el arranque cuando exista el puente hacia el backend. */
export function configureWorkspaceTransport(next: WorkspaceTransport): void {
  transport = next
}

function currentTransport(): WorkspaceTransport {
  if (transport !== null) return transport
  throw new ApiError(
    'backend_unavailable',
    'La aplicación todavía no está conectada al espacio de trabajo.',
    0
  )
}

export async function api<T>(request: TransportRequest): Promise<T> {
  const response = await currentTransport().request(request)
  if (response.status >= 200 && response.status < 300) return response.body as T
  const envelope = (response.body ?? {}) as ErrorEnvelope
  if (envelope.error?.code === 'confirmation_required' && envelope.confirmation !== undefined) {
    throw new ConfirmationNeeded(envelope.confirmation)
  }
  throw new ApiError(
    envelope.error?.code ?? 'unexpected_error',
    envelope.error?.message ?? 'No se pudo completar la operación.',
    response.status,
    envelope.error?.details ?? []
  )
}

export function ifMatch(revision: number): Readonly<Record<string, string>> {
  return { 'If-Match': `"${revision}"` }
}

export function toQuery(params: Readonly<Record<string, unknown>>): string {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '' || value === false) continue
    if (Array.isArray(value)) {
      for (const item of value) query.append(key, String(item))
    } else {
      query.set(key, String(value))
    }
  }
  const text = query.toString()
  return text === '' ? '' : `?${text}`
}

/** Rutas de `drakter/seguridad`. Solo la interfaz, con su token, puede aprobar. */
export const confirmations = {
  approve: (id: string) => api<unknown>({ method: 'POST', path: `/confirmations/${id}/approve` }),
  reject: (id: string) => api<unknown>({ method: 'POST', path: `/confirmations/${id}/reject` })
}
