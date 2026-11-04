/** Espejo de backend/app/schemas/calendar.py. Fechas y horas locales viajan como texto sin desfase. */
export type EventKind = 'event' | 'reminder' | 'work_session'
export type EventStatus = 'tentative' | 'confirmed' | 'cancelled'
export type TimeBlockStatus = 'planned' | 'in_progress' | 'done' | 'skipped' | 'cancelled'
export type SourceType = 'calendar_event' | 'time_block' | 'class_session'
export type OccurrenceKind = EventKind | 'time_block' | 'class'

export interface EventOut {
  readonly id: string
  readonly title: string
  readonly description: string | null
  readonly location: string | null
  readonly reminder_minutes_before: number | null
  readonly kind: EventKind
  readonly status: EventStatus
  readonly timezone: string
  readonly all_day: boolean
  readonly local_start: string | null
  readonly local_end: string | null
  readonly start_date: string | null
  readonly end_date_exclusive: string | null
  readonly rrule: string | null
  readonly revision: number
}

export interface EventPayload {
  title: string
  description: string | null
  location: string | null
  reminder_minutes_before: number | null
  kind: EventKind
  status: EventStatus
  timezone: string
  all_day: boolean
  local_start: string | null
  local_end: string | null
  start_date: string | null
  end_date_exclusive: string | null
  rrule: string | null
}

export interface TimeBlockOut {
  readonly id: string
  readonly title: string
  readonly description: string | null
  readonly timezone: string
  readonly local_start: string
  readonly local_end: string
  readonly status: TimeBlockStatus
  readonly task_id: string | null
  readonly revision: number
}

export interface TimeBlockPayload {
  title: string
  description: string | null
  timezone: string
  local_start: string
  local_end: string
  status: TimeBlockStatus
  task_id: string | null
}

export interface AgendaItem {
  readonly occurrence_id: string
  readonly source_type: SourceType
  readonly source_id: string
  readonly title: string
  readonly description: string | null
  readonly kind: string
  readonly status: string
  readonly all_day: boolean
  readonly timezone: string
  readonly occurrence_local_start: string
  readonly starts_at_utc: string | null
  readonly ends_at_utc: string | null
  readonly start_date: string | null
  readonly end_date_exclusive: string | null
  readonly display_start: string | null
  readonly display_end: string | null
  readonly recurring: boolean
  readonly modified: boolean
  readonly location: string | null
  readonly room: string | null
  readonly subject_id: string | null
  readonly task_id: string | null
  readonly color: string | null
}

export interface AgendaResponse {
  readonly timezone: string
  readonly from_date: string
  readonly to_date: string
  readonly items: readonly AgendaItem[]
  readonly truncated: boolean
}

export interface OverlapsResponse {
  readonly timezone: string
  readonly items: readonly OverlapGroup[]
}

export interface OverlapGroup {
  readonly items: readonly string[]
  readonly starts_at_utc: string
  readonly ends_at_utc: string
}

export interface EventWriteResult {
  readonly event: EventOut
  readonly conflicts: readonly AgendaItem[]
}

export interface TimeBlockWriteResult {
  readonly time_block: TimeBlockOut
  readonly conflicts: readonly AgendaItem[]
}

export type CalendarView = 'day' | 'week' | 'month'

/** Tipos filtrables en pantalla. */
export const KIND_ORDER: readonly OccurrenceKind[] = ['event', 'reminder', 'work_session', 'time_block', 'class']

export function normalizeKind(kind: string): OccurrenceKind {
  return (KIND_ORDER as readonly string[]).includes(kind) ? (kind as OccurrenceKind) : 'event'
}
