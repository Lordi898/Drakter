import { addNotification, type NotificationInput } from '@/stores/notifications'

// Stub: lo completa la pieza de notificaciones (toast + escritorio). La firma está congelada.
export function notify(input: NotificationInput): void {
  addNotification(input)
}
