export const WEEKDAYS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'] as const

export function weekdayName(weekday: number): string {
  return WEEKDAYS[weekday - 1] ?? ''
}

/** 'HH:MM' (o con segundos) -> 'HH:MM'. */
export function hhmm(time: string): string {
  return time.slice(0, 5)
}

/** Valor de input time -> 'HH:MM'. */
export function toApiTime(value: string): string {
  return value.slice(0, 5)
}

export function minutesOf(time: string): number {
  const [h, m] = time.split(':')
  return Number(h) * 60 + Number(m)
}

function pad(n: number): string {
  return String(n).padStart(2, '0')
}

/** Fecha local de hoy como AAAA-MM-DD. */
export function todayIso(): string {
  const d = new Date()
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** Día de la semana 1=lunes .. 7=domingo de una fecha AAAA-MM-DD. */
export function weekdayOf(iso: string): number {
  const [y, m, d] = iso.split('-').map(Number)
  const day = new Date(y ?? 1970, (m ?? 1) - 1, d ?? 1).getDay()
  return day === 0 ? 7 : day
}

export function localTimezone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
}

export function formatDate(iso: string): string {
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

export function validityText(from: string, until: string | null): string {
  return until ? `Del ${formatDate(from)} al ${formatDate(until)}` : `Desde el ${formatDate(from)}`
}

export function intervalText(weeks: number): string {
  return weeks === 1 ? 'Cada semana' : `Cada ${weeks} semanas`
}

/** 'AAAA-MM-DDTHH:MM:SS' -> 'DD/MM HH:MM'. */
export function formatLocalStart(local: string): string {
  const [date = '', time = ''] = local.split('T')
  const [, m, d] = date.split('-')
  return `${d}/${m} ${time.slice(0, 5)}`.trim()
}
