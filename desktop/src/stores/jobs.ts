import { useSyncExternalStore } from 'react'
import { describeError } from '@/services/api'
import { notify } from '@/services/notify'
import { subscribeLinkStatus, subscribeResync, subscribeServerEvents } from '@/services/ws'
import type { JobOut } from '../../../contracts/ts'

export type { JobOut }

/** Trabajos en segundo plano: seed por REST, eventos `job.*` y relectura tras un resync. */
let items: readonly JobOut[] = []
let refreshing = false
const listeners = new Set<() => void>()

function emit(): void {
  listeners.forEach((listener) => listener())
}

function upsert(job: JobOut): void {
  const known = items.some((j) => j.job_id === job.job_id)
  items = known ? items.map((j) => (j.job_id === job.job_id ? job : j)) : [job, ...items]
  emit()
}

function patch(jobId: string, change: (job: JobOut) => JobOut): void {
  if (!items.some((j) => j.job_id === jobId)) return
  items = items.map((j) => (j.job_id === jobId ? change(j) : j))
  emit()
}

async function refresh(): Promise<void> {
  if (refreshing || typeof window === 'undefined' || typeof window.api === 'undefined') return
  refreshing = true
  try {
    const result = await window.api.jobs.list()
    if (result.ok) {
      items = result.data.items
      emit()
    }
  } catch {
    console.warn('No se pudieron leer los trabajos.')
  } finally {
    refreshing = false
  }
}

const STATE_TITLE = { completed: 'Trabajo terminado', failed: 'El trabajo ha fallado', cancelled: 'Trabajo cancelado' } as const

subscribeServerEvents((event) => {
  switch (event.type) {
    case 'job.started': {
      const p = event.payload
      if (items.some((j) => j.job_id === p.job_id)) return
      upsert({
        job_id: p.job_id,
        title: p.title,
        state: 'running',
        reason: null,
        pending_actions: 0,
        created_at: p.created_at,
        finished_at: null,
        elapsed_s: 0,
        tool_calls: 0,
        last_tool: null
      })
      return
    }
    case 'job.progress': {
      const p = event.payload
      patch(p.job_id, (j) => ({ ...j, state: 'running', elapsed_s: p.elapsed_s, tool_calls: p.tool_calls, last_tool: p.last_tool ?? null }))
      return
    }
    case 'job.finished': {
      const p = event.payload
      const job = items.find((j) => j.job_id === p.job_id)
      if (job?.state === p.state) return // ya reflejado (p. ej. cancelado desde la lista)
      patch(p.job_id, (j) => ({
        ...j,
        state: p.state,
        reason: p.reason ?? null,
        pending_actions: p.pending_actions,
        finished_at: p.finished_at
      }))
      notify({
        tone: p.state === 'completed' ? 'success' : p.state === 'failed' ? 'error' : 'info',
        title: STATE_TITLE[p.state],
        ...(job ? { body: job.title } : {})
      })
      return
    }
    default:
  }
})
subscribeResync(() => void refresh())
subscribeLinkStatus((status) => {
  if (status === 'open') void refresh()
})

export async function cancelJob(jobId: string): Promise<void> {
  try {
    const result = await window.api.jobs.cancel(jobId)
    if (result.ok) upsert(result.data)
    else notify({ tone: 'warning', title: 'No se pudo cancelar el trabajo', body: 'Puede que ya haya terminado.' })
  } catch (error) {
    notify({ tone: 'error', title: 'No se pudo cancelar el trabajo', body: describeError(error, 'Inténtalo de nuevo.') })
  }
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export function useJobs(): readonly JobOut[] {
  return useSyncExternalStore(subscribe, () => items)
}
