import { addDays } from './dateUtils'
import { minutesOf } from './dateUtils'
import type { AgendaItem } from './types'

export interface Placed {
  readonly item: AgendaItem
  readonly startMin: number
  readonly endMin: number
  readonly lane: number
  readonly lanes: number
}

/** Ocurrencias de día completo que tocan `day` ('AAAA-MM-DD'; `end_date_exclusive` es exclusivo). */
export function allDayOn(items: readonly AgendaItem[], day: string): AgendaItem[] {
  return items.filter((i) => i.all_day && i.start_date !== null && i.start_date <= day && (i.end_date_exclusive ?? i.start_date) > day)
}

/** Ocurrencias con hora recortadas al día, en carriles lado a lado cuando se pisan. */
export function placeTimed(items: readonly AgendaItem[], day: string): Placed[] {
  const dayStart = `${day}T00:00`
  const dayEnd = `${addDays(day, 1)}T00:00`
  const clipped = items
    .filter((i) => !i.all_day && i.display_start !== null && i.display_end !== null)
    .filter((i) => (i.display_start as string) < dayEnd && (i.display_end as string) > dayStart)
    .map((item) => {
      const s = item.display_start as string
      const e = item.display_end as string
      const startMin = s < dayStart ? 0 : minutesOf(s)
      const endMin = e >= dayEnd ? 1440 : minutesOf(e)
      return { item, startMin, endMin: Math.max(endMin, startMin + 20) }
    })
    .sort((a, b) => a.startMin - b.startMin || b.endMin - a.endMin)

  const result: Placed[] = []
  let cluster: { item: AgendaItem; startMin: number; endMin: number; lane: number }[] = []
  let laneEnds: number[] = []
  let clusterEnd = -1
  const flush = (): void => {
    for (const c of cluster) result.push({ ...c, lanes: laneEnds.length })
    cluster = []
    laneEnds = []
    clusterEnd = -1
  }
  for (const entry of clipped) {
    if (entry.startMin >= clusterEnd) flush()
    let lane = laneEnds.findIndex((end) => end <= entry.startMin)
    if (lane === -1) {
      lane = laneEnds.length
      laneEnds.push(entry.endMin)
    } else {
      laneEnds[lane] = entry.endMin
    }
    cluster.push({ ...entry, lane })
    clusterEnd = Math.max(clusterEnd, entry.endMin)
  }
  flush()
  return result
}

/** Todas las ocurrencias (con o sin hora) que caen en `day`, para la vista mensual. */
export function itemsOn(items: readonly AgendaItem[], day: string): AgendaItem[] {
  const dayStart = `${day}T00:00`
  const dayEnd = `${addDays(day, 1)}T00:00`
  return items
    .filter((i) =>
      i.all_day
        ? i.start_date !== null && i.start_date <= day && (i.end_date_exclusive ?? i.start_date) > day
        : i.display_start !== null && i.display_end !== null && i.display_start < dayEnd && i.display_end > dayStart
    )
    .sort((a, b) => Number(b.all_day) - Number(a.all_day) || (a.display_start ?? '').localeCompare(b.display_start ?? ''))
}
