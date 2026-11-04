import { apiRequest } from '@/services/api'

export type SearchEntityType =
  | 'task'
  | 'project'
  | 'habit'
  | 'calendar_event'
  | 'subject'
  | 'resource'

export interface SnippetPart {
  readonly text: string
  readonly match: boolean
}

export interface SearchItem {
  readonly entity_type: SearchEntityType
  readonly entity_id: string
  readonly title: string
  readonly snippet: readonly SnippetPart[]
  readonly trust: 'workspace' | 'untrusted'
}

export interface SearchResponse {
  readonly items: readonly SearchItem[]
  readonly total: number
}

export interface SearchOptions {
  readonly limit?: number
  readonly offset?: number
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

function parseSnippet(value: unknown): readonly SnippetPart[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((part: unknown) =>
    isRecord(part) && typeof part['text'] === 'string'
      ? [{ text: part['text'], match: part['match'] === true }]
      : []
  )
}

/** Lo desconocido se descarta. Sin `trust` explícito, la fila se trata como no confiable. */
function parseItem(value: unknown): readonly SearchItem[] {
  if (!isRecord(value)) return []
  const { entity_type: entityType, entity_id: entityId, title, snippet, trust } = value
  if (typeof entityType !== 'string' || !ENTITY_TYPES.has(entityType)) return []
  if (typeof entityId !== 'string' || typeof title !== 'string') return []
  return [
    {
      entity_type: entityType as SearchEntityType,
      entity_id: entityId,
      title,
      snippet: parseSnippet(snippet),
      trust: trust === 'workspace' ? 'workspace' : 'untrusted'
    }
  ]
}

export async function searchGlobal(
  q: string,
  { limit = 20, offset = 0, types = [] }: SearchOptions = {}
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q, limit: String(limit), offset: String(offset) })
  for (const type of types) params.append('types', type)
  const body = await apiRequest<unknown>(`/api/v1/search?${params.toString()}`)
  const items = isRecord(body) && Array.isArray(body['items']) ? body['items'] : []
  const total = isRecord(body) && typeof body['total'] === 'number' ? body['total'] : items.length
  return { items: items.flatMap(parseItem), total }
}
