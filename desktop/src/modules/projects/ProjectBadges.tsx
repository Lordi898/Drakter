import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { PRIORITY_LABELS, PROJECT_STATUS_LABELS, type Priority, type ProjectStatus } from './types'

const STATUS_TONE: Readonly<Record<ProjectStatus, string>> = {
  planned: 'border-border text-muted-foreground',
  active: 'border-warning text-warning',
  paused: 'border-border text-foreground',
  completed: 'border-success text-success',
  cancelled: 'border-border text-muted-foreground line-through'
}

export function ProjectStatusBadge({ status }: { readonly status: ProjectStatus }) {
  return (
    <Badge variant="outline" className={cn(STATUS_TONE[status])}>
      {PROJECT_STATUS_LABELS[status]}
    </Badge>
  )
}

export function ProjectPriority({ priority }: { readonly priority: Priority }) {
  return <span className="text-xs text-muted-foreground">Prioridad {PRIORITY_LABELS[priority].toLowerCase()}</span>
}
