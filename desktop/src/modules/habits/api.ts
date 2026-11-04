import { api, type Page } from '@/modules/calendar/workspaceApi'
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
  const limit = 100
  for (;;) {
    const page = await api<Page<Habit>>('GET', '/habits', {
      query: { include_archived: includeArchived, limit, offset: items.length }
    })
    items.push(...page.items)
    if (page.items.length < limit || items.length >= page.total) return items
  }
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
