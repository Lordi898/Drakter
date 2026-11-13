import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { taskHistory } from './api'
import { describeHistory } from './format'
import { errorMessage } from './useTasks'
import type { HistoryEntry } from './types'

export interface HistoryTabProps {
  readonly taskId: string
  readonly version: number
}

export function HistoryTab({ taskId, version }: HistoryTabProps) {
  const [entries, setEntries] = useState<readonly HistoryEntry[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let current = true
    setLoading(true)
    setError(null)
    taskHistory(taskId)
      .then((page) => {
        if (!current) return
        setEntries(page.items)
        setTotal(page.total)
      })
      .catch((e: unknown) => {
        if (current) setError(errorMessage(e))
      })
      .finally(() => {
        if (current) setLoading(false)
      })
    return () => {
      current = false
    }
  }, [taskId, version, attempt])

  async function more() {
    if (entries.length >= total) return
    try {
      const page = await taskHistory(taskId, 50, entries.length)
      setEntries((list) => [...list, ...page.items])
      setTotal(page.total)
    } catch (e) {
      setError(errorMessage(e))
    }
  }

  if (error !== null) {
    return (
      <div role="alert" className="flex flex-col items-start gap-2 text-sm">
        <p className="text-destructive">No se pudo cargar el historial: {error}</p>
        <Button size="sm" variant="outline" onClick={() => setAttempt((n) => n + 1)}>
          Reintentar
        </Button>
      </div>
    )
  }
  if (loading) return <p className="text-sm text-muted-foreground">Cargando historial…</p>
  if (entries.length === 0) return <p className="text-sm text-muted-foreground">Todavía no hay movimientos.</p>

  return (
    <div className="flex flex-col gap-3">
      <ol className="flex flex-col">
        {entries.map((entry) => {
          const line = describeHistory(entry)
          return (
            <li key={line.id} className="flex flex-col gap-1 border-b py-3 text-sm">
              <p>
                <span className={line.isAgent ? 'voice-drakter font-semibold' : 'font-semibold'}>{line.actor}</span>{' '}
                {line.summary}
              </p>
              {line.details.length > 0 ? (
                <ul className="flex flex-col gap-0.5 text-xs text-muted-foreground">
                  {line.details.map((detail) => (
                    <li key={detail}>{detail}</li>
                  ))}
                </ul>
              ) : null}
              <p className="text-xs text-muted-foreground">{line.when}</p>
            </li>
          )
        })}
      </ol>
      {entries.length < total ? (
        <Button size="sm" variant="outline" className="self-start" onClick={() => void more()}>
          Cargar más
        </Button>
      ) : null}
    </div>
  )
}
