import { apiRequest, ApiError } from '@/services/api'
import type {
  Direction, EntityType, RelatedItems, RelationshipKind, RelationshipOut,
  RelationshipPage, RelationshipTypeOut
} from './types'

const BASE = '/api/v1'

function query(params: Record<string, string | number | null | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') search.set(key, String(value))
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}

export interface RelationshipFilters {
  readonly relationship_type?: RelationshipKind
  readonly entity_type?: EntityType
  readonly source_id?: string
  readonly target_id?: string
}

export const listRelationshipTypes = () => apiRequest<RelationshipTypeOut[]>(`${BASE}/relationships/types`)

export const searchRelationships = (filters: RelationshipFilters, cursor: string | null, limit = 50) =>
  apiRequest<RelationshipPage>(`${BASE}/relationships${query({ ...filters, limit, cursor })}`)

export const getRelated = (entityId: string, direction: Direction = 'both', type?: RelationshipKind) =>
  apiRequest<RelatedItems>(
    `${BASE}/entities/${encodeURIComponent(entityId)}/related${query({ direction, type })}`
  )

export const createRelationship = (data: {
  source_id: string
  target_id: string
  relationship_type: RelationshipKind
}) => apiRequest<RelationshipOut>(`${BASE}/relationships`, { method: 'POST', body: data })

export const deleteRelationship = (id: string, confirmationId?: string) =>
  apiRequest<unknown>(`${BASE}/relationships/${encodeURIComponent(id)}${query({ confirmation_id: confirmationId })}`, {
    method: 'DELETE'
  })

const ERROR_TEXT: Record<string, string> = {
  relationship_not_allowed: 'Esos dos elementos no se pueden vincular con ese tipo de relación.',
  hierarchy_cycle: 'Esa relación crearía un ciclo: un elemento acabaría dependiendo de sí mismo.',
  duplicate: 'Esa relación ya existe.',
  entity_archived: 'Uno de los dos elementos está archivado. Desarchívalo antes de vincularlo.',
  not_found: 'No se ha encontrado el elemento o la relación.',
  validation_error: 'Revisa los datos: alguno no es válido.',
  confirmation_required: 'La acción espera tu aprobación.',
  confirmation_unavailable: 'La confirmación de acciones aún no está disponible.',
  permission_denied: 'No tienes permiso para esta acción.'
}

/** Mensaje propio por código; nunca el texto del servidor. */
export function humanError(error: unknown): string {
  if (!(error instanceof ApiError)) return 'No se ha podido completar la acción.'
  if (isDisconnected(error)) return 'Drakter no está conectado al servicio local.'
  if (error.code === 'conflict') {
    const sub = error.details[0]?.code
    if (sub && ERROR_TEXT[sub]) return ERROR_TEXT[sub]
    return 'Esa acción ya no es posible en el estado actual.'
  }
  return ERROR_TEXT[error.code] ?? 'El servicio local no ha podido completar la acción.'
}

export function isDisconnected(error: unknown): boolean {
  return error instanceof ApiError && (error.code === 'no_session' || error.code === 'network')
}

/** Resumen de la confirmación pendiente (409 `confirmation_required`), si el cliente lo trae. */
export function confirmationSummary(error: unknown): string | null {
  const confirmation = (error as { confirmation?: { summary?: unknown } } | null)?.confirmation
  return typeof confirmation?.summary === 'string' ? confirmation.summary.slice(0, 300) : null
}
