import { useSyncExternalStore } from 'react'

export type NotificationTone = 'info' | 'success' | 'warning' | 'error'

export interface AppNotification {
  readonly id: string
  readonly tone: NotificationTone
  readonly title: string
  readonly body?: string
  readonly createdAt: Date
  readonly read: boolean
}

export interface NotificationInput {
  readonly tone: NotificationTone
  readonly title: string
  readonly body?: string
  /** Si es true, también se pide una notificación de escritorio (respeta la preferencia). */
  readonly desktop?: boolean
}

const MAX_KEPT = 100
let items: readonly AppNotification[] = []
const listeners = new Set<() => void>()

function emit(): void {
  listeners.forEach((listener) => listener())
}

/** Añade al historial. Mostrar el toast y avisar al escritorio es cosa de `services/notify.ts`. */
export function addNotification(input: NotificationInput): AppNotification {
  const notification: AppNotification = {
    id: crypto.randomUUID(),
    tone: input.tone,
    title: input.title,
    ...(input.body === undefined ? {} : { body: input.body }),
    createdAt: new Date(),
    read: false
  }
  items = [notification, ...items].slice(0, MAX_KEPT)
  emit()
  return notification
}

export function markAllNotificationsRead(): void {
  items = items.map((item) => (item.read ? item : { ...item, read: true }))
  emit()
}

export function clearNotifications(): void {
  items = []
  emit()
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function useNotifications(): readonly AppNotification[] {
  return useSyncExternalStore(subscribe, () => items)
}
