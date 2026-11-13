import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { formatDueDate, formatInstant } from '../tasks/format'
import { actorLabel } from '../tasks/format'
import type { HistoryEntry } from '../tasks/types'
import { projectActivity } from './api'
import { LoadFailure, LoadingNote } from './ProjectStates'
import { PRIORITY_LABELS, PROJECT_STATUS_LABELS, type Priority, type ProjectStatus } from './types'
import { toLoadError, type LoadError } from './useLoad'

const ACTIONS: Readonly<Record<string, string>> = {
  'project.create': 'creó el proyecto',
  'project.update': 'modificó el proyecto',
  'project.archive': 'archivó el proyecto',
  'project.unarchive': 'restauró el proyecto',
  'project.delete': 'eliminó el proyecto',
  'task.create': 'creó una tarea',
  'task.update': 'modificó una tarea',
  'task.complete': 'completó una tarea',
  'task.reopen': 'reabrió una tarea',
  'task.archive': 'archivó una tarea',
  'task.unarchive': 'restauró una tarea',
  'task.delete': 'eliminó una tarea'
}

const FIELDS: Readonly<Record<string, string>> = {
  name: 'Nombre',
  description: 'Descripción',
  objective: 'Objetivo',
  status: 'Estado',
  priority: 'Prioridad',
  start_date: 'Inicio',
  target_date: 'Fecha objetivo',
  manual_progress: 'Progreso manual',
  title: 'Título',
  project_id: 'Proyecto',
  due_date: 'Fecha límite'
}

function show(field: string, value: unknown): string {
  if (value === null || value === undefined || value === '') return 'vacío'
  if (typeof value !== 'string') return String(value)
  if (field === 'status') return PROJECT_STATUS_LABELS[value as ProjectStatus] ?? value
  if (field === 'priority') return PRIORITY_LABELS[value as Priority] ?? value
  if (field.endsWith('_date')) return formatDueDate(value)
  return value.length > 60 ? `${value.slice(0, 57)}…` : value
}

function changes(entry: HistoryEntry): string[] {
  const lines: string[] = []
  for (const [field, change] of Object.entries(entry.changes ?? {})) {
    const label = FIELDS[field]
    if (label === undefined) continue
    if (typeof change === 'object' && change !== null && 'changed' in change) {
      lines.push(`${label}: modificado`)
    } else if (typeof change === 'object' && change !== null && ('from' in change || 'to' in change)) {
      const c = change as { from?: unknown; to?: unknown }
      lines.push(`${label}: ${show(field, c.from)} → ${show(field, c.to)}`)
    }
  }
  return lines
}

function describe(entry: HistoryEntry): string {
  const base = ACTIONS[entry.action] ?? 'realizó un cambio'
  if (entry.result === 'denied') return `intentó sin permiso: ${base}`
  if (entry.result === 'failed') return `no pudo completar: ${base}`
  if (entry.result === 'confirmation_required') return `pidió confirmación para: ${base}`
  return base
}

/** Actividad del proyecto y de sus tareas, de más reciente a más antigua. */
export function ProjectActivity({ projectId, version }: { readonly projectId: string; readonly version: number }) {
  const [items, setItems] = useState<readonly HistoryEntry[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<LoadError | null>(null)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    let current = true
    setLoading(true)
    setError(null)
    projectActivity(projectId)
      .then((page) => {
        if (!current) return
        setItems(page.items)
        setTotal(page.total)
      })
      .catch((e: unknown) => current && setError(toLoadError(e)))
      .finally(() => current && setLoading(false))
    return () => {
      current = false
    }
  }, [projectId, version, tick])

  async function more() {
    if (items.length >= total) return
    setLoading(true)
    try {
      const page = await projectActivity(projectId, 30, items.length)
      setItems((c) => [...c, ...page.items])
      setTotal(page.total)
    } catch (e) {
      setError(toLoadError(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section aria-labelledby="project-activity" className="flex flex-col gap-3">
      <h2 id="project-activity" className="text-lg font-semibold text-foreground">
        Actividad
      </h2>
      {error !== null ? <LoadFailure error={error} what="la actividad" onRetry={() => setTick((n) => n + 1)} /> : null}
      {loading && items.length === 0 && error === null ? <LoadingNote label="Cargando actividad…" /> : null}
      {!loading && error === null && items.length === 0 ? (
        <p className="text-sm text-muted-foreground">Todavía no hay actividad registrada.</p>
      ) : null}
      {items.length > 0 ? (
        <ol className="flex flex-col gap-3 border-l border-border pl-4">
          {items.map((entry) => {
            const lines = changes(entry)
            return (
              <li key={entry.id} className="flex flex-col gap-0.5">
                <p className="text-sm text-foreground">
                  <span className="font-medium">{actorLabel(entry.actor_type)}</span> {describe(entry)}
                </p>
                {lines.map((line) => (
                  <p key={line} className="text-xs text-muted-foreground">
                    {line}
                  </p>
                ))}
                <time dateTime={entry.occurred_at} className="text-xs text-muted-foreground">
                  {formatInstant(entry.occurred_at)}
                </time>
              </li>
            )
          })}
        </ol>
      ) : null}
      {items.length < total ? (
        <Button variant="outline" size="sm" className="self-start" disabled={loading} onClick={() => void more()}>
          {loading ? 'Cargando…' : 'Ver más'}
        </Button>
      ) : null}
    </section>
  )
}
