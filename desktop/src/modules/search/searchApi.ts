import { apiRequest } from '@/services/api'

export type SearchEntityType =
  | 'task'
  | 'project'
  | 'habit'
  | 'calendar_event'
  | 'subject'
  | 'resource'

/** Forma de `SearchHitOut`. Todo resultado es dato no confiable: solo texto plano. */
export interface SearchItem {
  readonly entity_type: SearchEntityType
  readonly entity_id: string
  readonly title: string
  readonly snippet: string
}

export interface SearchResponse {
  readonly items: readonly SearchItem[]
  readonly next_cursor: string | null
}

export interface SearchOptions {
  readonly limit?: number
  readonly cursor?: string
  readonly types?: readonly SearchEntityType[]
}

const ENTITY_TYPES: ReadonlySet<string> = new Set<SearchEntityType>([
  'task',
  'project',
  'habit',
  'calendar_event',
  'subject',
  'resource'
])

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function parseItem(value: unknown): readonly SearchItem[] {
  if (!isRecord(value)) return []
  const { entity_type: entityType, entity_id: entityId, title, snippet } = value
  if (typeof entityType !== 'string' || !ENTITY_TYPES.has(entityType)) return []
  if (typeof entityId !== 'string' || typeof title !== 'string') return []
  return [
    {
      entity_type: entityType as SearchEntityType,
      entity_id: entityId,
      title,
      snippet: typeof snippet === 'string' ? snippet : ''
    }
  ]
}

export async function searchGlobal(
  q: string,
  { limit = 20, cursor, types = [] }: SearchOptions = {}
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q, limit: String(limit) })
  if (cursor) params.set('cursor', cursor)
  for (const type of types) params.append('types', type)
  const body = await apiRequest<unknown>(`/api/v1/search?${params.toString()}`)
  const items = isRecord(body) && Array.isArray(body['items']) ? body['items'] : []
  const nextCursor = isRecord(body) && typeof body['next_cursor'] === 'string' ? body['next_cursor'] : null
  return { items: items.flatMap(parseItem), next_cursor: nextCursor }
}
