import type { ProjectProgress } from './types'

/** Muestra el avance que calcula el backend. No recalcula nada. */
export function ProjectProgressBar({
  progress,
  name,
  detailed = false
}: {
  readonly progress: ProjectProgress
  readonly name: string
  readonly detailed?: boolean
}) {
  const manual = progress.source === 'manual'
  return (
    <div className="flex flex-col gap-1.5">
      <div
        role="progressbar"
        aria-label={`Progreso de ${name}`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={progress.percent}
        aria-valuetext={`${progress.percent} %`}
        className="h-2 w-full overflow-hidden rounded-full bg-muted"
      >
        <div className="h-full bg-primary" style={{ width: `${progress.percent}%` }} />
      </div>
      <p className="text-xs text-muted-foreground">
        <span className="font-medium text-foreground">{progress.percent} %</span>
        {' · '}
        {progress.completed} de {progress.total} {progress.total === 1 ? 'tarea' : 'tareas'}
        {manual ? ` · manual (según las tareas sería ${progress.computed_percent} %)` : ''}
        {detailed && progress.overdue > 0
          ? ` · ${progress.overdue} ${progress.overdue === 1 ? 'vencida' : 'vencidas'}`
          : ''}
      </p>
    </div>
  )
}
