import { apiRequest } from '@/services/api'
import type {
  Folder, ReadResult, RefreshResult, Resource, ResourceCreate, ResourcePage, ResourceUpdate,
  ScanResult, SearchPage, StorageLocation
} from './types'

export const PAGE_SIZE = 30

type Method = 'GET' | 'POST' | 'PATCH' | 'DELETE'

function backendRequest<T>(method: Method, path: string, body?: unknown): Promise<T> {
  const init = { method, ...(body === undefined ? {} : { body }) }
  return apiRequest<T>(`/api/v1${path}`, init)
}

function query(params: Record<string, string | number | boolean | null | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') search.set(key, String(value))
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}

export const listLocations = () => backendRequest<StorageLocation[]>('GET', '/storage-locations')
export const createLocation = (path: string, label: string) =>
  backendRequest<StorageLocation>('POST', '/storage-locations', { path, label, read_only: true, agent_read: false })
export const updateLocation = (id: string, patch: { agent_read?: boolean; enabled?: boolean }) =>
  backendRequest<StorageLocation>('PATCH', `/storage-locations/${id}`, patch)
export const deleteLocation = (id: string) => backendRequest<void>('DELETE', `/storage-locations/${id}`)
export const scanLocation = (locationId: string) =>
  backendRequest<ScanResult>('POST', '/resources/scan', { location_id: locationId })
export const refreshIndex = () => backendRequest<RefreshResult>('POST', '/resources/refresh-index', {})

export const listFolders = (parentId: string | null) =>
  backendRequest<Folder[]>('GET', `/folders${query({ parent_id: parentId })}`)

export interface ListFilters {
  readonly folderId: string | null
  readonly type: string
  readonly availability: string
  readonly cursor?: string | null
}

export const listResources = (f: ListFilters) =>
  backendRequest<ResourcePage>(
    'GET',
    `/resources${query({
      folder_id: f.folderId, resource_type: f.type, availability: f.availability,
      limit: PAGE_SIZE, cursor: f.cursor
    })}`
  )

export const searchResources = (q: string, type: string, cursor?: string | null) =>
  backendRequest<SearchPage>('GET', `/resources/search${query({ q, type, limit: PAGE_SIZE, cursor })}`)

export const getResource = (id: string) => backendRequest<Resource>('GET', `/resources/${id}`)
export const createResource = (data: ResourceCreate) => backendRequest<Resource>('POST', '/resources', data)
export const updateResource = (id: string, data: ResourceUpdate) =>
  backendRequest<Resource>('PATCH', `/resources/${id}`, data)
export const archiveResource = (id: string) => backendRequest<Resource>('POST', `/resources/${id}/archive`, {})
export const indexResource = (id: string) => backendRequest<Resource>('POST', `/resources/${id}/index`, {})
export const readResource = (id: string, offset: number) =>
  backendRequest<ReadResult>('POST', `/resources/${id}/read`, { offset })
export const deleteResource = (id: string, detach: boolean) =>
  backendRequest<void>('DELETE', `/resources/${id}${query({ detach: detach ? true : undefined })}`)
