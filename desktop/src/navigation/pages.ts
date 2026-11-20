import { lazy, type ComponentType } from 'react'
import { TodayPage } from '@/pages/today/TodayPage'
import type { SectionId } from './sections'

// «Hoy» es la primera pantalla y va en el chunk principal. El resto se carga aparte
// (un chunk por módulo) y se precarga en reposo tras el primer pintado: así el arranque
// solo evalúa lo que se ve y cambiar de sección no espera a la red ni al disco.
const loaders: Readonly<Record<Exclude<SectionId, 'today'>, () => Promise<{ default: ComponentType }>>> = {
  home: () => import('@/pages/HomePage').then((m) => ({ default: m.HomePage })),
  habits: () => import('@/modules/habits/HabitsPage').then((m) => ({ default: m.HabitsPage })),
  tasks: () => import('@/modules/tasks/TasksPage').then((m) => ({ default: m.TasksPage })),
  projects: () => import('@/modules/projects/ProjectsPage').then((m) => ({ default: m.ProjectsPage })),
  storage: () => import('@/modules/storage/StoragePage').then((m) => ({ default: m.StoragePage })),
  calendar: () => import('@/modules/calendar/CalendarPage').then((m) => ({ default: m.CalendarPage })),
  subjects: () => import('@/modules/subjects/SubjectsPage').then((m) => ({ default: m.SubjectsPage })),
  relationships: () =>
    import('@/modules/relationships/RelationshipsPage').then((m) => ({ default: m.RelationshipsPage })),
  settings: () => import('@/settings/SettingsPage').then((m) => ({ default: m.SettingsPage }))
}

export const PAGES: Readonly<Record<SectionId, ComponentType>> = {
  today: TodayPage,
  home: lazy(loaders.home),
  habits: lazy(loaders.habits),
  tasks: lazy(loaders.tasks),
  projects: lazy(loaders.projects),
  storage: lazy(loaders.storage),
  calendar: lazy(loaders.calendar),
  subjects: lazy(loaders.subjects),
  relationships: lazy(loaders.relationships),
  settings: lazy(loaders.settings)
}

const PRELOAD_DELAY_MS = 1500
let preloaded = false

/** Calienta los chunks de las demás secciones cuando el arranque ya terminó. Idempotente. */
export function preloadPages(): void {
  if (preloaded) return
  preloaded = true
  const run = () => {
    for (const load of Object.values(loaders)) void load().catch(() => undefined)
  }
  // Tras el primer pintado y los datos de «Hoy»: antes competiría con ellos por el hilo.
  setTimeout(() => {
    if ('requestIdleCallback' in window) window.requestIdleCallback(run, { timeout: 2000 })
    else run()
  }, PRELOAD_DELAY_MS)
}
