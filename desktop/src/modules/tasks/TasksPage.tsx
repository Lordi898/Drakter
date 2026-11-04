import { Plus } from 'lucide-react'
import { useCallback, useState } from 'react'
import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { ConfirmationDialog } from './ConfirmationDialog'
import { DEFAULT_FILTERS, TaskFilters, type TaskFilterState } from './TaskFilters'
import { TaskDetailDialog } from './TaskDetailDialog'
import { TaskForm } from './TaskForm'
import { TaskRow } from './TaskRow'
import { TasksDrawing } from './TasksDrawing'
import { useTaskActions } from './useTaskActions'
import { useTaskRunner } from './useTaskRunner'
import { useTasks } from './useTasks'
import type { TaskListParams } from './api'

function toParams(filters: TaskFilterState): TaskListParams {
  const q = filters.q.trim()
  return {
    include_archived: filters.includeArchived,
    limit: 50,
    root_only: filters.rootOnly && q === '',
    ...(q === '' ? {} : { q }),
    ...(filters.status === 'all' ? {} : { status: [filters.status] }),
    ...(filters.priority === 'all' ? {} : { priority: [filters.priority] })
  }
}

export function TasksPage() {
  const [filters, setFilters] = useState<TaskFilterState>(DEFAULT_FILTERS)
  const [creating, setCreating] = useState(false)
  const [openId, setOpenId] = useState<string | null>(null)
  const [version, setVersion] = useState(0)

  const list = useTasks(toParams(filters))
  const { reload } = list
  const onChanged = useCallback(() => {
    reload()
    setVersion((n) => n + 1)
  }, [reload])
  const { run, ticket, resolveConfirmation } = useTaskRunner(onChanged)
  const actions = useTaskActions(run, () => setOpenId(null))

  const filtered =
    filters.q.trim() !== '' || filters.status !== 'all' || filters.priority !== 'all' || filters.includeArchived
  const showEmpty = !list.loading && list.error === null && list.items.length === 0

  return (
    <>
      <PageHeader
        title="Tareas"
        summary="Tus tareas con subtareas, prioridades, fechas límite y dependencias."
        actions={
          <Button onClick={() => setCreating(true)}>
            <Plus aria-hidden="true" />
            Nueva tarea
          </Button>
        }
      />
      <TaskFilters value={filters} onChange={setFilters} />

      {list.error !== null ? (
        <div role="alert" className="flex max-w-xl flex-col items-start gap-3">
          <h2 className="text-xl font-semibold">No se pudieron cargar las tareas</h2>
          <p className="text-muted-foreground">{list.error}</p>
          <Button variant="outline" onClick={reload}>
            Reintentar
          </Button>
        </div>
      ) : list.loading ? (
        <p role="status" className="text-muted-foreground">
          Cargando tareas…
        </p>
      ) : showEmpty ? (
        filtered ? (
          <div className="flex max-w-xl flex-col items-start gap-3">
            <h2 className="text-xl font-semibold">Nada coincide con estos filtros</h2>
            <p className="text-muted-foreground">Prueba con otra búsqueda o quita algún filtro.</p>
            <Button variant="outline" onClick={() => setFilters(DEFAULT_FILTERS)}>
              Quitar filtros
            </Button>
          </div>
        ) : (
          <div className="flex flex-col items-start gap-4">
            <EmptyState
              title="Aún no hay tareas"
              description="Crea la primera y añade subtareas, prioridad y fecha límite cuando la necesites."
              drawing={<TasksDrawing />}
            />
            <Button onClick={() => setCreating(true)}>
              <Plus aria-hidden="true" />
              Crear tarea
            </Button>
          </div>
        )
      ) : (
        <div className="flex flex-col gap-4">
          <ul
            aria-label="Lista de tareas"
            className="overflow-hidden rounded-[var(--radius-sheet)] border bg-card"
          >
            {list.items.map((task) => (
              <TaskRow key={task.id} task={task} onOpen={(item) => setOpenId(item.id)} onToggle={actions.toggle} />
            ))}
          </ul>
          {list.hasMore ? (
            <Button variant="outline" className="self-center" disabled={list.loadingMore} onClick={list.loadMore}>
              {list.loadingMore ? 'Cargando…' : 'Cargar más'}
            </Button>
          ) : null}
        </div>
      )}

      {creating ? <TaskForm open onOpenChange={setCreating} run={run} onSaved={(task) => setOpenId(task.id)} /> : null}
      <TaskDetailDialog
        taskId={openId}
        version={version}
        run={run}
        actions={actions}
        onNavigate={setOpenId}
        onChanged={onChanged}
      />
      {actions.subtasksPrompt}
      <ConfirmationDialog ticket={ticket} onResolved={resolveConfirmation} />
    </>
  )
}
