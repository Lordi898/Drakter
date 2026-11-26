import { useEffect, useId, useRef, useState, type MouseEvent } from 'react'
import { Button } from '@/components/ui/button'
import type { PendingConfirmation } from '@/services/protocol'
import { reviewConfirmation, useConfirmations } from '@/stores/confirmations'

const CONFLICT_NOTICE = 'Los elementos han cambiado; la acción no se ha ejecutado.'
const FAILED_NOTICE = 'No se ha podido completar la decisión. Comprueba el estado antes de repetir.'
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
      if (outcome === 'conflict') setProblem(CONFLICT_NOTICE)
      else if (outcome === 'failed') setProblem(FAILED_NOTICE)
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
          {typeof confirmation.affected_count === 'number' ? (
            <p className="text-xs text-muted-foreground">
              Afecta a {confirmation.affected_count} {confirmation.affected_count === 1 ? 'elemento' : 'elementos'}
            </p>
          ) : null}
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
            data-confirmation-review={confirmation.action_id}
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

/** El foco está en un campo de texto: no se le roba (el aviso sigue visible y anunciado). */
function typingSomewhere(): boolean {
  const active = document.activeElement
  return active instanceof HTMLElement && active.closest('input, textarea, select, [contenteditable="true"]') !== null
}

/**
 * Avisa de lo pendiente y abre la revisión. La decisión se toma en el diálogo nativo
 * del proceso principal: aquí no hay ni debe haber ningún control para aprobar o rechazar.
 *
 * Siempre a la vista, en cualquier modo e interfaz (CLAUDE.md §8): capa fija por encima de Jarvis
 * (`z-40`), de los diálogos (`z-50`) y de cualquier lienzo; solo los avisos (Sonner) van más arriba.
 * Una confirmación nueva se lleva el foco a su «Revisar», salvo que se esté escribiendo.
 */
export function ConfirmationHost() {
  const confirmations = useConfirmations()
  const seen = useRef<ReadonlySet<string>>(new Set())

  useEffect(() => {
    const fresh = confirmations.find((c) => !seen.current.has(c.action_id))
    seen.current = new Set(confirmations.map((c) => c.action_id))
    if (!fresh || typingSomewhere()) return
    const frame = requestAnimationFrame(() => {
      document
        .querySelector<HTMLButtonElement>(`[data-confirmation-review="${CSS.escape(fresh.action_id)}"]`)
        ?.focus()
    })
    return () => cancelAnimationFrame(frame)
  }, [confirmations])

  if (confirmations.length === 0) return null

  return (
    <div className="pointer-events-none fixed inset-x-0 top-14 z-[70] flex justify-center px-4">
      <ul
        role="status"
        aria-label="Confirmaciones pendientes"
        className="pointer-events-auto flex max-h-[40vh] w-full max-w-xl flex-col gap-2 overflow-y-auto rounded-lg shadow-lg"
      >
        {confirmations.map((confirmation) => (
          <ConfirmationNotice key={confirmation.action_id} confirmation={confirmation} />
        ))}
      </ul>
    </div>
  )
}
