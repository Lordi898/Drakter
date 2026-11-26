export interface ExcludedItem {
  readonly what: string
  readonly reason: string
}

export interface BundleInfo {
  readonly name: string
  readonly label: string
  readonly created_at: string
  readonly size_bytes: number
  readonly schema_version: number | null
  readonly app_version: string | null
  readonly file_count: number | null
  readonly includes_storage: boolean | null
  readonly excluded: readonly ExcludedItem[]
}

export interface ExportResponse {
  readonly name: string
  readonly size_bytes: number
}

export interface VerifyResponse {
  readonly name: string
  readonly valid: boolean
  readonly schema_version: number
  readonly file_count: number
}
