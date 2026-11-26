export type AuditActor = 'user' | 'agent' | 'automation' | 'system'
export type AuditResult = 'success' | 'denied' | 'failed' | 'confirmation_required'

/** Evento de auditoría (solo lectura). `params` y `changes` son dato no confiable. */
export interface AuditEvent {
  readonly seq: number
  readonly id: string
  readonly occurred_at: string
  readonly correlation_id: string
  readonly actor_type: AuditActor
  readonly origin: string
  readonly action: string
  readonly tool_name: string | null
  readonly entity_type: string | null
  readonly entity_id: string | null
  readonly affected_count: number | null
  readonly params: Record<string, unknown> | null
  readonly changes: Record<string, unknown> | null
  readonly result: AuditResult
  readonly error_code: string | null
  readonly confirmation_id: string | null
  readonly duration_ms: number | null
  readonly turn_id: string | null
  readonly tainted: boolean
}

export interface ActivityFilters {
  readonly actor?: AuditActor
  readonly entity_id?: string
  readonly result?: AuditResult
  readonly from?: string
  readonly to?: string
  readonly limit?: number
}

export interface ActivityPage {
  readonly items: readonly AuditEvent[]
  readonly next_cursor: string | null
}
