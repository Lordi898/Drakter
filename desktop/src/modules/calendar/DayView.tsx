import { TimeGrid, type TimeGridProps } from './TimeGrid'

export interface DayViewProps extends Omit<TimeGridProps, 'days' | 'onOpenDay'> {
  readonly day: string
}

export function DayView({ day, ...rest }: DayViewProps) {
  return <TimeGrid days={[day]} {...rest} />
}
