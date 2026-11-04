export function systemTimezone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
}

function isValidZone(zone: string): boolean {
  try {
    new Intl.DateTimeFormat('en-CA', { timeZone: zone })
    return true
  } catch {
    return false
  }
}

/** Fecha de hoy `YYYY-MM-DD` en la zona indicada. */
export function todayIn(zone: string): string {
  const tz = isValidZone(zone) ? zone : systemTimezone()
  return new Intl.DateTimeFormat('en-CA', { timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit' }).format(
    new Date()
  )
}

function parse(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(Date.UTC(y ?? 1970, (m ?? 1) - 1, d ?? 1))
}

export function addDays(iso: string, days: number): string {
  const d = parse(iso)
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

/** 1 = lunes … 7 = domingo. */
export function isoWeekday(iso: string): number {
  const d = parse(iso).getUTCDay()
  return d === 0 ? 7 : d
}

export function formatDate(iso: string, withYear = true): string {
  return new Intl.DateTimeFormat('es', {
    timeZone: 'UTC',
    day: 'numeric',
    month: 'short',
    ...(withYear ? { year: 'numeric' } : {})
  }).format(parse(iso))
}

export function formatLongDate(iso: string): string {
  return new Intl.DateTimeFormat('es', { timeZone: 'UTC', weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(
    parse(iso)
  )
}

export function dayOfMonth(iso: string): number {
  return parse(iso).getUTCDate()
}

export function timeZoneOptions(current: string): readonly string[] {
  const supported = (Intl as unknown as { supportedValuesOf?: (key: string) => string[] }).supportedValuesOf
  const list = supported ? supported('timeZone') : []
  return list.includes(current) ? list : [current, ...list]
}
