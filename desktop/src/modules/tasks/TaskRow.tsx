import { Check, ChevronRight, RotateCcw } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { GuardedButton } from './GuardedButton'
import { cn } from '@/lib/utils'
import { BlockedBadge, DueBadge, PriorityLabel, StatusBadge } from './TaskBadges'
import type { Task } from './types'

export interface TaskRowProps {
  readonly task: Task
  readonly onOpen: (task: Task) => void
  readonly onToggle: (task: Task) => void
}

export function TaskRow({ task, onOpen, onToggle }: TaskRowProps) {
  const done = task.status === 'completed'
  const closed = done || task.status === 'cancelled'
  return (
    <li className="flex items-center gap-3 border-b px-4 py-3 last:border-b-0">
      <GuardedButton
        variant="outline"
        size="icon-sm"
        unavailableReason={
          task.archived_at !== null
            ? 'Está archivada: restáurala para cambiarla.'
            : task.status === 'cancelled'
              ? 'Está cancelada: edítala para cambiar su estado.'
              : null
        }
        aria-label={done ? `Reabrir «${task.title}»` : `Completar «${task.title}»`}
        title={done ? 'Reabrir' : 'Completar'}
        onClick={() => onToggle(task)}
      >
        {done ? <RotateCcw aria-hidden="true" /> : <Check aria-hidden="true" className="opacity-60" />}
      </GuardedButton>
      <button
        type="button"
        onClick={() => onOpen(task)}
        className="group flex min-w-0 flex-1 flex-col items-start gap-1 rounded-sm text-left"
      >
        <span className={cn('max-w-full truncate font-medium', closed && 'text-muted-foreground line-through')}>
          {task.title}
        </span>
        <span className="flex flex-wrap items-center gap-2">
          <StatusBadge status={task.status} />
          <DueBadge task={task} />
          <BlockedBadge task={task} />
          {task.archived_at !== null ? <Badge variant="outline">Archivada</Badge> : null}
          {task.subtask_count > 0 ? (
            <span className="text-xs text-muted-foreground">
              {task.completed_subtask_count} de {task.subtask_count} subtareas
            </span>
          ) : null}
          {task.tags.map((tag) => (
            <Badge key={tag.id} variant="outline" className="font-normal">
              {tag.name}
            </Badge>
          ))}
          <PriorityLabel priority={task.priority} />
        </span>
      </button>
      <ChevronRight aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />
    </li>
  )
}
