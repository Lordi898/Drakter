import { useCallback, useEffect, useState } from 'react'
import { getHistory, getStatistics, listHabits } from './api'
import { addDays, todayIn } from './dates'
import type { Habit, HabitHistory, HabitStatistics } from './types'

export interface HabitsState {
  readonly habits: readonly Habit[] | null
  readonly error: unknown
  readonly reload: () => void
}

/** Lista de hábitos; `habits` es null mientras carga o si falló. */
export function useHabits(includeArchived: boolean): HabitsState {
  const [habits, setHabits] = useState<readonly Habit[] | null>(null)
  const [error, setError] = useState<unknown>(null)

  const reload = useCallback(() => {
    setError(null)
    listHabits(includeArchived)
      .then(setHabits)
      .catch((e: unknown) => {
        setHabits(null)
        setError(e)
      })
  }, [includeArchived])

  useEffect(reload, [reload])
  return { habits, error, reload }
}

export interface HabitStatsState {
  readonly history: HabitHistory | null
  readonly stats: HabitStatistics | null
  readonly error: unknown
  readonly reload: () => void
}

/** Historial y estadísticas de un hábito en los últimos `rangeDays` días (hasta hoy en su zona). */
export function useHabitStats(habit: Habit, rangeDays: number): HabitStatsState {
  const today = todayIn(habit.timezone)
  const [history, setHistory] = useState<HabitHistory | null>(null)
  const [stats, setStats] = useState<HabitStatistics | null>(null)
  const [error, setError] = useState<unknown>(null)

  const reload = useCallback(() => {
    const from = addDays(today, -(rangeDays - 1))
    setError(null)
    Promise.all([getHistory(habit.id, from, today), getStatistics(habit.id, from, today)])
      .then(([h, s]) => {
        setHistory(h)
        setStats(s)
      })
      .catch(setError)
  }, [habit.id, rangeDays, today])

  useEffect(reload, [reload])
  return { history, stats, error, reload }
}
