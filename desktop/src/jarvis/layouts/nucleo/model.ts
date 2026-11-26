/**
 * Modelo de vista de Núcleo: convierte los datos REALES del Workspace (tipos de dominio que entrega
 * `jarvis/data`) en lo que dibujan los anillos. Funciones puras, sin red. Lo que no existe en los datos
 * no se inventa: el campo queda vacío o `null` y el anillo lo oculta.
 * Los textos son datos no confiables: el kit los pinta glifo a glifo y React como texto plano.
 */
import type { AgendaItem } from '@/modules/calendar/types'
import type { Habit, HabitHistoryDay } from '@/modules/habits/types'
import type { Project } from '@/modules/projects/types'
import type { EntityType, RelationshipKind, RelationshipOut } from '@/modules/relationships/types'
import type { IndexStatus, ResourceSummary, ResourceType } from '@/modules/storage/types'
import type { Subject, TimetableEntry } from '@/modules/subjects/types'
import type { Priority, Task } from '@/modules/tasks/types'
import type { TodayResponse, TodayTask } from '@/pages/today/contract'
import { SERIES, type ColorName } from './gl/kit'

export type Tone = 'late' | 'soon' | 'open' | 'done'

/** Ids numéricos estables (los shaders seleccionan por número). Nunca se reasignan en la sesión. */
export class IdMap {
  private map = new Map<string, number>()
  private back: string[] = ['']
  num(id: string): number {
    let n = this.map.get(id)
    if (n === undefined) {
      n = this.back.length
      this.map.set(id, n)
      this.back.push(id)
    }
    return n
  }
  id(num: number): string | null { return this.back[num] ?? null }
}

export interface VTask {
  readonly id: string
  readonly num: number
  readonly title: string
  readonly done: boolean
  readonly tone: Tone
  readonly dueText: string
  /** Días hasta el vencimiento (negativo = vencida); `null` sin fecha. */
  readonly dueDays: number | null
  readonly prio: 1 | 2 | 3
  readonly priority: Priority
  readonly projectId: string | null
  readonly projectName: string | null
  /** Para escribir: la API pide la revisión (si viene de /today no la hay y se lee de `tasks`). */
  readonly revision: number | null
}
export interface VProject {
  readonly id: string
  readonly num: number
  readonly name: string
  readonly percent: number
  readonly col: ColorName
  readonly open: number
  readonly overdue: number
}
export interface VEvent {
  readonly id: string
  readonly num: number
  readonly title: string
  /** Día relativo a hoy (0 = hoy … 6). */
  readonly day: number
  /** Horas locales decimales. */
  readonly start: number
  readonly end: number
  readonly allDay: boolean
  readonly col: ColorName
  readonly kind: string
  readonly subject: string | null
  readonly room: string | null
}
export interface VHabit {
  readonly id: string
  readonly num: number
  readonly name: string
  readonly col: ColorName
  /** 28 días (el último es hoy): true hecho, false tocaba y no, null no tocaba. `null` = sin historial. */
  readonly days: readonly (boolean | null)[] | null
  readonly todayDone: boolean
  readonly todayScheduled: boolean
  readonly streak: number | null
  readonly rate: number | null
  readonly revision: number
}
export interface VNode { readonly num: number; readonly id: string; readonly name: string; readonly type: EntityType; deg: number }
export interface VEdge { readonly a: number; readonly b: number; readonly rel: RelationshipKind }
export interface VStoreGroup { readonly num: number; readonly key: string; readonly name: string; readonly count: number; readonly col: ColorName; readonly kids: readonly { readonly num: number; readonly key: string; readonly name: string; readonly count: number }[] }
export interface VStore {
  readonly total: number
  readonly indexed: number
  readonly pending: number
  readonly failed: number
  readonly bytes: number
  readonly groups: readonly VStoreGroup[]
  /** Recursos tocados por día, de hace 59 días a hoy. */
  readonly perDay: readonly number[]
  readonly recent: readonly { readonly id: string; readonly title: string; readonly type: string; readonly when: string; readonly status: IndexStatus }[]
}
export interface VSubject { readonly id: string; readonly name: string; readonly short: string; readonly col: ColorName; readonly weekHours: number }

export interface NucleoModel {
  readonly tz: string
  readonly todayKey: string
  readonly nowHour: number
  /** 0 = lunes. */
  readonly todayDow: number
  readonly todayEvents: readonly VEvent[] | null
  readonly todayTasks: readonly VTask[] | null
  readonly tasks: readonly VTask[] | null
  readonly projects: readonly VProject[] | null
  readonly habits: readonly VHabit[] | null
  readonly week: readonly VEvent[] | null
  /** Tareas con fecha en los próximos 35 días, por día. */
  readonly dueStrip: readonly number[] | null
  readonly subjects: readonly VSubject[] | null
  readonly graph: { readonly nodes: readonly VNode[]; readonly edges: readonly VEdge[] } | null
  readonly store: VStore | null
}

export interface ModelInput {
  readonly today: TodayResponse | null
  readonly tasks: readonly Task[] | null
  readonly projects: readonly Project[] | null
  readonly habits: readonly Habit[] | null
  readonly habitHistory?: Readonly<Record<string, readonly HabitHistoryDay[]>> | null
  readonly agenda: readonly AgendaItem[] | null
  readonly timetable: readonly TimetableEntry[] | null
  readonly subjects?: readonly Subject[] | null
  readonly relationships: readonly RelationshipOut[] | null
  readonly entityNames?: Readonly<Record<string, string>> | null
  readonly resources: readonly ResourceSummary[] | null
  /** Tareas marcadas en esta sesión (hasta que la recarga las saque de la lista de abiertas). */
  readonly doneLocal: ReadonlySet<string>
  readonly ids: IdMap
}

// ── Fechas en la zona del usuario.
const pad2 = (n: number): string => String(n).padStart(2, '0')
export const hm = (h: number): string => { const m = Math.round(h * 60); return `${pad2(Math.floor(m / 60) % 24)}:${pad2(m % 60)}` }
export function zonedNow(tz: string, at = new Date()): { key: string; hour: number; dow: number } {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23', weekday: 'short' }).formatToParts(at)
  const g = (t: string): string => parts.find((p) => p.type === t)?.value ?? ''
  const dow = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].indexOf(g('weekday'))
  return { key: `${g('year')}-${g('month')}-${g('day')}`, hour: Number(g('hour')) + Number(g('minute')) / 60, dow: Math.max(0, dow) }
}
const dayMs = 86_400_000
const keyToUtc = (key: string): number => Date.UTC(Number(key.slice(0, 4)), Number(key.slice(5, 7)) - 1, Number(key.slice(8, 10)))
export const daysBetween = (fromKey: string, toKey: string): number => Math.round((keyToUtc(toKey) - keyToUtc(fromKey)) / dayMs)
export const addDays = (key: string, n: number): string => new Date(keyToUtc(key) + n * dayMs).toISOString().slice(0, 10)
/** 'AAAA-MM-DDTHH:MM…' local → horas decimales. */
const hoursOf = (s: string): number => Number(s.slice(11, 13)) + Number(s.slice(14, 16)) / 60
const DOW_ES = ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom']
export const dow3 = (todayDow: number, offset: number): string => DOW_ES[(((todayDow + offset) % 7) + 7) % 7]!
export const dayNum = (todayKey: string, offset: number): number => Number(addDays(todayKey, offset).slice(8, 10))

/** Color estable de la paleta fría por id (el color significa algo: nada de colores arbitrarios). */
export function seriesColor(id: string): ColorName {
  let h = 0
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) | 0
  return SERIES[Math.abs(h) % SERIES.length]!
}

const PRIO: Readonly<Record<Priority, 1 | 2 | 3>> = { low: 1, medium: 1, high: 2, urgent: 3 }

function dueOf(t: Pick<Task, 'due_date' | 'due_at'>, todayKey: string, tz: string): number | null {
  if (t.due_date) return daysBetween(todayKey, t.due_date)
  if (t.due_at) return daysBetween(todayKey, zonedNow(tz, new Date(t.due_at)).key)
  return null
}
export function dueText(d: number | null): string {
  if (d === null) return 'sin fecha'
  if (d < -1) return `venció hace ${-d} días`
  if (d === -1) return 'venció ayer'
  if (d === 0) return 'vence hoy'
  if (d === 1) return 'mañana'
  return `en ${d} días`
}
const toneOf = (done: boolean, d: number | null): Tone => (done ? 'done' : d !== null && d < 0 ? 'late' : d !== null && d <= 1 ? 'soon' : 'open')

function vTask(t: Task | TodayTask, m: ModelInput, todayKey: string, tz: string, projectName: string | null): VTask {
  const done = m.doneLocal.has(t.id) || ('status' in t && t.status === 'completed')
  const d = dueOf(t, todayKey, tz)
  return {
    id: t.id, num: m.ids.num(t.id), title: t.title, done, tone: toneOf(done, d), dueText: dueText(d), dueDays: d,
    prio: PRIO[t.priority], priority: t.priority, projectId: t.project_id, projectName,
    revision: 'revision' in t ? t.revision : null
  }
}

function vEvent(a: AgendaItem, m: ModelInput, todayKey: string, subjectName: (id: string | null) => string | null): VEvent | null {
  const startS = a.display_start ?? (a.start_date ? `${a.start_date}T00:00` : null)
  if (!startS) return null
  const day = daysBetween(todayKey, startS.slice(0, 10))
  if (day < 0 || day > 6) return null
  const start = a.all_day ? 0 : hoursOf(startS)
  let end = a.all_day ? 24 : a.display_end ? hoursOf(a.display_end) : start + 1
  if (a.display_end && a.display_end.slice(0, 10) !== startS.slice(0, 10)) end = 24
  return {
    id: a.occurrence_id, num: m.ids.num(a.occurrence_id), title: a.title, day, start, end: Math.max(end, start + 0.25), allDay: a.all_day,
    col: a.subject_id ? seriesColor(a.subject_id) : a.kind === 'time_block' || a.kind === 'work_session' ? 'blue' : 'cyan',
    kind: a.kind, subject: subjectName(a.subject_id), room: a.room ?? a.location
  }
}

const TYPE_ES: Readonly<Record<ResourceType, string>> = {
  image: 'Imágenes', document: 'Documentos', pdf: 'PDF', text: 'Texto', code: 'Código', link: 'Enlaces', note: 'Notas', study_note: 'Apuntes', archive: 'Comprimidos', other: 'Otros'
}
const INDEX_ES: Readonly<Record<IndexStatus, string>> = { indexed: 'indexado', pending: 'pendiente', failed: 'con error', none: 'sin indexar', skipped: 'omitido' }
export const indexLabel = (s: IndexStatus): string => INDEX_ES[s]

export function buildModel(m: ModelInput, at = new Date()): NucleoModel {
  const tz = m.today?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone
  const now = zonedNow(tz, at)
  const todayKey = m.today?.date ?? now.key
  const projectName = new Map((m.projects ?? []).map((p) => [p.id, p.name]))
  const subjectNames = new Map<string, string>()
  for (const s of m.subjects ?? []) subjectNames.set(s.id, s.name)
  for (const e of m.timetable ?? []) subjectNames.set(e.subject_id, e.subject_name)
  const subjectName = (id: string | null): string | null => (id ? subjectNames.get(id) ?? null : null)

  // Hoy: agenda (incluye clases) y tareas vencidas o de hoy.
  const week = m.agenda ? m.agenda.map((a) => vEvent(a, m, todayKey, subjectName)).filter((e): e is VEvent => e !== null) : null
  if (week) for (const e of week) if (e.subject) subjectNames.set(e.subject, e.subject)
  const todayEvents = week ? week.filter((e) => e.day === 0 && !e.allDay).sort((a, b) => a.start - b.start) : null
  const todayTasks = m.today
    ? [...(m.today.overdue.status === 'ready' ? m.today.overdue.items : []), ...(m.today.due_today.status === 'ready' ? m.today.due_today.items : [])].map((t) => vTask(t, m, todayKey, tz, t.project_name))
    : null

  const tasks = m.tasks ? m.tasks.filter((t) => t.status !== 'cancelled' && !t.archived_at).map((t) => vTask(t, m, todayKey, tz, t.project_id ? projectName.get(t.project_id) ?? null : null)) : null
  const projects = m.projects
    ? m.projects.filter((p) => !p.archived_at).map((p) => ({ id: p.id, num: m.ids.num(p.id), name: p.name, percent: Math.max(0, Math.min(1, p.progress.percent / 100)), col: seriesColor(p.id), open: p.progress.open, overdue: p.progress.overdue }))
      .sort((a, b) => b.open - a.open)
    : null

  const habits = m.habits
    ? m.habits.filter((h) => !h.archived_at && h.status === 'active').map((h): VHabit => {
        const hist = m.habitHistory?.[h.id] ?? null
        let days: (boolean | null)[] | null = null
        let streak: number | null = null
        let rate: number | null = null
        if (hist) {
          const byDate = new Map(hist.map((d) => [d.date, d]))
          days = Array.from({ length: 28 }, (_, i) => { const d = byDate.get(addDays(todayKey, i - 27)); return !d || !d.scheduled ? null : d.status === 'done' })
          days[27] = h.today_scheduled ? h.today_status === 'done' || m.doneLocal.has(`habit:${h.id}`) : null
          const sched = days.filter((x) => x !== null)
          rate = sched.length ? sched.filter(Boolean).length / sched.length : null
          streak = 0
          for (let i = 27; i >= 0; i--) { const v = days[i]; if (v === null || (i === 27 && v === false)) continue; if (!v) break; streak++ }
        }
        return { id: h.id, num: m.ids.num(h.id), name: h.name, col: seriesColor(h.id), days, todayDone: h.today_status === 'done' || m.doneLocal.has(`habit:${h.id}`), todayScheduled: h.today_scheduled, streak, rate, revision: h.revision }
      })
    : null

  const dueStrip = m.tasks ? Array.from({ length: 35 }, () => 0) : null
  if (dueStrip && tasks) for (const t of tasks) if (!t.done && t.dueDays !== null && t.dueDays >= 0 && t.dueDays < 35) dueStrip[t.dueDays]!++

  // Asignaturas: horas de clase de la semana a partir de la agenda.
  const hours = new Map<string, number>()
  for (const e of week ?? []) if (e.kind === 'class' || e.subject) { const k = e.subject ?? e.title; hours.set(k, (hours.get(k) ?? 0) + (e.end - e.start)) }
  const subjSrc = m.subjects?.length ? m.subjects.map((s) => ({ id: s.id, name: s.name })) : [...subjectNames.entries()].map(([id, name]) => ({ id, name }))
  const seen = new Set<string>()
  const subjects = m.subjects || m.timetable || week
    ? subjSrc.filter((s) => (seen.has(s.name) ? false : (seen.add(s.name), true))).map((s) => ({ id: s.id, name: s.name, short: shortName(s.name), col: seriesColor(s.id), weekHours: hours.get(s.name) ?? 0 }))
    : null

  // Relaciones: nodos de ambos extremos, con el nombre que conozcamos.
  let graph: NucleoModel['graph'] = null
  if (m.relationships) {
    const names = new Map<string, string>(Object.entries(m.entityNames ?? {}))
    for (const t of m.tasks ?? []) names.set(t.id, t.title)
    for (const p of m.projects ?? []) names.set(p.id, p.name)
    for (const h of m.habits ?? []) names.set(h.id, h.name)
    for (const r of m.resources ?? []) names.set(r.id, r.title)
    for (const [id, n] of subjectNames) names.set(id, n)
    const nodes: VNode[] = [], index = new Map<string, number>(), edges: VEdge[] = []
    const node = (id: string, type: EntityType): number => {
      let i = index.get(id)
      if (i === undefined) { i = nodes.length; index.set(id, i); nodes.push({ num: m.ids.num(id), id, name: names.get(id) ?? ENTITY_ES[type], type, deg: 0 }) }
      return i
    }
    for (const r of m.relationships.slice(0, 400)) {
      const a = node(r.source_id, r.source_type), b = node(r.target_id, r.target_type)
      if (a === b) continue
      nodes[a]!.deg++
      nodes[b]!.deg++
      edges.push({ a, b, rel: r.relationship_type })
    }
    graph = { nodes, edges }
  }

  let store: VStore | null = null
  if (m.resources) {
    const res = m.resources.filter((r) => !r.archived_at)
    const byType = new Map<ResourceType, ResourceSummary[]>()
    for (const r of res) { const l = byType.get(r.resource_type) ?? []; l.push(r); byType.set(r.resource_type, l) }
    const groups = [...byType.entries()].sort((a, b) => b[1].length - a[1].length).slice(0, 6).map(([type, list], i): VStoreGroup => {
      const st = new Map<IndexStatus, number>()
      for (const r of list) st.set(r.index_status, (st.get(r.index_status) ?? 0) + 1)
      return {
        num: m.ids.num(`type:${type}`), key: type, name: TYPE_ES[type], count: list.length, col: SERIES[i % SERIES.length]!,
        kids: [...st.entries()].sort((a, b) => b[1] - a[1]).map(([s, n]) => ({ num: m.ids.num(`type:${type}:${s}`), key: s, name: INDEX_ES[s], count: n }))
      }
    })
    const perDay = Array.from({ length: 60 }, () => 0)
    for (const r of res) { const d = daysBetween(zonedNow(tz, new Date(r.updated_at)).key, todayKey); if (d >= 0 && d < 60) perDay[59 - d]!++ }
    store = {
      total: res.length, indexed: res.filter((r) => r.index_status === 'indexed').length, pending: res.filter((r) => r.index_status === 'pending').length,
      failed: res.filter((r) => r.index_status === 'failed').length, bytes: res.reduce((a, r) => a + (r.size_bytes ?? 0), 0), groups, perDay,
      recent: [...res].sort((a, b) => b.updated_at.localeCompare(a.updated_at)).slice(0, 6).map((r) => ({ id: r.id, title: r.title, type: TYPE_ES[r.resource_type], when: whenText(daysBetween(zonedNow(tz, new Date(r.updated_at)).key, todayKey)), status: r.index_status }))
    }
  }

  return { tz, todayKey, nowHour: now.hour, todayDow: now.dow, todayEvents, todayTasks, tasks, projects, habits, week, dueStrip, subjects, graph, store }
}

export const ENTITY_ES: Readonly<Record<EntityType, string>> = {
  task: 'Tarea', project: 'Proyecto', habit: 'Hábito', calendar_event: 'Evento', time_block: 'Bloque', subject: 'Asignatura', class_session: 'Clase', resource: 'Recurso', folder: 'Carpeta'
}
export const REL_ES: Readonly<Record<RelationshipKind, string>> = {
  belongs_to: 'pertenece a', related_to: 'relacionado con', scheduled_for: 'programado para', uses_resource: 'usa', depends_on: 'depende de',
  supports: 'apoya', studies: 'estudia', parent_of: 'contiene', references: 'cita', derived_from: 'deriva de'
}
const whenText = (d: number): string => (d <= 0 ? 'hoy' : d === 1 ? 'ayer' : `hace ${d} d`)
function shortName(name: string): string {
  const w = name.split(/\s+/).filter((x) => x.length > 2 || /^[A-ZÁÉÍÓÚ]/.test(x))
  const s = w.length > 1 ? w.map((x) => x[0]).join('') : name.slice(0, 4)
  return s.toUpperCase().slice(0, 5)
}
