import { api, listAll } from '@/modules/calendar/workspaceApi'
import type {
  Habit,
  HabitCreate,
  HabitHistory,
  HabitRecord,
  HabitStatistics,
  HabitUpdate,
  RecordStatus
} from './types'

export const listHabits = (includeArchived: boolean): Promise<readonly Habit[]> =>
  listAll<Habit>('/habits', { include_archived: includeArchived })

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
