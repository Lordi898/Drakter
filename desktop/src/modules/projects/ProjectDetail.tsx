import { useCallback, useState } from 'react'
import { Button } from '@/components/ui/button'
import type { ReviewOutcome } from '@/stores/confirmations'
import { ConfirmationDialog } from '../tasks/ConfirmationDialog'
import { formatDueDate } from '../tasks/format'
import { archiveProject, deleteProject, getProject, unarchiveProject, updateProject } from './api'
import { ProjectActivity } from './ProjectActivity'
import { ProjectPriority, ProjectStatusBadge } from './ProjectBadges'
import { ProjectForm } from './ProjectForm'
import { ProjectProgressBar } from './ProjectProgressBar'
import { LoadFailure, LoadingNote } from './ProjectStates'
import { ProjectTasks } from './ProjectTasks'
import type { Project, ProjectUpdate } from './types'
import { useLoad } from './useLoad'
import { useProjectRunner } from './useProjectRunner'

function Dates({ project }: { readonly project: Project }) {
  const rows: Array<[string, string]> = []
  if (project.start_date !== null) rows.push(['Inicio', formatDueDate(project.start_date)])
  if (project.target_date !== null) rows.push(['Fecha objetivo', formatDueDate(project.target_date)])
  if (rows.length === 0) return <p className="text-sm text-muted-foreground">Sin fechas definidas.</p>
  return (
    <dl className="flex flex-wrap gap-x-8 gap-y-2">
      {rows.map(([label, value]) => (
        <div key={label}>
          <dt className="text-xs text-muted-foreground">{label}</dt>
          <dd className="text-sm text-foreground">{value}</dd>
        </div>
      ))}
    </dl>
  )
}

export function ProjectDetail({
  id,
  onBack,
  onChanged
}: {
  readonly id: string
  readonly onBack: () => void
  /** Avisa al listado de que debe recargarse. */
  readonly onChanged: () => void
}) {
  const project = useLoad(() => getProject(id), id)
  const [version, setVersion] = useState(0)
  const [editing, setEditing] = useState(false)

  const refresh = useCallback(() => {
    project.reload()
    setVersion((n) => n + 1)
    onChanged()
  }, [project.reload, onChanged])
  const runner = useProjectRunner(refresh)

  function resolved(outcome: ReviewOutcome) {
    runner.resolveConfirmation(outcome)
    if (outcome === 'approved') onBack()
  }

  const backButton = (
    <Button variant="ghost" size="sm" className="mb-4 self-start" onClick={onBack}>
      ← Todos los proyectos
    </Button>
  )

  if (project.error !== null) {
    return (
      <>
        {backButton}
        <LoadFailure error={project.error} what="el proyecto" onRetry={project.reload} />
      </>
    )
  }
  const current = project.data
  if (current === null) {
    return (
      <>
        {backButton}
        <LoadingNote label="Cargando proyecto…" />
      </>
    )
  }
  const archived = current.archived_at !== null

  return (
    <>
      {backButton}
      <header className="mb-8 flex flex-col gap-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex flex-col gap-2">
            <h1 className="type-display text-3xl text-foreground">{current.name}</h1>
            <div className="flex flex-wrap items-center gap-3">
              <ProjectStatusBadge status={current.status} />
              <ProjectPriority priority={current.priority} />
              {archived ? <span className="text-xs text-muted-foreground">Archivado</span> : null}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {archived ? (
              <Button variant="outline" onClick={() => void runner.run(() => unarchiveProject(current.id, current.revision), 'Proyecto restaurado')}>
                Desarchivar
              </Button>
            ) : (
              <>
                <Button variant="outline" onClick={() => setEditing(true)}>
                  Editar
                </Button>
                <Button variant="outline" onClick={() => void runner.run(() => archiveProject(current.id, current.revision), 'Proyecto archivado')}>
                  Archivar
                </Button>
              </>
            )}
            <Button variant="destructive" onClick={() => void runner.run(() => deleteProject(current.id, current.revision))}>
              Eliminar
            </Button>
          </div>
        </div>
        <ProjectProgressBar progress={current.progress} name={current.name} detailed />
      </header>

      <section aria-labelledby="project-summary" className="mb-8 flex flex-col gap-4 rounded-[var(--radius-sheet)] border border-border bg-card p-5">
        <h2 id="project-summary" className="sr-only">
          Resumen
        </h2>
        <div>
          <p className="text-xs text-muted-foreground">Objetivo</p>
          <p className="max-w-[70ch] whitespace-pre-line text-sm text-foreground">
            {current.objective ?? 'Aún no has escrito un objetivo.'}
          </p>
        </div>
        {current.description !== null ? (
          <div>
            <p className="text-xs text-muted-foreground">Descripción</p>
            <p className="max-w-[70ch] whitespace-pre-line text-sm text-foreground">{current.description}</p>
          </div>
        ) : null}
        <Dates project={current} />
      </section>

      <div className="mb-8">
        <ProjectTasks projectId={current.id} archived={archived} version={version} run={runner.run} onChanged={refresh} />
      </div>
      <ProjectActivity projectId={current.id} version={version} />

      <ProjectForm
        open={editing}
        project={current}
        onClose={() => setEditing(false)}
        onStale={refresh}
        onSubmit={async (data) => {
          await updateProject(current.id, data as ProjectUpdate, current.revision)
          refresh()
        }}
      />
      <ConfirmationDialog ticket={runner.ticket} onResolved={resolved} />
    </>
  )
}
