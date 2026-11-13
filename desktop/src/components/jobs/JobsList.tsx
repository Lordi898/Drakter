import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cancelJob, useJobs, type JobOut } from '@/stores/jobs'

const STATE_LABEL: Record<JobOut['state'], string> = {
  running: 'En curso',
  completed: 'Terminado',
  failed: 'Fallido',
  cancelled: 'Cancelado'
}
const STATE_VARIANT = {
  running: 'default',
  completed: 'secondary',
  failed: 'destructive',
  cancelled: 'outline'
} as const

function elapsed(seconds: number): string {
  const m = Math.floor(seconds / 60)
  return m > 0 ? `${m} min ${seconds % 60} s` : `${seconds} s`
}

/** Trabajos en segundo plano. No pinta nada si no hay ninguno. */
export function JobsList() {
  const jobs = useJobs()
  if (jobs.length === 0) return null

  return (
    <section aria-labelledby="context-jobs" className="border-t border-chassis-line pt-4">
      <h3 id="context-jobs" className="mb-3 text-sm font-medium">
        Trabajos
      </h3>
      <ul className="flex flex-col gap-3 text-sm">
        {jobs.map((job) => (
          <li key={job.job_id} className="flex flex-col gap-1">
            <div className="flex items-start justify-between gap-2">
              <span className="min-w-0 break-words">{job.title}</span>
              <Badge variant={STATE_VARIANT[job.state]}>{STATE_LABEL[job.state]}</Badge>
            </div>
            <p className="text-xs text-chassis-muted">
              {elapsed(job.elapsed_s)} · {job.tool_calls} {job.tool_calls === 1 ? 'herramienta' : 'herramientas'}
            </p>
            {job.pending_actions > 0 ? (
              <p className="text-xs text-chassis-muted">
                {job.pending_actions} {job.pending_actions === 1 ? 'acción pendiente' : 'acciones pendientes'} de su
                confirmación
              </p>
            ) : null}
            {job.state === 'running' ? (
              <Button
                type="button"
                size="xs"
                variant="outline"
                className="self-start"
                onClick={() => void cancelJob(job.job_id)}
              >
                Cancelar
              </Button>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  )
}
