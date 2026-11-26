/**
 * Instantáneas reales del Workspace (`jarvis/data`, D1) → modelo de vista de la Holomesa. Funciones
 * puras, sin red. Lo que no ha llegado queda en `loading`; lo que falló sin dato previo, en `error`.
 * Nada se inventa: una sección sin datos se dibuja vacía y lo dice.
 */
import type { JarvisData, Snapshot } from '@/jarvis/data'
import { addDays, daysBetween, shortDayLabel, todayIn, weekdayShort } from '@/modules/calendar/dateUtils'
import type { AgendaItem } from '@/modules/calendar/types'
import type { Habit, HabitHistoryDay } from '@/modules/habits/types'
import type { Project } from '@/modules/projects/types'
import { ENTITY_TYPE_LABEL } from '@/modules/relationships/types'
import type { Task } from '@/modules/tasks/types'
import type { TodayAgendaEntry } from '@/pages/today/contract'
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

/** Temas de `jarvis/data` que usa la Holomesa (constante de módulo: lista estable entre renders). */
export const HOLO_TOPICS = ['today', 'tasks', 'projects', 'habits', 'habitHistory', 'agenda', 'relationships', 'resources', 'folders', 'subjects', 'entityNames'] as const
export type HoloTopics = Pick<JarvisData, (typeof HOLO_TOPICS)[number]>

/** Días que cubre la torre del calendario (la agenda de D1 va de hoy a +7). */
export const CALENDAR_DAYS = 7
export const HABIT_DAYS = 28

const loadOf = (t: Snapshot<unknown>): Load => (t.data !== null ? 'ready' : t.status === 'loading' ? 'loading' : 'error')

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

const dateIn = (iso: string, tz: string): string =>
  new Intl.DateTimeFormat('en-CA', { timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(iso))

function kindOf(sourceType: string, kind: string): HmEventKind {
  if (sourceType === 'class_session') return 'clase'
  if (sourceType === 'time_block') return 'bloque'
  return kind === 'reminder' ? 'recordatorio' : 'evento'
}

type EventSource = Pick<AgendaItem, 'occurrence_id' | 'title' | 'all_day' | 'display_start' | 'display_end' | 'start_date' | 'color' | 'room' | 'source_id' | 'kind'> & {
  readonly source_type: string
  readonly location?: string | null
  readonly subject_id?: string | null
}

function eventFrom(e: EventSource, today: string, subjectColor: ReadonlyMap<string, number | null>): HmEvent | null {
  const startDate = e.display_start?.slice(0, 10) ?? e.start_date
  if (!startDate) return null
  const endDate = e.display_end?.slice(0, 10) ?? startDate
  const start = e.all_day || !e.display_start ? 0 : hoursOf(e.display_start)
  const end = e.all_day || !e.display_end ? 24 : endDate > startDate ? 24 : hoursOf(e.display_end)
  const st = e.source_type
  return {
    id: e.occurrence_id,
    title: e.title,
    day: daysBetween(today, startDate),
    start,
    end: Math.max(start + 0.05, end),
    allDay: e.all_day,
    kind: kindOf(st, e.kind),
    color: parseColor(e.color) ?? (e.subject_id ? (subjectColor.get(e.subject_id) ?? null) : null),
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

const COLUMN: Record<Task['status'], HmColumn | null> = { pending: 0, in_progress: 1, on_hold: 2, completed: null, cancelled: null }

function adaptTasks(tasks: readonly Task[], projects: ReadonlyMap<string, string>, today: string, tz: string): HmTask[] {
  return tasks.flatMap((t) => {
    const column = COLUMN[t.status]
    if (column === null || t.archived_at) return []
    const due = t.due_date ?? (t.due_at ? dateIn(t.due_at, tz) : null)
    return [{
      id: t.id,
      title: t.title,
      status: t.status,
      column,
      priority: t.priority,
      project: t.project_id ? (projects.get(t.project_id) ?? null) : null,
      due: due ? dueLabel(due, today) : null,
      overdue: due !== null && due < today,
      dueSoon: due !== null && due >= today && daysBetween(today, due) <= 2,
      estimatedMin: t.estimated_minutes,
      revision: t.revision
    }]
  })
}

function adaptProjects(projects: readonly Project[], today: string): HmProject[] {
  const rank = { urgent: 0, high: 1, medium: 2, low: 3 } as const
  return projects
    .filter((p) => !p.archived_at && p.status !== 'completed' && p.status !== 'cancelled')
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

/** Racha actual (días que tocaban, seguidos y cumplidos; hoy sin marcar no la rompe) y mejor racha de la ventana. */
function streaks(days: readonly HmHabitDay[]): { current: number; best: number } {
  let best = 0, run = 0
  for (const d of days) {
    if (d === null) continue
    if (d === 'done') best = Math.max(best, ++run)
    else if (d !== 'open') run = 0
  }
  let current = 0
  for (let i = days.length - 1; i >= 0; i--) {
    const d = days[i]
    if (d === null || (d === 'open' && i === days.length - 1)) continue
    if (d === 'done') current++
    else break
  }
  return { current, best }
}

function adaptHabits(habits: readonly Habit[], history: Readonly<Record<string, readonly HabitHistoryDay[]>>, today: string): HmHabit[] {
  const from = addDays(today, -(HABIT_DAYS - 1))
  return habits
    .filter((h) => !h.archived_at && h.status === 'active')
    .map((h) => {
      const byDate = new Map((history[h.id] ?? []).map((d) => [d.date, d]))
      const days: HmHabitDay[] = Array.from({ length: HABIT_DAYS }, (_, i) => {
        const date = addDays(from, i)
        const d = byDate.get(date)
        if (date === today) return h.today_scheduled ? (h.today_status ?? 'open') : null
        if (!d || !d.scheduled) return d?.status ?? null
        return d.status ?? 'missed'
      })
      const { current, best } = streaks(days)
      return {
        id: h.id,
        name: h.name,
        days,
        streak: current,
        best,
        goal: h.goal_note,
        todayScheduled: h.today_scheduled,
        todayDone: h.today_status === 'done',
        revision: h.revision
      }
    })
}

export function buildSnapshot(d: HoloTopics, now: Date): HoloSnapshot {
  const todayData = d.today.data
  const tz = todayData?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone
  const today = todayData?.date ?? todayIn(tz)
  const projectsRaw = d.projects.data ?? []
  const projectNames = new Map(projectsRaw.map((p) => [p.id, p.name]))
  for (const p of todayData?.projects.items ?? []) if (!projectNames.has(p.id)) projectNames.set(p.id, p.name)
  const subjectsRaw = (d.subjects.data ?? []).filter((s) => !s.archived_at)
  const subjectColor = new Map(subjectsRaw.map((s) => [s.id, parseColor(s.color)]))

  // Agenda: la de D1 (hoy … +7) y, si aún no llegó, la de `/today` para el dial.
  const agendaEvents = (d.agenda.data ?? []).flatMap((e) => eventFrom(e, today, subjectColor) ?? []).filter((e) => e.day >= 0 && e.day < CALENDAR_DAYS)
  const todayAgenda: readonly TodayAgendaEntry[] = todayData?.agenda.items ?? []
  const todayEvents =
    d.agenda.data !== null
      ? agendaEvents.filter((e) => e.day === 0)
      : todayAgenda.flatMap((e) => eventFrom({ ...e, start_date: today, room: e.room }, today, subjectColor) ?? []).filter((e) => e.day === 0)

  const habitsToday = todayData?.habits.items ?? []
  const names = d.entityNames.data
  const folderNames = new Map((d.folders.data ?? []).map((f) => [f.id, f.name]))
  const files: HmFile[] = (d.resources.data ?? [])
    .filter((r) => !r.archived_at)
    .map((r) => ({ id: r.id, title: r.title, type: r.resource_type, sizeBytes: r.size_bytes, folder: r.folder_id ? (folderNames.get(r.folder_id) ?? 'subcarpeta') : null, index: r.index_status }))

  const nodes = new Map<string, HmNode>()
  const edges: [string, string][] = []
  for (const r of d.relationships.data ?? []) {
    for (const [id, type] of [[r.source_id, r.source_type], [r.target_id, r.target_type]] as const)
      if (!nodes.has(id)) nodes.set(id, { id, kind: type, label: names?.get(id)?.name ?? folderNames.get(id) ?? ENTITY_TYPE_LABEL[type] })
    edges.push([r.source_id, r.target_id])
  }

  return {
    now,
    timezone: tz,
    nowHours: nowHoursIn(now, tz),
    today: {
      load: todayData !== null || d.agenda.data !== null ? 'ready' : loadOf(d.today),
      events: todayEvents,
      tasksToday: todayData?.due_today.total ?? 0,
      overdue: todayData?.overdue.total ?? 0,
      habitsDue: habitsToday.length,
      habitsDone: habitsToday.filter((h) => h.today_status === 'done').length,
      label: new Intl.DateTimeFormat('es-ES', { weekday: 'long', day: 'numeric', month: 'long', timeZone: tz }).format(now)
    },
    calendar: {
      load: loadOf(d.agenda),
      days: Array.from({ length: CALENDAR_DAYS }, (_, i) => {
        const day = addDays(today, i)
        return `${weekdayShort(day).toLowerCase()} ${Number(day.slice(8, 10))}`
      }),
      todayIndex: 0,
      events: agendaEvents,
      subjects: subjectsRaw.map((s) => ({ id: s.id, name: s.name, color: parseColor(s.color) }))
    },
    tasks: { load: loadOf(d.tasks), items: adaptTasks(d.tasks.data ?? [], projectNames, today, tz) },
    projects: { load: loadOf(d.projects), items: adaptProjects(projectsRaw, today) },
    habits: { load: loadOf(d.habits), items: adaptHabits(d.habits.data ?? [], d.habitHistory.data ?? {}, today) },
    graph: { load: loadOf(d.relationships), nodes: [...nodes.values()], edges },
    files: { load: loadOf(d.resources), items: files, total: files.length, pending: files.filter((f) => f.index === 'pending' || f.index === 'failed').length }
  }
}
