import { Lock, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { addTaskDependency, listTasks, removeTaskDependency } from './api'
import { Field } from './Field'
import { StatusBadge } from './TaskBadges'
import type { RunTask } from './useTaskRunner'
import { errorMessage } from './useTasks'
import { isOpen } from './format'
import type { Task, TaskDetail } from './types'

export interface DependenciesTabProps {
  readonly detail: TaskDetail
  readonly run: RunTask
  readonly onOpen: (id: string) => void
}

export function DependenciesTab({ detail, run, onOpen }: DependenciesTabProps) {
  const [candidates, setCandidates] = useState<readonly Task[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)
  const [choice, setChoice] = useState('')

  useEffect(() => {
    let current = true
    listTasks({ archived: 'exclude', limit: 100, sort: 'title' })
      .then((page) => {
        if (current) setCandidates(page.items)
      })
      .catch((error: unknown) => {
        if (current) setLoadError(errorMessage(error))
      })
    return () => {
      current = false
    }
  }, [detail.revision])

  const taken = new Set([detail.id, ...detail.dependencies.map((dep) => dep.id)])
  const options = candidates.filter((task) => !taken.has(task.id))
  const waiting = detail.dependencies.filter((dep) => isOpen(dep.status))

  return (
    <div className="flex flex-col gap-5">
      {detail.blocked ? (
        <p role="status" className="flex items-start gap-2 rounded-md border border-destructive/40 p-3 text-sm">
          <Lock aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-destructive" />
          <span>
            <strong className="font-semibold text-destructive">Bloqueada.</strong> Espera a:{' '}
            {waiting.map((dep) => dep.title).join(', ')}.
          </span>
        </p>
      ) : null}

      <section aria-labelledby="deps-title" className="flex flex-col gap-2">
        <h3 id="deps-title" className="text-sm font-semibold">
          Depende de
        </h3>
        {detail.dependencies.length === 0 ? (
          <p className="text-sm text-muted-foreground">No depende de ninguna otra tarea.</p>
        ) : (
          <ul className="flex flex-col">
            {detail.dependencies.map((dep) => (
              <li key={dep.id} className="flex items-center gap-2 border-b py-2">
                <button type="button" onClick={() => onOpen(dep.id)} className="min-w-0 flex-1 truncate rounded-sm text-left text-sm">
                  {dep.title}
                </button>
                <StatusBadge status={dep.status} />
                <Button
                  variant="ghost"
                  size="icon-xs"
                  aria-label={`Quitar la dependencia de «${dep.title}»`}
                  onClick={() => void run(() => removeTaskDependency(detail.id, dep.id), 'Dependencia quitada')}
                >
                  <X aria-hidden="true" />
                </Button>
              </li>
            ))}
          </ul>
        )}
        <div className="flex items-end gap-2 pt-1">
          <Field label="Añadir dependencia" error={loadError} className="flex-1">
            {(control) => (
              <Select value={choice} onValueChange={setChoice}>
                <SelectTrigger id={control.id} className="w-full" aria-describedby={control['aria-describedby']}>
                  <SelectValue placeholder={options.length === 0 ? 'No hay tareas disponibles' : 'Elige una tarea'} />
                </SelectTrigger>
                <SelectContent>
                  {options.map((task) => (
                    <SelectItem key={task.id} value={task.id}>
                      {task.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </Field>
          <Button
            variant="outline"
            disabled={choice === ''}
            onClick={() => {
              void run(() => addTaskDependency(detail.id, choice), 'Dependencia añadida').then((result) => {
                if (result !== undefined) setChoice('')
              })
            }}
          >
            Añadir
          </Button>
        </div>
      </section>

      <section aria-labelledby="dependents-title" className="flex flex-col gap-2">
        <h3 id="dependents-title" className="text-sm font-semibold">
          Bloquea a
        </h3>
        {detail.dependents.length === 0 ? (
          <p className="text-sm text-muted-foreground">Ninguna tarea espera a esta.</p>
        ) : (
          <ul className="flex flex-col">
            {detail.dependents.map((dep) => (
              <li key={dep.id} className="flex items-center gap-2 border-b py-2">
                <button type="button" onClick={() => onOpen(dep.id)} className="min-w-0 flex-1 truncate rounded-sm text-left text-sm">
                  {dep.title}
                </button>
                <StatusBadge status={dep.status} />
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
