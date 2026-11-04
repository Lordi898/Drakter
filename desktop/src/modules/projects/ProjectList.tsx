import { Button } from '@/components/ui/button'
import { formatDueDate } from '../tasks/format'
import { ProjectPriority, ProjectStatusBadge } from './ProjectBadges'
import { ProjectProgressBar } from './ProjectProgressBar'
import type { Project } from './types'

function ProjectRow({ project, onOpen }: { readonly project: Project; readonly onOpen: () => void }) {
  return (
    <li>
      <button
        type="button"
        onClick={onOpen}
        className="flex w-full flex-col gap-3 rounded-[var(--radius-sheet)] border border-border bg-card p-4 text-left transition-colors outline-none hover:bg-accent focus-visible:ring-[3px] focus-visible:ring-ring/50"
      >
        <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span className="font-medium text-foreground">{project.name}</span>
          <ProjectStatusBadge status={project.status} />
          {project.archived_at !== null ? (
            <span className="text-xs text-muted-foreground">Archivado</span>
          ) : null}
        </span>
        <span className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <ProjectPriority priority={project.priority} />
          {project.target_date !== null ? (
            <span className="text-xs text-muted-foreground">
              Para el {formatDueDate(project.target_date)}
            </span>
          ) : null}
        </span>
        <ProjectProgressBar progress={project.progress} name={project.name} />
      </button>
    </li>
  )
}

export function ProjectList({
  items,
  hasMore,
  loadingMore,
  onLoadMore,
  onOpen
}: {
  readonly items: readonly Project[]
  readonly hasMore: boolean
  readonly loadingMore: boolean
  readonly onLoadMore: () => void
  readonly onOpen: (id: string) => void
}) {
  return (
    <div className="flex flex-col gap-4">
      <ul aria-label="Proyectos" className="flex flex-col gap-3">
        {items.map((project) => (
          <ProjectRow key={project.id} project={project} onOpen={() => onOpen(project.id)} />
        ))}
      </ul>
      {hasMore ? (
        <Button variant="outline" className="self-start" disabled={loadingMore} onClick={onLoadMore}>
          {loadingMore ? 'Cargando…' : 'Cargar más'}
        </Button>
      ) : null}
    </div>
  )
}
