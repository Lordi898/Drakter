import { CalendarClock, Lock, TriangleAlert } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { dueLabel, isOverdue } from './format'
import { PRIORITY_LABELS, TASK_STATUS_LABELS, type Priority, type Task, type TaskStatus } from './types'

const priorityTone: Readonly<Record<Priority, string>> = {
  low: 'text-muted-foreground',
  medium: 'text-foreground',
  high: 'text-warning font-semibold',
  urgent: 'text-destructive font-semibold'
}

export function StatusBadge({ status }: { readonly status: TaskStatus }) {
  return (
    <Badge variant={status === 'in_progress' ? 'default' : 'secondary'}>{TASK_STATUS_LABELS[status]}</Badge>
  )
}

export function PriorityLabel({ priority }: { readonly priority: Priority }) {
  return <span className={cn('text-xs', priorityTone[priority])}>Prioridad {PRIORITY_LABELS[priority].toLowerCase()}</span>
}

export function DueBadge({ task }: { readonly task: Task }) {
  const label = dueLabel(task)
  if (label === null) return null
  if (isOverdue(task)) {
    return (
      <Badge variant="outline" className="border-destructive text-destructive">
        <TriangleAlert aria-hidden="true" />
        Vencida · {label}
      </Badge>
    )
  }
  return (
    <Badge variant="outline">
      <CalendarClock aria-hidden="true" />
      {label}
    </Badge>
  )
}

export function BlockedBadge({ task }: { readonly task: Task }) {
  if (!task.blocked) return null
  return (
    <Badge variant="outline">
      <Lock aria-hidden="true" />
      Bloqueada
    </Badge>
  )
}
