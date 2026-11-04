import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { archiveTask, completeTask, deleteTask, reopenTask, unarchiveTask } from './api'
import type { RunTask } from './useTaskRunner'
import type { Task } from './types'

type Target = Pick<Task, 'id' | 'title' | 'revision' | 'status' | 'subtask_count' | 'completed_subtask_count'>

export interface TaskActions {
  readonly toggle: (task: Target) => void
  readonly archive: (task: Pick<Task, 'id' | 'revision'>) => void
  readonly unarchive: (task: Pick<Task, 'id' | 'revision'>) => void
  readonly remove: (task: Pick<Task, 'id' | 'revision'>) => void
  /** Diálogo de subtareas abiertas; el llamador lo renderiza una sola vez. */
  readonly subtasksPrompt: React.ReactNode
}

/** Acciones de una tarea sobre `run`. Completar con subtareas abiertas pregunta antes. */
export function useTaskActions(run: RunTask): TaskActions {
  const [asking, setAsking] = useState<Target | null>(null)

  function toggle(task: Target) {
    if (task.status === 'completed') {
      void run(() => reopenTask(task.id, task.revision), 'Tarea reabierta')
    } else if (task.subtask_count > task.completed_subtask_count) {
      setAsking(task)
    } else {
      void run(() => completeTask(task.id, task.revision), 'Tarea completada')
    }
  }

  function finish(withSubtasks: boolean) {
    const task = asking
    setAsking(null)
    if (task === null) return
    void run(
      () => completeTask(task.id, task.revision, withSubtasks),
      withSubtasks ? 'Tarea y subtareas completadas' : 'Tarea completada'
    )
  }

  const subtasksPrompt = (
    <Dialog open={asking !== null} onOpenChange={(open) => !open && setAsking(null)}>
      <DialogContent className="rounded-[var(--radius-sheet)]">
        <DialogHeader>
          <DialogTitle>Quedan subtareas abiertas</DialogTitle>
          <DialogDescription>
            «{asking?.title}» tiene {asking ? asking.subtask_count - asking.completed_subtask_count : 0} subtareas sin
            completar. ¿Las completo también?
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => setAsking(null)}>
            Cancelar
          </Button>
          <Button onClick={() => finish(true)}>Completar todo</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )

  return {
    toggle,
    archive: (task) => void run(() => archiveTask(task.id, task.revision), 'Tarea archivada'),
    unarchive: (task) => void run(() => unarchiveTask(task.id, task.revision), 'Tarea restaurada'),
    remove: (task) => void run(() => deleteTask(task.id, task.revision)),
    subtasksPrompt
  }
}
