/**
 * Datos de las interfaces Jarvis (D1). Adaptan las funciones de lectura de `modules/*` (y `GET /today`
 * de `pages/today`) a instantáneas estables: sin `fetch` ni caché propios y sin estado por fotograma.
 * Rangos y filtros de cada tema: `types.ts`.
 */
import { useEffect, useMemo, useState } from 'react'
import { listActivity } from '@/modules/activity/api'
import { fetchAgenda } from '@/modules/calendar/api'
import { addDays, systemTimeZone, todayIn } from '@/modules/calendar/dateUtils'
import { getHistory, listHabits } from '@/modules/habits/api'
import { getMemoryStatus } from '@/modules/memory/api'
import { listProjects } from '@/modules/projects/api'
import { searchRelationships } from '@/modules/relationships/api'
import type { RelationshipOut } from '@/modules/relationships/types'
import { listFolders, listResources } from '@/modules/storage/api'
import type { IndexStatus } from '@/modules/storage/types'
import { getTimetable, listSubjects } from '@/modules/subjects/api'
import { listTasks } from '@/modules/tasks/api'
import { fetchSettings, fetchToday } from '@/pages/today/requests'
import { useDerived, useTopic } from './snapshot'
import type { EntityName, JarvisData, JarvisTopic, ResourceIndexSample, UseJarvisData } from './types'

export type { EntityName, JarvisData, JarvisTopic, ResourceIndexSample, Snapshot, SnapshotStatus, UseJarvisData } from './types'

const HISTORY_DAYS = 28
const AGENDA_DAYS = 7
const RELATIONSHIP_PAGES = 5
const MIDNIGHT_CHECK_MS = 60_000
const INDEX_STATUSES: readonly IndexStatus[] = ['none', 'pending', 'indexed', 'failed', 'skipped']

/** Temas que necesitan otros para calcularse. */
const NEEDS: Partial<Record<JarvisTopic, readonly JarvisTopic[]>> = {
  habitHistory: ['habits'],
  resourceIndex: ['resources'],
  entityNames: ['tasks', 'projects', 'habits', 'subjects', 'resources', 'agenda']
}

/** Zona del usuario: el ajuste `default_timezone` (como la página Hoy) o, si falta, la del sistema. */
async function userTimeZone(): Promise<string> {
  try {
    const settings = await fetchSettings()
    return settings.items.find((item) => item.key === 'default_timezone')?.value || systemTimeZone()
  } catch {
    return systemTimeZone()
  }
}

/** Día de hoy en `zone`; solo cambia (un `setState` al día) cuando pasa la medianoche. */
function useToday(zone: string | null): string | null {
  const [day, setDay] = useState<string | null>(null)
  useEffect(() => {
    if (!zone) return
    const check = (): void => setDay(todayIn(zone))
    check()
    const timer = window.setInterval(check, MIDNIGHT_CHECK_MS)
    return () => window.clearInterval(timer)
  }, [zone])
  return day
}

async function allRelationships(): Promise<readonly RelationshipOut[]> {
  const out: RelationshipOut[] = []
  let cursor: string | null = null
  for (let page = 0; page < RELATIONSHIP_PAGES; page++) {
    const result = await searchRelationships({}, cursor, 200)
    out.push(...result.items)
    cursor = result.next_cursor
    if (!cursor) break
  }
  return out
}

export const useJarvisData: UseJarvisData = <K extends JarvisTopic>(topics: readonly K[]) => {
  const wanted = useMemo(() => {
    const set = new Set<JarvisTopic>(topics)
    for (const topic of topics) for (const need of NEEDS[topic] ?? []) set.add(need)
    return set
  }, [topics])
  const on = (topic: JarvisTopic): boolean => wanted.has(topic)
  const dated = on('today') || on('agenda') || on('timetable') || on('habitHistory')

  const zoneTopic = useTopic(userTimeZone, 'zone', dated)
  const zone = zoneTopic.data
  const day = useToday(zone)
  const hasDay = zone !== null && day !== null

  const today = useTopic(() => fetchToday(zone!), `${zone}|${day}`, on('today') && hasDay)
  const tasks = useTopic(
    () => listTasks({ status: ['pending', 'in_progress', 'on_hold'], limit: 200 }).then((p) => p.items),
    'tasks',
    on('tasks')
  )
  const projects = useTopic(
    () => listProjects({ status: ['planned', 'active', 'paused'], limit: 200 }).then((p) => p.items),
    'projects',
    on('projects')
  )
  const habits = useTopic(() => listHabits(false), 'habits', on('habits'))
  const agenda = useTopic(
    () => fetchAgenda(day!, addDays(day!, AGENDA_DAYS), zone!).then((r) => r.items),
    `${zone}|${day}`,
    on('agenda') && hasDay
  )
  const timetable = useTopic(() => getTimetable(day!).then((t) => t.entries), `${day}`, on('timetable') && hasDay)
  const relationships = useTopic(allRelationships, 'relationships', on('relationships'))
  const resources = useTopic(
    () => listResources({ folderId: null, type: '', availability: '' }).then((p) => p.items),
    'resources',
    on('resources')
  )
  const activity = useTopic(() => listActivity({ limit: 50 }).then((p) => p.items), 'activity', on('activity'))
  const memory = useTopic(getMemoryStatus, 'memory', on('memory'))
  const subjects = useTopic(() => listSubjects(false).then((p) => p.items), 'subjects', on('subjects'))
  const folders = useTopic(() => listFolders(null), 'folders', on('folders'))

  // Una petición por hábito, en paralelo; se repite si cambian los hábitos o el día.
  const habitIds = habits.data?.map((h) => h.id) ?? []
  const habitHistory = useTopic(
    async () => {
      const from = addDays(day!, -(HISTORY_DAYS - 1))
      const rows = await Promise.all(habitIds.map(async (id) => [id, (await getHistory(id, from, day!)).days] as const))
      return Object.fromEntries(rows)
    },
    `${day}|${habitIds.join()}`,
    on('habitHistory') && hasDay && habits.data !== null
  )

  const resourceIndex = useDerived<ResourceIndexSample>(
    [resources],
    () => {
      const counts = Object.fromEntries(INDEX_STATUSES.map((s) => [s, 0])) as Record<IndexStatus, number>
      for (const r of resources.data ?? []) counts[r.index_status]++
      return { counts, sample: resources.data?.length ?? 0 }
    },
    [resources.data]
  )

  const entityNames = useDerived<ReadonlyMap<string, EntityName>>(
    [tasks, projects, habits, subjects, resources, agenda],
    () => {
      const map = new Map<string, EntityName>()
      for (const t of tasks.data ?? []) map.set(t.id, { name: t.title, type: 'task' })
      for (const p of projects.data ?? []) map.set(p.id, { name: p.name, type: 'project' })
      for (const h of habits.data ?? []) map.set(h.id, { name: h.name, type: 'habit' })
      for (const s of subjects.data ?? []) map.set(s.id, { name: s.name, type: 'subject' })
      for (const r of resources.data ?? []) map.set(r.id, { name: r.title, type: 'resource' })
      for (const a of agenda.data ?? []) if (!map.has(a.source_id)) map.set(a.source_id, { name: a.title, type: a.source_type })
      return map
    },
    [tasks.data, projects.data, habits.data, subjects.data, resources.data, agenda.data]
  )

  const all: JarvisData = {
    today, tasks, projects, habits, agenda, timetable, relationships, resources, activity, memory,
    habitHistory, subjects, folders, resourceIndex, entityNames
  }
  const picked = topics.map((t) => all[t])
  // Mismo objeto mientras ninguno de los temas pedidos cambie.
  return useMemo(
    () => Object.fromEntries(topics.map((t, i) => [t, picked[i]])) as Pick<JarvisData, K>,
    [topics, ...picked]
  )
}
