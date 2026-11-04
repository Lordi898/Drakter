/** Utilidades de fechas de calendario ('AAAA-MM-DD'). Sin aritmética de zonas: eso lo hace el backend. */
const DAY_MS = 86_400_000

export function pad(n: number): string {
  return String(n).padStart(2, '0')
}

/** Fecha civil -> Date a las 12:00 locales (evita saltos por cambio de hora). */
export function parseDate(iso: string): Date {
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number)
  return new Date(y ?? 1970, (m ?? 1) - 1, d ?? 1, 12)
}

export function formatDate(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function addDays(iso: string, days: number): string {
  return formatDate(new Date(parseDate(iso).getTime() + days * DAY_MS))
}

export function addMonths(iso: string, months: number): string {
  const d = parseDate(iso)
  const target = new Date(d.getFullYear(), d.getMonth() + months, 1, 12)
  const last = new Date(target.getFullYear(), target.getMonth() + 1, 0, 12).getDate()
  target.setDate(Math.min(d.getDate(), last))
  return formatDate(target)
}

/** Lunes de la semana de `iso`. */
export function startOfWeek(iso: string): string {
  const offset = (parseDate(iso).getDay() + 6) % 7
  return addDays(iso, -offset)
}

export function startOfMonth(iso: string): string {
  return `${iso.slice(0, 7)}-01`
}

export function daysBetween(from: string, to: string): number {
  return Math.round((parseDate(to).getTime() - parseDate(from).getTime()) / DAY_MS)
}

export function rangeOfDays(from: string, count: number): string[] {
  return Array.from({ length: count }, (_, i) => addDays(from, i))
}

/** Hoy en la zona dada. */
export function todayIn(timeZone: string): string {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone, year: 'numeric', month: '2-digit', day: '2-digit' }).format(
    new Date()
  )
  return parts
}

export function systemTimeZone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone
}

export function isValidTimeZone(zone: string): boolean {
  try {
    new Intl.DateTimeFormat('es-ES', { timeZone: zone })
    return true
  } catch {
    return false
  }
}

export function timeZoneList(current: string): string[] {
  const supported = (Intl as unknown as { supportedValuesOf?: (key: string) => string[] }).supportedValuesOf
  const all = supported ? supported('timeZone') : []
  const set = new Set<string>(['UTC', current, ...all])
  return [...set].sort((a, b) => a.localeCompare(b))
}

/** Minutos desde medianoche de 'AAAA-MM-DDTHH:MM:SS'. */
export function minutesOf(local: string): number {
  return Number(local.slice(11, 13)) * 60 + Number(local.slice(14, 16))
}

export function timeText(local: string): string {
  return local.slice(11, 16)
}

export function minutesToText(total: number): string {
  return `${pad(Math.floor(total / 60))}:${pad(total % 60)}`
}

const capitalize = (text: string): string => text.charAt(0).toUpperCase() + text.slice(1)

export function weekdayShort(iso: string): string {
  return capitalize(new Intl.DateTimeFormat('es-ES', { weekday: 'short' }).format(parseDate(iso)).replace('.', ''))
}

export function dayLabel(iso: string): string {
  return capitalize(new Intl.DateTimeFormat('es-ES', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(parseDate(iso)))
}

export function monthLabel(iso: string): string {
  return capitalize(new Intl.DateTimeFormat('es-ES', { month: 'long', year: 'numeric' }).format(parseDate(iso)))
}

export function shortDayLabel(iso: string): string {
  return new Intl.DateTimeFormat('es-ES', { day: 'numeric', month: 'short' }).format(parseDate(iso))
}

export function weekLabel(monday: string): string {
  return `${shortDayLabel(monday)} – ${new Intl.DateTimeFormat('es-ES', { day: 'numeric', month: 'short', year: 'numeric' }).format(parseDate(addDays(monday, 6)))}`
}

export function dateTimeLabel(local: string): string {
  return `${shortDayLabel(local.slice(0, 10))}, ${timeText(local)}`
}
