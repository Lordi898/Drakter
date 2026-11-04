import { Search } from 'lucide-react'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Field, TextInput } from './Field'
import {
  PRIORITIES,
  PRIORITY_LABELS,
  TASK_STATUSES,
  TASK_STATUS_LABELS,
  type Priority,
  type TaskStatus
} from './types'

export interface TaskFilterState {
  readonly q: string
  readonly status: TaskStatus | 'all'
  readonly priority: Priority | 'all'
  readonly archived: 'exclude' | 'only'
  readonly rootOnly: boolean
}

export const DEFAULT_FILTERS: TaskFilterState = {
  q: '',
  status: 'all',
  priority: 'all',
  archived: 'exclude',
  rootOnly: true
}

export interface TaskFiltersProps {
  readonly value: TaskFilterState
  readonly onChange: (next: TaskFilterState) => void
}

export function TaskFilters({ value, onChange }: TaskFiltersProps) {
  return (
    <form
      role="search"
      aria-label="Filtros de tareas"
      className="flex flex-wrap items-end gap-4 pb-4"
      onSubmit={(event) => event.preventDefault()}
    >
      <Field label="Buscar" className="min-w-56 flex-1">
        {(control) => (
          <div className="relative">
            <Search
              aria-hidden="true"
              className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
            />
            <TextInput
              {...control}
              type="search"
              className="pl-9"
              placeholder="Título o descripción"
              value={value.q}
              onChange={(event) => onChange({ ...value, q: event.target.value })}
            />
          </div>
        )}
      </Field>
      <Field label="Estado">
        {(control) => (
          <Select
            value={value.status}
            onValueChange={(status) => onChange({ ...value, status: status as TaskFilterState['status'] })}
          >
            <SelectTrigger id={control.id} className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos</SelectItem>
              {TASK_STATUSES.map((status) => (
                <SelectItem key={status} value={status}>
                  {TASK_STATUS_LABELS[status]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </Field>
      <Field label="Prioridad">
        {(control) => (
          <Select
            value={value.priority}
            onValueChange={(priority) =>
              onChange({ ...value, priority: priority as TaskFilterState['priority'] })
            }
          >
            <SelectTrigger id={control.id} className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todas</SelectItem>
              {PRIORITIES.map((priority) => (
                <SelectItem key={priority} value={priority}>
                  {PRIORITY_LABELS[priority]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </Field>
      <Field label="Mostrar">
        {(control) => (
          <Select
            value={value.archived}
            onValueChange={(archived) => onChange({ ...value, archived: archived as TaskFilterState['archived'] })}
          >
            <SelectTrigger id={control.id} className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="exclude">Activas</SelectItem>
              <SelectItem value="only">Archivadas</SelectItem>
            </SelectContent>
          </Select>
        )}
      </Field>
      <div className="flex items-center gap-2 pb-2">
        <Switch
          id="tasks-root-only"
          checked={value.rootOnly}
          onCheckedChange={(rootOnly) => onChange({ ...value, rootOnly })}
        />
        <Label htmlFor="tasks-root-only">Solo principales</Label>
      </div>
    </form>
  )
}
