import type { NOTIFICATION_OPERATIONS } from './operations'

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

export type NotificationOp = keyof typeof NOTIFICATION_OPERATIONS

/** Lo que el módulo necesita del cliente único de `@/services`. Rechaza ante error HTTP o de red. */
export type NotificationCall = (
  op: NotificationOp,
  args?: { readonly query?: Readonly<Record<string, string | number | boolean>>; readonly body?: unknown }
) => Promise<unknown>

/** Compatible con `window.drakter.api.subscribe('events', …)`: el evento llega sin validar. */
export type SubscribeFn = (listener: (event: unknown) => void) => () => void

export interface NotificationFeedOptions {
  readonly call: NotificationCall
  readonly subscribe?: SubscribeFn
}
