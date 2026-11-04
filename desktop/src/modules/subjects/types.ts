/** Espejo de backend/app/schemas/subjects.py. Horas 'HH:MM:SS' locales; weekday 1=lunes .. 7=domingo. */
export interface Subject {
  readonly id: string
  readonly name: string
  readonly description: string | null
  readonly teacher: string | null
  readonly color: string | null
  readonly session_count: number
  readonly archived_at: string | null
  readonly revision: number
  readonly created_at: string
  readonly updated_at: string
}

export interface SubjectInput {
  readonly name: string
  readonly description: string | null
  readonly teacher: string | null
  readonly color: string | null
}

export interface ClassSession {
  readonly id: string
  readonly subject_id: string
  readonly weekday: number
  readonly starts_local_time: string
  readonly ends_local_time: string
  readonly timezone: string
  readonly valid_from: string
  readonly valid_until: string | null
  readonly room: string | null
  readonly archived_at: string | null
  readonly revision: number
  readonly created_at: string
  readonly updated_at: string
}

export interface SessionInput {
  readonly weekday: number
  readonly starts_local_time: string
  readonly ends_local_time: string
  readonly timezone: string
  readonly valid_from: string
  readonly valid_until: string | null
  readonly room: string | null
}

/** Subconjunto de AgendaItem que usa el aviso de solapes. */
export interface ConflictItem {
  readonly title: string
  readonly occurrence_local_start: string
  readonly display_start: string | null
  readonly display_end: string | null
}

export interface SessionWriteResult {
  readonly session: ClassSession
  readonly conflicts: readonly ConflictItem[]
}

export interface OccurrenceOverride {
  readonly local_start?: string
  readonly local_end?: string
  readonly room?: string
}

export type ExceptionInput =
  | { readonly occurrence_date: string; readonly kind: 'cancelled' }
  | { readonly occurrence_date: string; readonly kind: 'modified'; readonly override: OccurrenceOverride }

export interface TimetableEntry {
  readonly session_id: string
  readonly subject_id: string
  readonly subject_name: string
  readonly color: string | null
  readonly teacher: string | null
  readonly weekday: number
  readonly starts_local_time: string
  readonly ends_local_time: string
  readonly timezone: string
  readonly room: string | null
  readonly valid_from: string
  readonly valid_until: string | null
}

export interface Timetable {
  readonly on_date: string
  readonly entries: readonly TimetableEntry[]
}
