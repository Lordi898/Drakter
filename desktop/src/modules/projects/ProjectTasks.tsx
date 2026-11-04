import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { listTasks, updateTask } from '../tasks/api'
import { dueLabel } from '../tasks/format'
import { StatusBadge } from '../tasks/TaskBadges'
import { LoadFailure, LoadingNote } from './ProjectStates'
import { useLoad } from './useLoad'
import type { RunProject } from './useProjectRunner'

function AttachTask({
  projectId,
  run,
  onAttached
}: {
  readonly projectId: string
  readonly run: RunProject
  readonly onAttached: () => void
}) {
  const [open, setOpen] = useState(false)
  const [taskId, setTaskId] = useState('')
  const loose = useLoad(
    () => (open ? listTasks({ no_project: true, root_only: true, limit: 100 }) : Promise.resolve(null)),
    `loose-${open}`
  )
  const options = loose.data?.items ?? []

  if (!open) {
    return (
      <Button variant="outline" size="sm" className="self-start" onClick={() => setOpen(true)}>
        Asociar una tarea existente
      </Button>
    )
  }
  if (loose.error !== null) return <LoadFailure error={loose.error} what="las tareas sin proyecto" onRetry={loose.reload} />

  async function attach() {
    const task = options.find((t) => t.id === taskId)
    if (task === undefined) return
    const ok = await run(() => updateTask(task.id, { project_id: projectId }, task.revision), 'Tarea asociada al proyecto')
    if (ok) {
      setOpen(false)
      setTaskId('')
      onAttached()
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {loose.loading ? (
        <LoadingNote label="Buscando tareas sin proyecto…" />
      ) : options.length === 0 ? (
        <p className="text-sm text-muted-foreground">No hay tareas sueltas para asociar.</p>
      ) : (
        <Select value={taskId} onValueChange={setTaskId}>
          <SelectTrigger size="sm" aria-label="Tarea a asociar" className="min-w-64">
            <SelectValue placeholder="Elige una tarea" />
          </SelectTrigger>
          <SelectContent>
            {options.map((t) => (
              <SelectItem key={t.id} value={t.id}>
                {t.title}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
      <Button size="sm" disabled={taskId === ''} onClick={() => void attach()}>
        Asociar
      </Button>
      <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>
        Cancelar
      </Button>
    </div>
  )
}

/** Tareas raíz del proyecto, solo lectura. Se crean y editan desde la sección Tareas. */
export function ProjectTasks({
  projectId,
  archived,
  version,
  run,
  onChanged
}: {
  readonly projectId: string
  readonly archived: boolean
  readonly version: number
  readonly run: RunProject
  readonly onChanged: () => void
}) {
  const tasks = useLoad(
    () => listTasks({ project_id: projectId, root_only: true, limit: 100 }),
    `${projectId}-${version}`
  )

  return (
    <section aria-labelledby="project-tasks" className="flex flex-col gap-3">
      <h2 id="project-tasks" className="text-lg font-semibold text-foreground">
        Tareas
      </h2>
      {tasks.loading && tasks.data === null ? <LoadingNote label="Cargando tareas…" /> : null}
      {tasks.error !== null ? <LoadFailure error={tasks.error} what="las tareas del proyecto" onRetry={tasks.reload} /> : null}
      {tasks.data !== null && tasks.data.items.length === 0 ? (
        <p className="text-sm text-muted-foreground">Este proyecto todavía no tiene tareas.</p>
      ) : null}
      {tasks.data !== null && tasks.data.items.length > 0 ? (
        <ul className="flex flex-col divide-y divide-border rounded-[var(--radius-sheet)] border border-border bg-card">
          {tasks.data.items.map((task) => {
            const due = dueLabel(task)
            return (
              <li key={task.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2.5">
                <span className="text-sm text-foreground">{task.title}</span>
                <StatusBadge status={task.status} />
                {due !== null ? <span className="text-xs text-muted-foreground">{due}</span> : null}
              </li>
            )
          })}
        </ul>
      ) : null}
      {tasks.data?.next_cursor != null ? (
        <p className="text-xs text-muted-foreground">Se muestran las primeras 100 tareas; el resto está en Tareas.</p>
      ) : null}
      {archived ? (
        <p className="text-xs text-muted-foreground">Desarchiva el proyecto para asociarle tareas.</p>
      ) : (
        <AttachTask projectId={projectId} run={run} onAttached={onChanged} />
      )}
    </section>
  )
}
