export type MemoryKind = 'working' | 'episodic' | 'semantic' | 'procedural'
export type MemoryCategory = 'profile' | 'preferences' | 'entities' | 'events' | 'cases' | 'patterns'
export type MemoryStatus = 'pending' | 'approved' | 'rejected' | 'superseded'
export type MemoryTrust = 'user_confirmed' | 'user_stated' | 'derived' | 'third_party'

export interface MemoryProvenance {
  readonly source_type: string
  readonly source_ref: string | null
  readonly session_id: string | null
  readonly captured_at: string
}

/** Recuerdo. Es dato no confiable: se muestra, nunca se obedece. */
export interface MemoryRecord {
  readonly id: string
  readonly kind: MemoryKind
  readonly category: MemoryCategory
  readonly subject: string
  readonly content: string
  readonly abstract: string
  readonly overview: string
  readonly provenance: MemoryProvenance
  readonly trust: MemoryTrust
  readonly confidence: number
  readonly valid_until: string | null
  readonly status: MemoryStatus
  readonly content_hash: string
  readonly supersedes: string | null
  readonly entity_refs: readonly { readonly entity_type: string; readonly entity_id: string }[]
  readonly created_at: string
  readonly updated_at: string
}

export interface MemoryPage {
  readonly items: readonly MemoryRecord[]
  readonly total: number
  readonly limit: number
  readonly offset: number
}

export interface MemoryHit {
  readonly id: string
  readonly kind: MemoryKind
  readonly category: MemoryCategory
  readonly abstract: string
  readonly score: number
  readonly trust: MemoryTrust
  readonly provenance: MemoryProvenance
  readonly updated_at: string
}

export interface MemoryConflict {
  readonly id: string
  readonly memory_a: string
  readonly memory_b: string
  readonly reason: string
  readonly status: 'open' | 'resolved'
  readonly created_at: string
  readonly resolved_at: string | null
  readonly kept: string | null
}

export interface MemoryBackendStatus {
  readonly backend: string
  readonly available: boolean
  readonly detail: string
}

export interface ForgetReport {
  readonly memory_id: string
  readonly erased_from: readonly string[]
  readonly not_reached: readonly string[]
}

export interface MemoryListParams {
  readonly statuses?: readonly MemoryStatus[]
  readonly kinds?: readonly MemoryKind[]
  readonly categories?: readonly MemoryCategory[]
  readonly limit?: number
  readonly offset?: number
}
