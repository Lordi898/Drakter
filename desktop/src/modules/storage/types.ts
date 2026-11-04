/** Réplica de backend/app/schemas/storage.py. */
export type ResourceType =
  | 'image' | 'document' | 'pdf' | 'text' | 'code' | 'link' | 'note' | 'study_note' | 'archive' | 'other'
export type AvailabilityStatus = 'available' | 'missing' | 'moved' | 'unreachable' | 'forbidden'
export type IndexStatus = 'none' | 'pending' | 'indexed' | 'failed' | 'skipped'

export interface StorageLocation {
  readonly id: string
  readonly path: string
  readonly label: string
  readonly read_only: boolean
  readonly agent_read: boolean
  readonly enabled: boolean
  readonly created_at: string
}

export interface Folder {
  readonly id: string
  readonly name: string
  readonly parent_folder_id: string | null
  readonly resource_count: number
  readonly revision: number
  readonly created_at: string
  readonly updated_at: string
  readonly archived_at: string | null
}

export interface ResourceSummary {
  readonly id: string
  readonly title: string
  readonly resource_type: ResourceType
  readonly folder_id: string | null
  readonly mime_type: string | null
  readonly size_bytes: number | null
  readonly availability_status: AvailabilityStatus
  readonly index_status: IndexStatus
  readonly tags: readonly string[]
  readonly revision: number
  readonly created_at: string
  readonly updated_at: string
  readonly archived_at: string | null
}

export interface Resource extends ResourceSummary {
  readonly location_id: string | null
  readonly relative_path: string | null
  readonly url: string | null
  readonly description: string | null
  readonly content_hash: string | null
  readonly source_modified_at: string | null
  readonly has_note_body: boolean
  readonly index_content: boolean
  readonly index_error_code: string | null
  readonly indexed_at: string | null
}

export interface ResourcePage {
  readonly items: readonly ResourceSummary[]
  readonly next_cursor: string | null
}

export interface SearchHit {
  readonly resource: ResourceSummary
  readonly snippet: string
  readonly content_trust: 'untrusted'
}

export interface SearchPage {
  readonly items: readonly SearchHit[]
  readonly next_cursor: string | null
}

/** `UntrustedEnvelope` de contracts, más la paginación de la lectura. */
export interface ReadResult {
  readonly trust: 'untrusted'
  readonly source_type: string
  readonly source_id: string
  readonly retrieved_at: string
  readonly content_hash: string
  readonly truncated: boolean
  readonly content: string
  readonly title: string
  readonly next_offset: number | null
  readonly metadata: Readonly<Record<string, string | number | boolean | null>>
}

export interface ScanResult {
  readonly location_id: string
  readonly seen: number
  readonly added: number
  readonly updated: number
  readonly missing: number
  readonly moved: number
  readonly skipped: number
  readonly truncated: boolean
}

export interface RefreshResult {
  readonly checked: number
  readonly available: number
  readonly missing: number
  readonly moved: number
  readonly forbidden: number
  readonly reindexed: number
  readonly failed: number
}

export type ResourceCreate =
  | { title: string; note_body: string; folder_id?: string; resource_type: 'note' }
  | { title: string; url: string; folder_id?: string; resource_type: 'link' }
  | { title: string; location_id: string; relative_path: string; folder_id?: string }

export interface ResourceUpdate {
  title?: string
  description?: string
  tags?: string[]
  index_content?: boolean
  expected_revision: number
}

export const TYPE_LABELS: Readonly<Record<ResourceType, string>> = {
  image: 'Imagen', document: 'Documento', pdf: 'PDF', text: 'Texto', code: 'Código',
  link: 'Enlace', note: 'Nota', study_note: 'Apunte', archive: 'Comprimido', other: 'Otro'
}

export const AVAILABILITY_LABELS: Readonly<Record<AvailabilityStatus, string>> = {
  available: 'Disponible', missing: 'No encontrado', moved: 'Movido',
  unreachable: 'Inaccesible', forbidden: 'Acceso denegado'
}

export const INDEX_LABELS: Readonly<Record<IndexStatus, string>> = {
  none: 'Sin indexar', pending: 'Pendiente', indexed: 'Indexado', failed: 'Con error', skipped: 'Omitido'
}
