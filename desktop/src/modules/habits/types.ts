/** Espejo de backend/app/schemas/habits.py. Fechas `YYYY-MM-DD`; hora `HH:MM[:SS]`. */
export type HabitStatus = 'active' | 'paused' | 'ended'
export type RecordStatus = 'done' | 'skipped' | 'missed'

export interface HabitScheduleVersion {
  readonly id: string
  readonly rrule: string
  readonly valid_from: string
  readonly valid_until: string | null
}

export interface Habit {
  readonly id: string
  readonly name: string
  readonly description: string | null
  readonly timezone: string
  readonly rrule: string
  readonly schedule_versions: readonly HabitScheduleVersion[]
  readonly status: HabitStatus
  readonly start_date: string
  readonly end_date: string | null
  readonly goal_note: string | null
  readonly goal_project_id: string | null
  readonly preferred_local_time: string | null
  readonly reminder_enabled: boolean
  readonly today_scheduled: boolean
  readonly today_status: RecordStatus | null
  readonly archived_at: string | null
  readonly revision: number
  readonly created_at: string
  readonly updated_at: string
}

export interface HabitCreate {
  readonly name: string
  readonly description?: string | null
  readonly timezone: string
  readonly rrule: string
  readonly start_date: string
  readonly end_date?: string | null
  readonly goal_note?: string | null
  readonly preferred_local_time?: string | null
  readonly reminder_enabled?: boolean
}

export interface HabitUpdate {
  readonly name?: string
  readonly description?: string | null
  readonly timezone?: string
  readonly rrule?: string
  readonly schedule_effective_from?: string
  readonly end_date?: string | null
  readonly status?: HabitStatus
  readonly goal_note?: string | null
  readonly preferred_local_time?: string | null
  readonly reminder_enabled?: boolean
}

export interface HabitRecord {
  readonly id: string
  readonly habit_id: string
  readonly occurrence_date: string
  readonly status: RecordStatus
  readonly note: string | null
}

export interface HabitHistoryDay {
  readonly date: string
  readonly scheduled: boolean
  readonly status: RecordStatus | null
  readonly note: string | null
}

export interface HabitHistory {
  readonly habit_id: string
  readonly from_date: string
  readonly to_date: string
  readonly days: readonly HabitHistoryDay[]
}

export interface WeekdayStat {
  /** 1 = lunes … 7 = domingo. */
  readonly weekday: number
  readonly scheduled: number
  readonly done: number
}

export interface HabitStatistics {
  readonly habit_id: string
  readonly from_date: string
  readonly to_date: string
  readonly scheduled: number
  readonly done: number
  readonly skipped: number
  readonly missed: number
  readonly unrecorded: number
  readonly completion_rate: number | null
  readonly current_streak: number
  readonly best_streak: number
  readonly by_weekday: readonly WeekdayStat[]
}
