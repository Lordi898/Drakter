import type { BackendNotification, NotificationSeverity, NotificationsStatus } from './types'

const SEVERITIES: readonly string[] = ['info', 'success', 'warning', 'error']
const MAX_TITLE = 120
const MAX_BODY = 500

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function nullableString(value: unknown): string | null | undefined {
  if (value === null || value === undefined) return null
  return typeof value === 'string' ? value : undefined
}

export function parseNotification(raw: unknown): BackendNotification | null {
  if (!isRecord(raw)) return null
  const { id, kind, title, severity, created_at: createdAt } = raw
  if (typeof id !== 'string' || id === '' || typeof kind !== 'string') return null
  if (typeof title !== 'string' || title.trim() === '') return null
  if (typeof severity !== 'string' || !SEVERITIES.includes(severity)) return null
  if (typeof createdAt !== 'string') return null
  const body = nullableString(raw.body)
  const entityId = nullableString(raw.entity_id)
  const readAt = nullableString(raw.read_at)
  if (body === undefined || entityId === undefined || readAt === undefined) return null
  return {
    id,
    kind,
    title: title.slice(0, MAX_TITLE),
    body: body === null || body === '' ? null : body.slice(0, MAX_BODY),
    severity: severity as NotificationSeverity,
    entityId,
    createdAt,
    readAt
  }
}

export function parseNotificationList(raw: unknown): BackendNotification[] {
  if (!isRecord(raw) || !Array.isArray(raw.items)) return []
  const out: BackendNotification[] = []
  for (const item of raw.items as unknown[]) {
    const parsed = parseNotification(item)
    if (parsed !== null) out.push(parsed)
  }
  return out
}

export function parseStatus(raw: unknown): NotificationsStatus | null {
  if (!isRecord(raw)) return null
  const { running, tick_seconds: tick, catch_up_hours: hours } = raw
  const lastTick = nullableString(raw.last_tick_at)
  const lastError = nullableString(raw.last_error)
  if (typeof running !== 'boolean' || typeof tick !== 'number' || typeof hours !== 'number') return null
  if (lastTick === undefined || lastError === undefined) return null
  return {
    requires_app_open: true,
    running,
    tick_seconds: tick,
    catch_up_hours: hours,
    last_tick_at: lastTick,
    last_error: lastError
  }
}
