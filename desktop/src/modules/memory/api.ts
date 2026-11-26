import { backend, queryString, runConfirmable } from '../remote'
import type {
  ForgetReport,
  MemoryBackendStatus,
  MemoryConflict,
  MemoryHit,
  MemoryKind,
  MemoryCategory,
  MemoryListParams,
  MemoryPage,
  MemoryRecord
} from './types'

function listQuery(p: MemoryListParams): string {
  const search = new URLSearchParams()
  for (const s of p.statuses ?? []) search.append('statuses', s)
  for (const k of p.kinds ?? []) search.append('kinds', k)
  for (const c of p.categories ?? []) search.append('categories', c)
  if (p.limit !== undefined) search.set('limit', String(p.limit))
  if (p.offset !== undefined) search.set('offset', String(p.offset))
  const text = search.toString()
  return text ? `?${text}` : ''
}

export const listMemories = (params: MemoryListParams = {}) =>
  backend<MemoryPage>('GET', `/memory${listQuery(params)}`)

export const getMemoryStatus = () => backend<MemoryBackendStatus>('GET', '/memory/status')

export const searchMemories = (
  text: string,
  filters: { readonly kinds?: readonly MemoryKind[]; readonly categories?: readonly MemoryCategory[]; readonly limit?: number } = {}
) => backend<readonly MemoryHit[]>('POST', '/memory/search', { text, ...filters })

export const getMemory = (id: string) => backend<MemoryRecord>('GET', `/memory/${id}`)

export const listConflicts = (openOnly = true) =>
  backend<readonly MemoryConflict[]>('GET', `/memory/conflicts${queryString({ open_only: openOnly })}`)

export const resolveConflict = (id: string, kept: string | null) =>
  backend<MemoryConflict>('POST', `/memory/conflicts/${id}/resolve`, { kept })

export const rejectMemory = (id: string) => backend<MemoryRecord>('POST', `/memory/${id}/reject`, {})

/** Aprobar y olvidar son confirmables: el backend responde 409 y la decisión la toma el diálogo nativo. */
export const approveMemory = (id: string) =>
  runConfirmable(() => backend<MemoryRecord>('POST', `/memory/${id}/approve`, {}))

export const forgetMemory = (id: string) =>
  runConfirmable(() => backend<ForgetReport>('POST', `/memory/${id}/forget`, {}))
