import type { ComponentType } from 'react'
import { CalendarPage } from '@/modules/calendar/CalendarPage'
import { HabitsPage } from '@/modules/habits/HabitsPage'
import { ProjectsPage } from '@/modules/projects/ProjectsPage'
import { RelationshipsPage } from '@/modules/relationships/RelationshipsPage'
import { StoragePage } from '@/modules/storage/StoragePage'
import { SubjectsPage } from '@/modules/subjects/SubjectsPage'
import { TasksPage } from '@/modules/tasks/TasksPage'
import { HomePage } from '@/pages/HomePage'
import { TodayPage } from '@/pages/today/TodayPage'
import { SettingsPage } from '@/settings/SettingsPage'
import type { SectionId } from './sections'

export const PAGES: Readonly<Record<SectionId, ComponentType>> = {
  today: TodayPage,
  home: HomePage,
  habits: HabitsPage,
  tasks: TasksPage,
  projects: ProjectsPage,
  storage: StoragePage,
  calendar: CalendarPage,
  subjects: SubjectsPage,
  relationships: RelationshipsPage,
  settings: SettingsPage
}
