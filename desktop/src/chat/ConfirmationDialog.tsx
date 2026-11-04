import { useEffect, useId, useState, type MouseEvent } from 'react'
import { Button } from '@/components/ui/button'
import type { PendingConfirmation } from '@/services/protocol'
import { reviewConfirmation, useConfirmations } from '@/stores/confirmations'

const UNAVAILABLE_NOTICE = 'No se puede decidir desde aquí, así que la acción no se ejecutará.'
const REVIEW_FAILED_NOTICE = 'No se ha podido abrir la revisión. Inténtalo de nuevo.'

function formatRemaining(ms: number): string {
  const seconds = Math.max(0, Math.ceil(ms / 1000))
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}

function useRemainingMs(expiresAt: string): number {
  const deadline = Date.parse(expiresAt)
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  return deadline - now
}

function ConfirmationNotice({ confirmation }: { confirmation: PendingConfirmation }) {
  const [pending, setPending] = useState(false)
  const [problem, setProblem] = useState<string | null>(null)
  const remaining = useRemainingMs(confirmation.expires_at)
  const summaryId = useId()

  async function review(event: MouseEvent<HTMLButtonElement>): Promise<void> {
    setPending(true)
    setProblem(null)
    try {
      const outcome = await reviewConfirmation(confirmation.action_id, event)
      if (outcome === 'unavailable') setProblem(UNAVAILABLE_NOTICE)
    } catch {
      setProblem(REVIEW_FAILED_NOTICE)
    } finally {
      setPending(false)
    }
  }

  return (
    <li className="flex flex-col gap-1 rounded-md border border-warning/60 bg-card px-3 py-2 text-sm text-card-foreground">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-xs text-muted-foreground">Drakter necesita tu confirmación</p>
          <p id={summaryId} className="max-h-24 overflow-y-auto break-words whitespace-pre-wrap">
            {confirmation.summary}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span role="timer" aria-live="off" aria-label="Tiempo restante" className="text-xs text-muted-foreground tabular-nums">
            {formatRemaining(remaining)}
          </span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={pending || remaining <= 0}
            aria-describedby={summaryId}
            onClick={(event) => void review(event)}
          >
            {pending ? 'Revisando…' : 'Revisar'}
          </Button>
        </div>
      </div>
      {problem ? (
        <p role="alert" className="text-xs text-destructive">
          {problem}
        </p>
      ) : null}
    </li>
  )
}

/**
 * Avisa de lo pendiente y abre la revisión. La decisión se toma en el diálogo nativo
 * del proceso principal: aquí no hay ni debe haber ningún control para aprobar o rechazar.
 */
export function ConfirmationHost() {
  const confirmations = useConfirmations()

  if (confirmations.length === 0) return null

  return (
    <ul role="status" aria-label="Confirmaciones pendientes" className="flex max-h-[30vh] flex-col gap-2 overflow-y-auto">
      {confirmations.map((confirmation) => (
        <ConfirmationNotice key={confirmation.action_id} confirmation={confirmation} />
      ))}
    </ul>
  )
}
