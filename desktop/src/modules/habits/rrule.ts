export type FrequencyKind = 'daily' | 'weekdays' | 'everyNWeeks' | 'monthly'

export interface Frequency {
  readonly kind: FrequencyKind
  /** Códigos RRULE (MO…SU). */
  readonly days: readonly string[]
  readonly interval: number
  readonly monthDay: number
}

/** Orden lunes → domingo; `code` es el de RRULE, `iso` el de la API (1..7). */
export const WEEK_DAYS = [
  { code: 'MO', iso: 1, short: 'L', name: 'Lunes' },
  { code: 'TU', iso: 2, short: 'M', name: 'Martes' },
  { code: 'WE', iso: 3, short: 'X', name: 'Miércoles' },
  { code: 'TH', iso: 4, short: 'J', name: 'Jueves' },
  { code: 'FR', iso: 5, short: 'V', name: 'Viernes' },
  { code: 'SA', iso: 6, short: 'S', name: 'Sábado' },
  { code: 'SU', iso: 7, short: 'D', name: 'Domingo' }
] as const

const ALL_CODES = WEEK_DAYS.map((d) => d.code)

export function buildRrule(f: Frequency): string {
  const days = ALL_CODES.filter((c) => f.days.includes(c)).join(',')
  switch (f.kind) {
    case 'daily':
      return 'FREQ=DAILY'
    case 'weekdays':
      return `FREQ=WEEKLY;BYDAY=${days}`
    case 'everyNWeeks':
      return `FREQ=WEEKLY;INTERVAL=${Math.max(2, f.interval)};BYDAY=${days}`
    case 'monthly':
      return `FREQ=MONTHLY;BYMONTHDAY=${f.monthDay}`
  }
}

/** Devuelve null si la regla usa algo que el editor no sabe representar. */
export function parseRrule(rrule: string): Frequency | null {
  const parts = new Map<string, string>()
  for (const piece of rrule.split(';')) {
    const [k, v] = piece.split('=')
    if (k && v !== undefined) parts.set(k.toUpperCase(), v)
  }
  const freq = parts.get('FREQ')
  const interval = Number(parts.get('INTERVAL') ?? 1)
  const days = (parts.get('BYDAY') ?? '').split(',').filter(Boolean)
  if (days.some((d) => !ALL_CODES.includes(d as (typeof ALL_CODES)[number]))) return null
  if (freq === 'DAILY' && interval === 1 && days.length === 0) return { kind: 'daily', days: [], interval: 1, monthDay: 1 }
  if (freq === 'WEEKLY' && days.length > 0)
    return interval === 1
      ? { kind: 'weekdays', days, interval: 1, monthDay: 1 }
      : { kind: 'everyNWeeks', days, interval, monthDay: 1 }
  if (freq === 'MONTHLY') {
    const md = Number(parts.get('BYMONTHDAY'))
    if (Number.isInteger(md) && md >= 1 && md <= 31 && interval === 1) return { kind: 'monthly', days: [], interval: 1, monthDay: md }
  }
  return null
}

export function describeRrule(rrule: string): string {
  const f = parseRrule(rrule)
  if (!f) return rrule
  const names = WEEK_DAYS.filter((d) => f.days.includes(d.code)).map((d) => d.name.toLowerCase())
  switch (f.kind) {
    case 'daily':
      return 'Todos los días'
    case 'weekdays':
      return f.days.length === 7 ? 'Todos los días' : `Cada semana: ${names.join(', ')}`
    case 'everyNWeeks':
      return `Cada ${f.interval} semanas: ${names.join(', ')}`
    case 'monthly':
      return `Cada mes, el día ${f.monthDay}`
  }
}
