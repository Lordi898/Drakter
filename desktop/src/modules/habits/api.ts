import { api, type Page } from '../calendar/workspaceClient'
import type {
  Habit,
  HabitCreate,
  HabitHistory,
  HabitRecord,
  HabitStatistics,
  HabitUpdate,
  RecordStatus
} from './types'

export async function listHabits(includeArchived: boolean): Promise<readonly Habit[]> {
  const items: Habit[] = []
  let cursor: string | null = null
  do {
    const page: Page<Habit> = await api<Page<Habit>>('GET', '/habits', {
      query: { include_archived: includeArchived, limit: 100, cursor }
    })
    items.push(...page.items)
    cursor = page.next_cursor
  } while (cursor)
  return items
}

export const createHabit = (body: HabitCreate) => api<Habit>('POST', '/habits', { body })

export const updateHabit = (habit: Habit, body: HabitUpdate) =>
  api<Habit>('PATCH', `/habits/${habit.id}`, { body, revision: habit.revision })

export const setArchived = (habit: Habit, archived: boolean) =>
  api<Habit>('POST', `/habits/${habit.id}/${archived ? 'archive' : 'unarchive'}`, { revision: habit.revision })

export const registerRecord = (habitId: string, date: string, status: RecordStatus) =>
  api<HabitRecord>('PUT', `/habits/${habitId}/records/${date}`, { body: { status } })

export const getHistory = (habitId: string, from: string, to: string) =>
  api<HabitHistory>('GET', `/habits/${habitId}/history`, { query: { from, to } })

export const getStatistics = (habitId: string, from: string, to: string) =>
  api<HabitStatistics>('GET', `/habits/${habitId}/statistics`, { query: { from, to } })
