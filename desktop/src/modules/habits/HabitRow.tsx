import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { QuickMark } from './QuickMark'
import { describeRrule } from './rrule'
import type { Habit, RecordStatus } from './types'

export interface HabitRowProps {
  readonly habit: Habit
  readonly busy: boolean
  readonly onOpen: (habit: Habit) => void
  readonly onMark: (habit: Habit, status: RecordStatus) => void
}

export function HabitRow({ habit, busy, onOpen, onMark }: HabitRowProps) {
  const archived = habit.archived_at !== null
  return (
    <li className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-border bg-card px-4 py-3">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <Button type="button" variant="link" className="h-auto p-0 text-base font-semibold text-foreground" onClick={() => onOpen(habit)}>
            {habit.name}
          </Button>
          {archived ? <Badge variant="outline">Archivado</Badge> : null}
          {!archived && habit.status !== 'active' ? (
            <Badge variant="secondary">{habit.status === 'paused' ? 'En pausa' : 'Terminado'}</Badge>
          ) : null}
        </div>
        <p className="text-sm text-muted-foreground">
          {describeRrule(habit.rrule)}
          {habit.preferred_local_time ? ` · ${habit.preferred_local_time.slice(0, 5)}` : ''}
        </p>
      </div>
      {archived ? null : habit.today_scheduled ? (
        <QuickMark
          label={`Hoy: ${habit.name}`}
          current={habit.today_status}
          busy={busy}
          onMark={(status) => onMark(habit, status)}
        />
      ) : (
        <span className="text-sm text-muted-foreground">Hoy no toca</span>
      )}
    </li>
  )
}
