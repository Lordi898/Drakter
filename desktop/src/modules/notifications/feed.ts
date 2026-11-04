import { addNotification } from '@/stores/notifications'
import { notify } from '@/services/notify'
import { parseNotificationList } from './parse'
import type { NotificationFeedOptions } from './types'

const POLL_MS = 60_000
const MAX_SEEN = 1000
const MAX_INDIVIDUAL = 3
const READ_BATCH = 200

/** Arranca la entrega de recordatorios locales. Devuelve la función de parada. */
export function startNotificationFeed({ call, subscribe }: NotificationFeedOptions): () => void {
  const seen = new Set<string>()
  let stopped = false
  let inFlight = false
  let pending = false

  function remember(id: string): void {
    seen.add(id)
    if (seen.size > MAX_SEEN) {
      const oldest = seen.values().next()
      if (!oldest.done) seen.delete(oldest.value)
    }
  }

  async function cycle(): Promise<void> {
    let raw: unknown
    try {
      raw = await call('notifications.list', { query: { unread: true, limit: 50 } })
    } catch {
      return // Sin red o backend caído: el siguiente ciclo reintenta.
    }
    if (stopped) return
    const fresh = parseNotificationList(raw).filter((n) => !seen.has(n.id))
    if (fresh.length === 0) return
    fresh.forEach((n) => remember(n.id))

    if (fresh.length <= MAX_INDIVIDUAL) {
      for (const n of fresh) {
        notify({ tone: n.severity, title: n.title, ...(n.body === null ? {} : { body: n.body }), desktop: true })
      }
    } else {
      for (const n of fresh) {
        addNotification({ tone: n.severity, title: n.title, ...(n.body === null ? {} : { body: n.body }) })
      }
      notify({ tone: 'info', title: `${fresh.length} recordatorios pendientes`, desktop: true })
    }

    const ids = fresh.map((n) => n.id)
    for (let i = 0; i < ids.length; i += READ_BATCH) {
      try {
        await call('notifications.read', { body: { ids: ids.slice(i, i + READ_BATCH) } })
      } catch {
        console.warn('No se pudieron marcar los recordatorios como entregados.')
        return
      }
    }
  }

  async function run(): Promise<void> {
    if (stopped) return
    if (inFlight) {
      pending = true
      return
    }
    inFlight = true
    try {
      await cycle()
    } finally {
      inFlight = false
    }
    if (pending && !stopped) {
      pending = false
      void run()
    }
  }

  void run()
  const timer = setInterval(() => void run(), POLL_MS)
  const unsubscribe = subscribe?.((event) => {
    // Solo es un aviso de releer: de este evento sin validar no se muestra nada.
    if (typeof event === 'object' && event !== null && 'type' in event && event.type === 'notification.created') {
      void run()
    }
  })

  return () => {
    stopped = true
    clearInterval(timer)
    unsubscribe?.()
  }
}
