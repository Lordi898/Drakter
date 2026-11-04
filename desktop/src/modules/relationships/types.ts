/** Espejo de `backend/app/schemas/relations.py`. */
export const ENTITY_TYPES = [
  'task', 'project', 'habit', 'calendar_event', 'time_block',
  'subject', 'class_session', 'resource', 'folder'
] as const
export type EntityType = (typeof ENTITY_TYPES)[number]

export const RELATIONSHIP_TYPES = [
  'belongs_to', 'related_to', 'scheduled_for', 'uses_resource', 'depends_on',
  'supports', 'studies', 'parent_of', 'references', 'derived_from'
] as const
export type RelationshipKind = (typeof RELATIONSHIP_TYPES)[number]

export type Direction = 'in' | 'out' | 'both'

export interface RelationshipOut {
  readonly id: string
  readonly source_id: string
  readonly source_type: EntityType
  readonly target_id: string
  readonly target_type: EntityType
  readonly relationship_type: RelationshipKind
  readonly metadata: Record<string, unknown>
  readonly created_at: string
}

export interface RelationshipPage {
  readonly items: readonly RelationshipOut[]
  readonly next_cursor: string | null
}

export interface RelationshipTypeOut {
  readonly relationship_type: RelationshipKind
  readonly label: string
  readonly inverse_label: string
  readonly description: string
  readonly symmetric: boolean
  readonly allowed_pairs: readonly (readonly [EntityType, EntityType])[]
}

export interface RelatedItem {
  readonly relationship_id: string | null
  readonly relationship_type: RelationshipKind
  readonly direction: 'in' | 'out'
  readonly label: string
  readonly entity_id: string
  readonly entity_type: EntityType
  readonly entity_title: string
  readonly archived: boolean
  readonly virtual: boolean
  readonly metadata: Record<string, unknown>
}

export interface RelatedItems {
  readonly entity_id: string
  readonly entity_type: EntityType
  readonly entity_title: string
  readonly items: readonly RelatedItem[]
}

export const ENTITY_TYPE_LABEL: Record<EntityType, string> = {
  task: 'Tarea',
  project: 'Proyecto',
  habit: 'Hábito',
  calendar_event: 'Evento',
  time_block: 'Bloque de tiempo',
  subject: 'Asignatura',
  class_session: 'Clase',
  resource: 'Recurso',
  folder: 'Carpeta'
}

/** Nombres de respaldo mientras no han llegado los tipos del backend. */
export const RELATIONSHIP_FALLBACK_LABEL: Record<RelationshipKind, string> = {
  belongs_to: 'pertenece a',
  related_to: 'relacionado con',
  scheduled_for: 'programado para',
  uses_resource: 'usa el recurso',
  depends_on: 'depende de',
  supports: 'apoya a',
  studies: 'estudia',
  parent_of: 'es padre de',
  references: 'hace referencia a',
  derived_from: 'deriva de'
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
export function isUuid(value: string): boolean {
  return UUID_RE.test(value.trim())
}

export function shortId(id: string): string {
  return id.slice(0, 8)
}
