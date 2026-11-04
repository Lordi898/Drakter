import { useEffect, useState } from 'react'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { TextInput } from '../tasks/Field'
import {
  PRIORITIES,
  PRIORITY_LABELS,
  PROJECT_STATUSES,
  PROJECT_STATUS_LABELS,
  type ArchivedFilter,
  type Priority,
  type ProjectStatus
} from './types'

export interface ProjectFilterValues {
  readonly q: string
  readonly status: ProjectStatus | 'all'
  readonly priority: Priority | 'all'
  readonly archived: ArchivedFilter
  readonly sort: string
}

export const DEFAULT_FILTERS: ProjectFilterValues = {
  q: '',
  status: 'all',
  priority: 'all',
  archived: 'exclude',
  sort: '-updated_at'
}

const ARCHIVED_LABELS: Readonly<Record<ArchivedFilter, string>> = {
  exclude: 'Sin archivados',
  only: 'Solo archivados',
  include: 'Todos'
}

const SORT_LABELS: Readonly<Record<string, string>> = {
  '-updated_at': 'Modificados hace poco',
  name: 'Nombre',
  target_date: 'Fecha objetivo',
  '-priority': 'Prioridad',
  '-created_at': 'Más recientes'
}

function Option<T extends string>({
  label,
  value,
  onChange,
  options
}: {
  readonly label: string
  readonly value: T
  readonly onChange: (next: T) => void
  readonly options: ReadonlyArray<readonly [T, string]>
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      <Select value={value} onValueChange={(next) => onChange(next as T)}>
        <SelectTrigger size="sm" aria-label={label} className="min-w-36">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map(([key, text]) => (
            <SelectItem key={key} value={key}>
              {text}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

export function ProjectFilters({
  values,
  onChange
}: {
  readonly values: ProjectFilterValues
  readonly onChange: (next: ProjectFilterValues) => void
}) {
  const [text, setText] = useState(values.q)
  useEffect(() => {
    if (text === values.q) return
    const timer = setTimeout(() => onChange({ ...values, q: text }), 300)
    return () => clearTimeout(timer)
  }, [text, values, onChange])

  return (
    <div role="search" aria-label="Filtrar proyectos" className="flex flex-wrap items-end gap-3 pb-6">
      <div className="flex min-w-56 flex-1 flex-col gap-1.5">
        <Label htmlFor="project-search" className="text-xs text-muted-foreground">
          Buscar
        </Label>
        <TextInput
          id="project-search"
          type="search"
          value={text}
          placeholder="Nombre o descripción"
          onChange={(event) => setText(event.target.value)}
          className="h-8"
        />
      </div>
      <Option
        label="Estado"
        value={values.status}
        onChange={(status) => onChange({ ...values, status })}
        options={[['all', 'Todos'], ...PROJECT_STATUSES.map((s) => [s, PROJECT_STATUS_LABELS[s]] as const)]}
      />
      <Option
        label="Prioridad"
        value={values.priority}
        onChange={(priority) => onChange({ ...values, priority })}
        options={[['all', 'Todas'], ...PRIORITIES.map((p) => [p, PRIORITY_LABELS[p]] as const)]}
      />
      <Option
        label="Archivo"
        value={values.archived}
        onChange={(archived) => onChange({ ...values, archived })}
        options={Object.entries(ARCHIVED_LABELS) as Array<[ArchivedFilter, string]>}
      />
      <Option
        label="Orden"
        value={values.sort}
        onChange={(sort) => onChange({ ...values, sort })}
        options={Object.entries(SORT_LABELS) as Array<[string, string]>}
      />
    </div>
  )
}
