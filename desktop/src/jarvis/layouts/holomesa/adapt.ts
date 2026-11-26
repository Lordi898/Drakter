/**
 * Instantáneas reales del Workspace (`jarvis/data` y hooks de `modules/*`) → modelo de vista de la
 * Holomesa. Funciones puras, sin red. Lo que no ha llegado queda en `loading`; lo que falló sin dato
 * previo, en `error`. Nada se inventa: una sección sin datos se dibuja vacía y lo dice.
 */
import { addDays, daysBetween, formatDate, parseDate, shortDayLabel, todayIn, weekdayShort } from '@/modules/calendar/dateUtils'
import type { AgendaItem } from '@/modules/calendar/types'
import type { Habit, HabitHistory, HabitStatistics } from '@/modules/habits/types'
import type { Project } from '@/modules/projects/types'
import type { EntityType, RelationshipOut } from '@/modules/relationships/types'
import { ENTITY_TYPE_LABEL } from '@/modules/relationships/types'
import type { ResourceSummary } from '@/modules/storage/types'
import type { Task } from '@/modules/tasks/types'
import type { TodayAgendaEntry, TodayResponse } from '@/pages/today/contract'
import {
  parseColor,
  type HmColumn,
  type HmEvent,
  type HmEventKind,
  type HmFile,
  type HmHabit,
  type HmHabitDay,
  type HmNode,
  type HmProject,
  type HmTask,
  type HoloSnapshot,
  type Load
} from './model'

/** Forma mínima de una instantánea (`jarvis/data` `Snapshot<T>` la cumple). */
export interface Topic<T> {
  readonly status: 'loading' | 'ready' | 'offline' | 'error'
  readonly data: T | null
}

export interface HabitStatsEntry {
  readonly history: HabitHistory | null
  readonly stats: HabitStatistics | null
}

export interface AdaptInput {
  readonly now: Date
  readonly timezone: string
  readonly today: Topic<TodayResponse>
  readonly tasks: Topic<readonly Task[]>
  readonly projects: Topic<readonly Project[]>
  readonly habits: Topic<readonly Habit[]>
  readonly habitStats: ReadonlyMap<string, HabitStatsEntry>
  readonly agenda: Topic<readonly AgendaItem[]>
  readonly relationships: Topic<readonly RelationshipOut[]>
  readonly resources: Topic<readonly ResourceSummary[]>
  readonly folderNames: ReadonlyMap<string, string>
}

/** Días que cubre la torre del calendario (la agenda de `jarvis/data` va de hoy a +7). */
export const CALENDAR_DAYS = 8
export const HABIT_DAYS = 28

const loadOf = (t: Topic<unknown>): Load => (t.data !== null ? 'ready' : t.status === 'loading' ? 'loading' : 'error')

/** Hora local decimal de un «AAAA-MM-DDTHH:MM[:SS]». */
const hoursOf = (local: string): number => {
  const m = /T(\d{2}):(\d{2})/.exec(local)
  return m ? Number(m[1]) + Number(m[2]) / 60 : 0
}

/** Hora local decimal de `now` en la zona del usuario. */
export function nowHoursIn(now: Date, timeZone: string): number {
  const parts = new Intl.DateTimeFormat('en-GB', { timeZone, hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).formatToParts(now)
  const get = (t: string): number => Number(parts.find((p) => p.type === t)?.value ?? 0)
  return (get('hour') % 24) + get('minute') / 60 + get('second') / 3600
}

function kindOf(sourceType: string, kind: string): HmEventKind {
  if (sourceType === 'class_session') return 'clase'
  if (sourceType === 'time_block') return 'bloque'
  return kind === 'reminder' ? 'recordatorio' : 'evento'
}

function eventFrom(
  e: Pick<AgendaItem, 'occurrence_id' | 'title' | 'all_day' | 'display_start' | 'display_end' | 'start_date' | 'color' | 'room' | 'source_id' | 'kind'> & { readonly source_type: string; readonly location?: string | null },
  today: string
): HmEvent | null {
  const startDate = e.display_start?.slice(0, 10) ?? e.start_date
  if (!startDate) return null
  const day = daysBetween(today, startDate)
  const endDate = e.display_end?.slice(0, 10) ?? startDate
  const start = e.all_day || !e.display_start ? 0 : hoursOf(e.display_start)
  const end = e.all_day || !e.display_end ? 24 : endDate > startDate ? 24 : hoursOf(e.display_end)
  const st = e.source_type
  return {
    id: e.occurrence_id,
    title: e.title,
    day,
    start,
    end: Math.max(start, end),
    allDay: e.all_day,
    kind: kindOf(st, e.kind),
    color: parseColor(e.color),
    place: e.room ?? e.location ?? null,
    sourceType: st === 'class_session' || st === 'time_block' ? st : 'calendar_event',
    sourceId: e.source_id
  }
}

/** «hoy», «mañana», «vie 28» o «12 dic». */
function dueLabel(date: string, today: string): string {
  const d = daysBetween(today, date)
  if (d === 0) return 'hoy'
  if (d === 1) return 'mañana'
  if (d === -1) return 'ayer'
  if (d > 1 && d < 7) return `${weekdayShort(date).toLowerCase()} ${Number(date.slice(8, 10))}`
  return shortDayLabel(date).replace('.', '')
}

const dueDateOf = (t: Pick<Task, 'due_date' | 'due_at'>, tz: string): string | null => {
  if (t.due_date) return t.due_date
  if (!t.due_at) return null
  return new Intl.DateTimeFormat('en-CA', { timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(t.due_at))
}

const COLUMN: Record<Task['status'], HmColumn | null> = { pending: 0, on_hold: 0, in_progress: 1, completed: 2, cancelled: null }

function adaptTasks(tasks: readonly Task[], projects: ReadonlyMap<string, string>, today: string, tz: string): HmTask[] {
  const weekAgo = addDays(today, -7)
  return tasks.flatMap((t) => {
    const column = COLUMN[t.status]
    if (column === null || t.archived_at) return []
    // Las hechas solo cuentan si son de la última semana (la pila no crece sin fin).
    if (column === 2 && (!t.completed_at || formatDate(new Date(t.completed_at)) < weekAgo)) return []
    const due = dueDateOf(t, tz)
    const open = column !== 2
    return [{
      id: t.id,
      title: t.title,
      status: t.status,
      column,
      priority: t.priority,
      project: t.project_id ? (projects.get(t.project_id) ?? null) : null,
      due: due ? dueLabel(due, today) : null,
      overdue: open && due !== null && due < today,
      dueSoon: open && due !== null && due >= today && daysBetween(today, due) <= 2,
      estimatedMin: t.estimated_minutes,
      revision: t.revision
    }]
  })
}

function adaptProjects(projects: readonly Project[], today: string): HmProject[] {
  const rank = { urgent: 0, high: 1, medium: 2, low: 3 } as const
  return projects
    .filter((p) => !p.archived_at && (p.status === 'active' || p.status === 'planned' || p.status === 'paused'))
    .sort((a, b) => Number(b.status === 'active') - Number(a.status === 'active') || rank[a.priority] - rank[b.priority] || a.name.localeCompare(b.name))
    .map((p) => {
      const pct = p.progress.percent
      return {
        id: p.id,
        name: p.name,
        progress: Math.max(0, Math.min(1, pct > 1 ? pct / 100 : pct)),
        total: p.progress.total,
        completed: p.progress.completed,
        overdue: p.progress.overdue,
        due: p.target_date ? dueLabel(p.target_date, today) : null
      }
    })
}

function adaptHabits(habits: readonly Habit[], stats: ReadonlyMap<string, HabitStatsEntry>, today: string): HmHabit[] {
  const from = addDays(today, -(HABIT_DAYS - 1))
  return habits
    .filter((h) => !h.archived_at && h.status === 'active')
    .map((h) => {
      const entry = stats.get(h.id)
      const byDate = new Map(entry?.history?.days.map((d) => [d.date, d]) ?? [])
      const days: HmHabitDay[] = Array.from({ length: HABIT_DAYS }, (_, i) => {
        const date = addDays(from, i)
        const d = byDate.get(date)
        if (date === today) return h.today_scheduled ? (h.today_status === 'done' ? 'done' : h.today_status ?? 'open') : d?.status ?? null
        if (!d || !d.scheduled) return d?.status ?? null
        return d.status ?? 'missed'
      })
      return {
        id: h.id,
        name: h.name,
        days,
        streak: entry?.stats?.current_streak ?? 0,
        best: entry?.stats?.best_streak ?? 0,
        goal: h.goal_note,
        todayScheduled: h.today_scheduled,
        todayDone: h.today_status === 'done',
        revision: h.revision
      }
    })
}

function adaptFiles(resources: readonly ResourceSummary[], folders: ReadonlyMap<string, string>): HmFile[] {
  return resources
    .filter((r) => !r.archived_at)
    .map((r) => ({
      id: r.id,
      title: r.title,
      type: r.resource_type,
      sizeBytes: r.size_bytes,
      folder: r.folder_id ? (folders.get(r.folder_id) ?? 'carpeta') : null,
      index: r.index_status
    }))
}

function adaptGraph(rels: readonly RelationshipOut[], titles: ReadonlyMap<string, string>): { nodes: HmNode[]; edges: [string, string][] } {
  const nodes = new Map<string, HmNode>()
  const add = (id: string, kind: EntityType): void => {
    if (!nodes.has(id)) nodes.set(id, { id, kind, label: titles.get(id) ?? ENTITY_TYPE_LABEL[kind] })
  }
  const edges: [string, string][] = []
  for (const r of rels) {
    add(r.source_id, r.source_type)
    add(r.target_id, r.target_type)
    edges.push([r.source_id, r.target_id])
  }
  return { nodes: [...nodes.values()], edges }
}

export function buildSnapshot(input: AdaptInput): HoloSnapshot {
  const tz = input.timezone
  const today = input.today.data?.date ?? todayIn(tz)
  const nowHours = nowHoursIn(input.now, tz)
  const projectsRaw = input.projects.data ?? []
  const projectNames = new Map(projectsRaw.map((p) => [p.id, p.name]))
  for (const p of input.today.data?.projects.items ?? []) if (!projectNames.has(p.id)) projectNames.set(p.id, p.name)

  // Agenda: la del calendario (hoy … +7) y, si aún no llegó, la de `/today` para el dial.
  const agendaEvents = (input.agenda.data ?? []).flatMap((e) => eventFrom(e, today) ?? []).filter((e) => e.day >= 0 && e.day < CALENDAR_DAYS && e.end > e.start - 0.001)
  const todayAgenda: readonly TodayAgendaEntry[] = input.today.data?.agenda.items ?? []
  const todayEvents =
    input.agenda.data !== null
      ? agendaEvents.filter((e) => e.day === 0)
      : todayAgenda.flatMap((e) => eventFrom({ ...e, start_date: today }, today) ?? []).filter((e) => e.day === 0)

  const tasks = adaptTasks(input.tasks.data ?? [], projectNames, today, tz)
  const doneToday = tasks.filter((t) => t.column === 2).length > 0
    ? (input.tasks.data ?? []).filter((t) => t.status === 'completed' && t.completed_at && formatDate(new Date(t.completed_at)) === today).length
    : 0
  const dueToday = (input.today.data?.due_today.total ?? tasks.filter((t) => t.due === 'hoy' && t.column !== 2).length) + doneToday

  const subjects = new Map<string, { id: string; name: string; color: number | null }>()
  for (const e of input.agenda.data ?? [])
    if (e.subject_id && e.source_type === 'class_session' && !subjects.has(e.subject_id)) subjects.set(e.subject_id, { id: e.subject_id, name: e.title, color: parseColor(e.color) })

  const titles = new Map<string, string>()
  for (const t of input.tasks.data ?? []) titles.set(t.id, t.title)
  for (const p of projectsRaw) titles.set(p.id, p.name)
  for (const h of input.habits.data ?? []) titles.set(h.id, h.name)
  for (const r of input.resources.data ?? []) titles.set(r.id, r.title)
  for (const s of subjects.values()) titles.set(s.id, s.name)
  for (const e of input.agenda.data ?? []) if (!titles.has(e.source_id)) titles.set(e.source_id, e.title)
  for (const [id, name] of input.folderNames) titles.set(id, name)

  const files = adaptFiles(input.resources.data ?? [], input.folderNames)
  const startLabel = parseDate(today)
  return {
    now: input.now,
    timezone: tz,
    nowHours,
    today: {
      load: input.today.data !== null || input.agenda.data !== null ? 'ready' : loadOf(input.today),
      events: todayEvents,
      dueToday,
      doneToday,
      label: new Intl.DateTimeFormat('es-ES', { weekday: 'long', day: 'numeric', month: 'long' }).format(startLabel)
    },
    calendar: {
      load: loadOf(input.agenda),
      days: Array.from({ length: CALENDAR_DAYS }, (_, i) => {
        const d = addDays(today, i)
        return `${weekdayShort(d).toLowerCase()} ${Number(d.slice(8, 10))}`
      }),
      todayIndex: 0,
      events: agendaEvents,
      subjects: [...subjects.values()]
    },
    tasks: { load: loadOf(input.tasks), items: tasks },
    projects: { load: loadOf(input.projects), items: adaptProjects(projectsRaw, today) },
    habits: { load: loadOf(input.habits), items: adaptHabits(input.habits.data ?? [], input.habitStats, today) },
    graph: { load: loadOf(input.relationships), ...adaptGraph(input.relationships.data ?? [], titles) },
    files: { load: loadOf(input.resources), items: files, total: files.length, pending: files.filter((f) => f.index === 'pending' || f.index === 'failed').length }
  }
}
