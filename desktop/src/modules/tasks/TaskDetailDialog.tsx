import { Archive, ArchiveRestore, Check, Pencil, RotateCcw, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Tabs } from 'radix-ui'
import { Button } from '@/components/ui/button'
import { GuardedButton } from './GuardedButton'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { cn } from '@/lib/utils'
import { DependenciesTab } from './DependenciesTab'
import { HistoryTab } from './HistoryTab'
import { formatInstant } from './format'
import { SubtasksTab } from './SubtasksTab'
import { BlockedBadge, DueBadge, PriorityLabel, StatusBadge } from './TaskBadges'
import { TaskForm } from './TaskForm'
import type { TaskActions } from './useTaskActions'
import type { RunTask } from './useTaskRunner'
import { useTaskDetail } from './useTasks'
import type { Task, TaskDetail } from './types'

export interface TaskDetailDialogProps {
  /** Tarea abierta; `null` cierra el diálogo. */
  readonly taskId: string | null
  readonly version: number
  readonly run: RunTask
  readonly actions: TaskActions
  readonly onNavigate: (id: string | null) => void
  readonly onChanged: () => void
}

const TRIGGER =
  'rounded-tab px-3 py-1.5 text-sm font-medium text-muted-foreground outline-none data-[state=active]:bg-secondary data-[state=active]:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50'

export function TaskDetailDialog({ taskId, version, run, actions, onNavigate, onChanged }: TaskDetailDialogProps) {
  const { detail, loading, error } = useTaskDetail(taskId, version)
  const [editing, setEditing] = useState(false)
  const [subtaskParent, setSubtaskParent] = useState<{ id: string; title: string } | null>(null)

  return (
    <>
      <Dialog open={taskId !== null} onOpenChange={(open) => !open && onNavigate(null)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto rounded-[var(--radius-sheet)] sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>{detail?.title ?? 'Tarea'}</DialogTitle>
            <DialogDescription>
              {detail ? 'Datos, subtareas, dependencias e historial.' : 'Detalle de la tarea.'}
            </DialogDescription>
          </DialogHeader>
          {error !== null ? (
            <div role="alert" className="flex flex-col items-start gap-2 text-sm">
              <p className="text-destructive">No se pudo cargar la tarea: {error}</p>
              <Button size="sm" variant="outline" onClick={onChanged}>
                Reintentar
              </Button>
            </div>
          ) : detail === null ? (
            <p className="text-sm text-muted-foreground">{loading ? 'Cargando…' : ''}</p>
          ) : (
            <Tabs.Root defaultValue="data" className="flex flex-col gap-4">
              <Tabs.List aria-label="Secciones de la tarea" className="flex flex-wrap gap-1 border-b pb-2">
                <Tabs.Trigger value="data" className={TRIGGER}>
                  Datos
                </Tabs.Trigger>
                <Tabs.Trigger value="subtasks" className={TRIGGER}>
                  Subtareas{detail.subtask_count > 0 ? ` (${detail.subtask_count})` : ''}
                </Tabs.Trigger>
                <Tabs.Trigger value="deps" className={TRIGGER}>
                  Dependencias{detail.blocked ? ' · bloqueada' : ''}
                </Tabs.Trigger>
                <Tabs.Trigger value="history" className={TRIGGER}>
                  Historial
                </Tabs.Trigger>
              </Tabs.List>
              <Tabs.Content value="data" className="outline-none">
                <DataTab detail={detail} actions={actions} onEdit={() => setEditing(true)} />
              </Tabs.Content>
              <Tabs.Content value="subtasks" className="outline-none">
                <SubtasksTab
                  detail={detail}
                  onAdd={setSubtaskParent}
                  onToggle={actions.toggle}
                  onOpen={onNavigate}
                />
              </Tabs.Content>
              <Tabs.Content value="deps" className="outline-none">
                <DependenciesTab detail={detail} run={run} onOpen={onNavigate} />
              </Tabs.Content>
              <Tabs.Content value="history" className="outline-none">
                <HistoryTab taskId={detail.id} version={version} />
              </Tabs.Content>
            </Tabs.Root>
          )}
        </DialogContent>
      </Dialog>
      {editing && detail !== null ? (
        <TaskForm open onOpenChange={setEditing} run={run} task={detail as Task} />
      ) : null}
      {subtaskParent !== null ? (
        <TaskForm
          open
          onOpenChange={(open) => !open && setSubtaskParent(null)}
          run={run}
          parent={subtaskParent}
        />
      ) : null}
    </>
  )
}

function Row({ term, children, className }: { term: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={cn('flex flex-col gap-0.5', className)}>
      <dt className="text-xs text-muted-foreground">{term}</dt>
      <dd className="text-sm">{children}</dd>
    </div>
  )
}

function DataTab({
  detail,
  actions,
  onEdit
}: {
  readonly detail: TaskDetail
  readonly actions: TaskActions
  readonly onEdit: () => void
}) {
  const archived = detail.archived_at !== null
  const done = detail.status === 'completed'
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge status={detail.status} />
        <DueBadge task={detail} />
        <BlockedBadge task={detail} />
        <PriorityLabel priority={detail.priority} />
        {archived ? <span className="text-xs text-muted-foreground">Archivada</span> : null}
      </div>
      <dl className="grid grid-cols-2 gap-4">
        <Row term="Descripción" className="col-span-2">
          {detail.description ? (
            <span className="whitespace-pre-wrap">{detail.description}</span>
          ) : (
            <span className="text-muted-foreground">Sin descripción</span>
          )}
        </Row>
        <Row term="Estimación">
          {detail.estimated_minutes !== null ? `${detail.estimated_minutes} min` : 'Sin estimar'}
        </Row>
        <Row term="Etiquetas">
          {detail.tags.length > 0 ? detail.tags.map((tag) => tag.name).join(', ') : 'Sin etiquetas'}
        </Row>
        <Row term="Creada">{formatInstant(detail.created_at)}</Row>
        <Row term={done ? 'Completada' : 'Última modificación'}>
          {formatInstant(done && detail.completed_at !== null ? detail.completed_at : detail.updated_at)}
        </Row>
      </dl>
      <div className="flex flex-wrap gap-2 border-t pt-4">
        <GuardedButton
          size="sm"
          variant="outline"
          onClick={onEdit}
          unavailableReason={archived ? 'Está archivada: restáurala para editarla.' : null}
        >
          <Pencil aria-hidden="true" />
          Editar
        </GuardedButton>
        <GuardedButton
          size="sm"
          variant="outline"
          onClick={() => actions.toggle(detail)}
          unavailableReason={
            archived
              ? 'Está archivada: restáurala para cambiar su estado.'
              : detail.status === 'cancelled'
                ? 'Está cancelada: edítala para cambiar su estado.'
                : null
          }
        >
          {done ? <RotateCcw aria-hidden="true" /> : <Check aria-hidden="true" />}
          {done ? 'Reabrir' : 'Completar'}
        </GuardedButton>
        <Button
          size="sm"
          variant="outline"
          onClick={() => (archived ? actions.unarchive(detail) : actions.archive(detail))}
        >
          {archived ? <ArchiveRestore aria-hidden="true" /> : <Archive aria-hidden="true" />}
          {archived ? 'Restaurar' : 'Archivar'}
        </Button>
        <Button size="sm" variant="destructive" className="ml-auto" onClick={() => actions.remove(detail)}>
          <Trash2 aria-hidden="true" />
          Eliminar
        </Button>
      </div>
    </div>
  )
}
