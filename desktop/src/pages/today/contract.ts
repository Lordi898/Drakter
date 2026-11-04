/** Espejo de `backend/app/services/today_models.py` y `settings_models.py`. */
export type Priority = 'low' | 'medium' | 'high' | 'urgent'
export type UnavailableReason = 'not_migrated' | 'module_missing' | 'failed'

export interface Section<T> {
  readonly status: 'ready' | 'unavailable'
  readonly reason: UnavailableReason | null
  readonly items: readonly T[]
  readonly total: number
  readonly truncated: boolean
}

export interface TodayTask {
  readonly id: string
  readonly title: string
  readonly status: 'pending' | 'in_progress' | 'on_hold'
  readonly priority: Priority
  readonly due_at: string | null
  readonly due_date: string | null
  readonly days_overdue: number
  readonly project_id: string | null
  readonly project_name: string | null
  readonly parent_task_id: string | null
}

export interface TodayProject {
  readonly id: string
  readonly name: string
  readonly priority: Priority
  readonly target_date: string | null
  readonly progress: number | null
  readonly progress_source: 'manual' | 'calculated' | null
  readonly open_tasks: number
  readonly overdue_tasks: number
}

export interface TodayAgendaEntry {
  readonly occurrence_id: string
  readonly source_type: string
  readonly source_id: string
  readonly title: string
  readonly kind: string
  readonly all_day: boolean
  readonly display_start: string | null
  readonly display_end: string | null
  readonly room: string | null
  readonly color: string | null
}

export interface TodayHabit {
  readonly id: string
  readonly name: string
  readonly preferred_local_time: string | null
  readonly today_status: 'done' | 'skipped' | 'missed' | null
}

export interface TodayResponse {
  readonly date: string
  readonly timezone: string
  readonly generated_at: string
  readonly overdue: Section<TodayTask>
  readonly due_today: Section<TodayTask>
  readonly projects: Section<TodayProject>
  readonly agenda: Section<TodayAgendaEntry>
  readonly habits: Section<TodayHabit>
}

export interface SettingItem {
  readonly key: string
  readonly value: string | null
  readonly updated_at: string | null
}

export interface SettingsList {
  readonly persisted: boolean
  readonly items: readonly SettingItem[]
}

export interface BackupItem {
  readonly name: string
  readonly created_at: string
  readonly label: string
  readonly size_bytes: number
}

export interface SettingsStatus {
  readonly agent: {
    readonly key: 'configured' | 'missing' | 'unknown'
    readonly dev_mode: 'active' | 'inactive' | 'unknown'
    readonly provider: string | null
    readonly model: string | null
  }
  readonly storage: {
    readonly data_dir: string
    readonly schema_version: number | null
  }
  readonly last_backup: BackupItem | null
}
