import type { TodayResponse, TodayTask } from './contract'

const ISO_DAY = /^(\d{4})-(\d{2})-(\d{2})/

/** 'AAAA-MM-DD' como instante UTC: formateado con `timeZone: 'UTC'` no desplaza el día. */
export function parseDay(day: string): Date | null {
  const m = ISO_DAY.exec(day)
  if (!m) return null
  return new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3])))
}

function formatDay(day: string, options: Intl.DateTimeFormatOptions): string | null {
  const date = parseDay(day)
  return date ? new Intl.DateTimeFormat('es-ES', { timeZone: 'UTC', ...options }).format(date) : null
}

export function weekdayOf(day: string): string {
  return formatDay(day, { weekday: 'long' }) ?? ''
}

export function dayNumberOf(day: string): string {
  return formatDay(day, { day: 'numeric' }) ?? ''
}

export function monthOf(day: string): string {
  return formatDay(day, { month: 'long' }) ?? ''
}

export function longDay(day: string): string {
  return formatDay(day, { day: 'numeric', month: 'long' }) ?? day
}

export function shortDay(day: string, withYear: boolean): string {
  const options: Intl.DateTimeFormatOptions = withYear
    ? { day: 'numeric', month: 'short', year: 'numeric' }
    : { day: 'numeric', month: 'short' }
  return formatDay(day, options) ?? day
}

export function yearOf(day: string): number | null {
  const m = ISO_DAY.exec(day)
  return m ? Number(m[1]) : null
}

/** Día 'AAAA-MM-DD' ahora mismo en `timeZone`; null si la zona no es válida. */
export function dayInZone(timeZone: string): string | null {
  try {
    return new Intl.DateTimeFormat('en-CA', {
      timeZone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    }).format(new Date())
  } catch {
    return null
  }
}

/** Hora 'HH:MM' de un instante guardado (UTC) vista en `timeZone`. */
export function timeInZone(instant: string, timeZone: string): string | null {
  const hasZone = /(Z|[+-]\d{2}:?\d{2})$/.test(instant)
  const date = new Date(hasZone ? instant : `${instant}Z`)
  if (Number.isNaN(date.getTime())) return null
  try {
    return new Intl.DateTimeFormat('es-ES', {
      timeZone,
      hour: '2-digit',
      minute: '2-digit',
      hourCycle: 'h23'
    }).format(date)
  } catch {
    return null
  }
}

/** Corta 'HH:MM' del texto ('AAAA-MM-DDTHH:MM:SS' o 'HH:MM[:SS]') sin pasar por Date. */
export function clockOf(text: string | null): string | null {
  if (!text) return null
  const m = /(?:T|^)(\d{2}:\d{2})/.exec(text)
  return m?.[1] ?? null
}

export function plural(n: number, one: string, other: string): string {
  return n === 1 ? one : other
}

export function taskTime(task: TodayTask, timeZone: string): string | null {
  return task.due_at ? timeInZone(task.due_at, timeZone) : null
}

export function overdueLabel(task: TodayTask, timeZone: string): string {
  if (task.days_overdue >= 2) return `hace ${task.days_overdue} días`
  if (task.days_overdue === 1) return 'ayer'
  const time = taskTime(task, timeZone)
  return time ? `hoy a las ${time}` : 'hoy'
}

/** Frase con recuentos reales; null si alguna de las dos secciones no está disponible. */
export function summaryPhrase(data: TodayResponse): string | null {
  if (data.overdue.status !== 'ready' || data.due_today.status !== 'ready') return null
  const late = data.overdue.total
  const today = data.due_today.total
  if (late === 0 && today === 0) return 'Nada pendiente para hoy.'
  const lateText = `${late} ${plural(late, 'vencida', 'vencidas')}`
  const todayText = `${today} para hoy`
  if (late > 0 && today > 0) return `${lateText} y ${todayText}.`
  return late > 0 ? `${lateText}.` : `${todayText}.`
}
