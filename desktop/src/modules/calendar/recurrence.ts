/** Construcción y lectura de la cadena RRULE que acepta el backend (FREQ, INTERVAL, COUNT, UNTIL, BYDAY, BYMONTHDAY). */
export type Repeat = 'none' | 'daily' | 'weekly' | 'monthly'
export type EndMode = 'never' | 'until' | 'count'
export const WEEKDAY_CODES = ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU'] as const
export type WeekdayCode = (typeof WEEKDAY_CODES)[number]
export const WEEKDAY_NAMES: Readonly<Record<WeekdayCode, string>> = {
  MO: 'Lunes',
  TU: 'Martes',
  WE: 'Miércoles',
  TH: 'Jueves',
  FR: 'Viernes',
  SA: 'Sábado',
  SU: 'Domingo'
}

export interface RecurrenceDraft {
  repeat: Repeat
  interval: number
  weekdays: WeekdayCode[]
  endMode: EndMode
  until: string
  count: number
}

export const NO_RECURRENCE: RecurrenceDraft = {
  repeat: 'none',
  interval: 1,
  weekdays: [],
  endMode: 'never',
  until: '',
  count: 10
}

/** `startDate` ('AAAA-MM-DD') fija el día del mes y el día de la semana por defecto. */
export function buildRrule(draft: RecurrenceDraft, startDate: string): string | null {
  if (draft.repeat === 'none') return null
  const parts: string[] = [`FREQ=${draft.repeat.toUpperCase()}`]
  if (draft.interval > 1) parts.push(`INTERVAL=${draft.interval}`)
  if (draft.repeat === 'weekly' && draft.weekdays.length > 0) {
    const ordered = WEEKDAY_CODES.filter((code) => draft.weekdays.includes(code))
    parts.push(`BYDAY=${ordered.join(',')}`)
  }
  if (draft.repeat === 'monthly') parts.push(`BYMONTHDAY=${Number(startDate.slice(8, 10))}`)
  if (draft.endMode === 'until' && draft.until) parts.push(`UNTIL=${draft.until.replaceAll('-', '')}`)
  if (draft.endMode === 'count' && draft.count > 0) parts.push(`COUNT=${draft.count}`)
  return parts.join(';')
}

/** Lee una RRULE guardada. `supported=false` si trae algo que este formulario no sabe editar. */
export function parseRrule(text: string | null): { draft: RecurrenceDraft; supported: boolean } {
  if (!text) return { draft: { ...NO_RECURRENCE }, supported: true }
  const map = new Map<string, string>()
  for (const piece of text.split(';')) {
    const [k, v] = piece.split('=')
    if (k && v !== undefined) map.set(k.toUpperCase(), v)
  }
  const freq = map.get('FREQ')
  const repeat: Repeat = freq === 'DAILY' ? 'daily' : freq === 'WEEKLY' ? 'weekly' : freq === 'MONTHLY' ? 'monthly' : 'none'
  const draft: RecurrenceDraft = { ...NO_RECURRENCE, repeat }
  draft.interval = Math.max(1, Number(map.get('INTERVAL') ?? 1) || 1)
  const byday = map.get('BYDAY')
  if (byday) draft.weekdays = byday.split(',').filter((c): c is WeekdayCode => (WEEKDAY_CODES as readonly string[]).includes(c))
  const until = map.get('UNTIL')
  if (until && /^\d{8}/.test(until)) {
    draft.endMode = 'until'
    draft.until = `${until.slice(0, 4)}-${until.slice(4, 6)}-${until.slice(6, 8)}`
  }
  const count = map.get('COUNT')
  if (count) {
    draft.endMode = 'count'
    draft.count = Math.max(1, Number(count) || 1)
  }
  const knownKeys = ['FREQ', 'INTERVAL', 'COUNT', 'UNTIL', 'BYDAY', 'BYMONTHDAY']
  const supported =
    repeat !== 'none' &&
    [...map.keys()].every((k) => knownKeys.includes(k)) &&
    !(byday ?? '').split(',').some((t) => /^[+-]?\d/.test(t))
  return { draft, supported }
}

export function describeRrule(text: string | null): string {
  const { draft, supported } = parseRrule(text)
  if (!text) return 'No se repite'
  if (!supported) return `Repetición personalizada (${text})`
  const every = draft.interval > 1 ? `Cada ${draft.interval} ` : 'Cada '
  const unit =
    draft.repeat === 'daily' ? (draft.interval > 1 ? 'días' : 'día') : draft.repeat === 'weekly' ? (draft.interval > 1 ? 'semanas' : 'semana') : draft.interval > 1 ? 'meses' : 'mes'
  const days = draft.weekdays.length > 0 ? ` (${draft.weekdays.map((d) => WEEKDAY_NAMES[d].slice(0, 3)).join(', ')})` : ''
  const end = draft.endMode === 'until' ? `, hasta el ${draft.until}` : draft.endMode === 'count' ? `, ${draft.count} veces` : ''
  return `${every}${unit}${days}${end}`
}
