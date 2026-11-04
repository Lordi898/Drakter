import { rangeOfDays, startOfWeek } from './dateUtils'
import { TimeGrid, type TimeGridProps } from './TimeGrid'

export interface WeekViewProps extends Omit<TimeGridProps, 'days'> {
  readonly day: string
}

export function WeekView({ day, ...rest }: WeekViewProps) {
  return <TimeGrid days={rangeOfDays(startOfWeek(day), 7)} {...rest} />
}
