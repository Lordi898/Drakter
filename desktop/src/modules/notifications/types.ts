export type NotificationSeverity = 'info' | 'success' | 'warning' | 'error'

/** Forma validada de una notificación del backend (dato no confiable, solo texto plano). */
export interface BackendNotification {
  readonly id: string
  readonly kind: string
  readonly title: string
  readonly body: string | null
  readonly severity: NotificationSeverity
  readonly entityId: string | null
  readonly createdAt: string
  readonly readAt: string | null
}

export interface NotificationsStatus {
  readonly requires_app_open: boolean
  readonly running: boolean
  readonly tick_seconds: number
  readonly catch_up_hours: number
  readonly last_tick_at: string | null
  readonly last_error: string | null
}
