/**
 * Modelo de vista de la Holomesa: lo que dibujan las 7 estaciones. Lo produce `adapt.ts` a partir de
 * las instantáneas de `jarvis/data` (datos reales del Workspace); aquí no hay ni fetch ni datos de ejemplo.
 * Todo texto que venga del usuario (títulos, nombres) se trata como texto plano: nunca HTML.
 */
import type { EntityType } from '@/modules/relationships/types'
import type { IndexStatus, ResourceType } from '@/modules/storage/types'
import type { Priority, TaskStatus } from '@/modules/tasks/types'

export type SectionId = 'hoy' | 'calendario' | 'tareas' | 'proyectos' | 'habitos' | 'relaciones' | 'almacen'

export const SECTION_ORDER: readonly SectionId[] = ['hoy', 'calendario', 'tareas', 'proyectos', 'habitos', 'relaciones', 'almacen']

export const SECTION_NAMES: Readonly<Record<SectionId, string>> = {
  hoy: 'Hoy',
  calendario: 'Calendario',
  tareas: 'Tareas',
  proyectos: 'Proyectos',
  habitos: 'Hábitos',
  relaciones: 'Relaciones',
  almacen: 'Almacén'
}

/** Estado de carga de una sección: lo que no ha llegado o falló no se inventa. */
export type Load = 'loading' | 'ready' | 'error'

export type HmEventKind = 'clase' | 'evento' | 'recordatorio' | 'bloque'

export interface HmEvent {
  readonly id: string
  readonly title: string
  /** Día dentro de la ventana de 14 días del calendario (0 = lunes de esta semana). En Hoy siempre es el de hoy. */
  readonly day: number
  /** Horas locales decimales (9.5 = 09:30); `end` puede ser 24. */
  readonly start: number
  readonly end: number
  readonly allDay: boolean
  readonly kind: HmEventKind
  /** Color propio (asignatura o evento), `null` = el del tipo. */
  readonly color: number | null
  readonly place: string | null
  readonly sourceType: 'calendar_event' | 'time_block' | 'class_session'
  readonly sourceId: string
}

/** Columna de la pila de tareas (solo abiertas): 0 pendiente, 1 en curso, 2 en espera. */
export type HmColumn = 0 | 1 | 2

export interface HmTask {
  readonly id: string
  readonly title: string
  readonly status: TaskStatus
  readonly column: HmColumn
  readonly priority: Priority
  readonly project: string | null
  /** Vencimiento legible («hoy», «vie 28»…) o `null`. */
  readonly due: string | null
  readonly overdue: boolean
  readonly dueSoon: boolean
  readonly estimatedMin: number | null
  readonly revision: number
}

export interface HmProject {
  readonly id: string
  readonly name: string
  /** 0..1 */
  readonly progress: number
  readonly total: number
  readonly completed: number
  readonly overdue: number
  readonly due: string | null
}

/** Un día del historial de un hábito: `null` = no tocaba. */
export type HmHabitDay = 'done' | 'skipped' | 'missed' | 'open' | null

export interface HmHabit {
  readonly id: string
  readonly name: string
  /** 28 días, el último es hoy. */
  readonly days: readonly HmHabitDay[]
  readonly streak: number
  readonly best: number
  readonly goal: string | null
  readonly todayScheduled: boolean
  readonly todayDone: boolean
  readonly revision: number
}

export interface HmNode {
  readonly id: string
  readonly label: string
  readonly kind: EntityType
}

export interface HmFile {
  readonly id: string
  readonly title: string
  readonly type: ResourceType
  readonly sizeBytes: number | null
  readonly folder: string | null
  readonly index: IndexStatus
}

export interface HoloSnapshot {
  readonly now: Date
  readonly timezone: string
  /** Hora local decimal de `now` en `timezone`. */
  readonly nowHours: number
  readonly today: {
    readonly load: Load
    readonly events: readonly HmEvent[]
    /** Tareas abiertas que vencen hoy y vencidas (de `/today`). */
    readonly tasksToday: number
    readonly overdue: number
    /** Hábitos que tocan hoy y cuántos están hechos. */
    readonly habitsDue: number
    readonly habitsDone: number
    readonly label: string
  }
  readonly calendar: { readonly load: Load; readonly days: readonly string[]; readonly todayIndex: number; readonly events: readonly HmEvent[]; readonly subjects: readonly { readonly id: string; readonly name: string; readonly color: number | null }[] }
  readonly tasks: { readonly load: Load; readonly items: readonly HmTask[] }
  readonly projects: { readonly load: Load; readonly items: readonly HmProject[] }
  readonly habits: { readonly load: Load; readonly items: readonly HmHabit[] }
  readonly graph: { readonly load: Load; readonly nodes: readonly HmNode[]; readonly edges: readonly (readonly [string, string])[] }
  readonly files: { readonly load: Load; readonly items: readonly HmFile[]; readonly total: number; readonly pending: number }
}

/** Referencia al elemento real seleccionado en un holograma: habilita las acciones del panel. */
export type PickRef =
  | { readonly kind: 'task'; readonly id: string }
  | { readonly kind: 'event'; readonly sourceType: HmEvent['sourceType']; readonly id: string }
  | { readonly kind: 'project'; readonly id: string }
  | { readonly kind: 'habit'; readonly id: string; readonly day: number }
  | { readonly kind: 'entity'; readonly id: string; readonly entityType: EntityType }
  | { readonly kind: 'resource'; readonly id: string }

export interface PickInfo {
  readonly key: string
  readonly title: string
  readonly sub: string
  readonly lines: readonly string[]
  readonly ref: PickRef
}

/** Hex `#rrggbb` → número, o `null` si no es válido (los colores vienen del usuario). */
export function parseColor(hex: string | null | undefined): number | null {
  if (!hex) return null
  const m = /^#?([0-9a-f]{6})$/i.exec(hex.trim())
  return m ? parseInt(m[1]!, 16) : null
}

/** «09:30» a partir de horas decimales. */
export function hhmm(h: number): string {
  const total = Math.round(h * 60)
  return `${String(Math.floor(total / 60) % 24).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`
}
