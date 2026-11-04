import { BackendError, backendRequest, query } from '@/modules/storage/backend'
import type {
  Direction, EntityType, RelatedItems, RelationshipKind, RelationshipOut,
  RelationshipPage, RelationshipTypeOut
} from './types'

export interface RelationshipFilters {
  readonly relationship_type?: RelationshipKind
  readonly entity_type?: EntityType
  readonly source_id?: string
  readonly target_id?: string
}

export const listRelationshipTypes = () => backendRequest<RelationshipTypeOut[]>('GET', '/relationships/types')

export const searchRelationships = (filters: RelationshipFilters, cursor: string | null, limit = 50) =>
  backendRequest<RelationshipPage>('GET', `/relationships${query({ ...filters, limit, cursor })}`)

export const getRelated = (entityId: string, direction: Direction = 'both', type?: RelationshipKind) =>
  backendRequest<RelatedItems>(
    'GET',
    `/entities/${encodeURIComponent(entityId)}/related${query({ direction, type })}`
  )

export const createRelationship = (data: {
  source_id: string
  target_id: string
  relationship_type: RelationshipKind
}) => backendRequest<RelationshipOut>('POST', '/relationships', data)

export const deleteRelationship = (id: string, confirmationId?: string) =>
  backendRequest<unknown>('DELETE', `/relationships/${encodeURIComponent(id)}${query({ confirmation_id: confirmationId })}`)

const ERROR_TEXT: Record<string, string> = {
  invalid_relationship: 'Esos dos elementos no se pueden vincular con ese tipo de relación.',
  relationship_cycle: 'Esa relación crearía un ciclo: un elemento acabaría dependiendo de sí mismo.',
  duplicate: 'Esa relación ya existe.',
  entity_archived: 'Uno de los dos elementos está archivado. Desarchívalo antes de vincularlo.',
  not_found: 'No se ha encontrado el elemento o la relación.',
  validation_error: 'Revisa los datos: alguno no es válido.',
  confirmation_required: 'La acción espera tu aprobación.'
}

export function humanError(error: unknown): string {
  if (error instanceof BackendError) return ERROR_TEXT[error.code] ?? 'El backend no ha podido completar la acción.'
  return 'No se ha podido conectar con el backend.'
}
