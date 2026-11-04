import type { RecordStatus } from './types'

export const STATUS_LABEL: Record<RecordStatus, string> = {
  done: 'Hecho',
  skipped: 'Saltado',
  missed: 'No hecho'
}

export const STATUS_ORDER: readonly RecordStatus[] = ['done', 'skipped', 'missed']

export const STATUS_ACTIVE_CLASS: Record<RecordStatus, string> = {
  done: 'border-success bg-success text-white hover:bg-success/90',
  skipped: 'border-warning bg-warning text-white hover:bg-warning/90 dark:text-[#081a33]',
  missed: 'border-destructive bg-destructive text-white hover:bg-destructive/90'
}
