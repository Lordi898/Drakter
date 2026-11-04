import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { registerConfirmation, reviewConfirmation, type ReviewOutcome } from '@/stores/confirmations'
import type { PendingTicket } from './useTaskRunner'

export interface ConfirmationDialogProps {
  /** Confirmación que el backend pidió; `null` mantiene el diálogo cerrado. */
  readonly ticket: PendingTicket | null
  /** `approved` recarga; `rejected` cierra; `dismissed` no hace nada; `expired`/`unavailable` avisan. */
  readonly onResolved: (outcome: ReviewOutcome) => void
}

/**
 * Muestra lo que el backend pide confirmar. La decisión NO se toma aquí: el botón abre
 * la revisión nativa del proceso principal, que es quien aprueba o rechaza.
 */
export function ConfirmationDialog({ ticket, onResolved }: ConfirmationDialogProps) {
  const [busy, setBusy] = useState(false)

  function review(event: React.MouseEvent<HTMLButtonElement>) {
    if (ticket === null || busy) return
    const nativeEvent = event.nativeEvent
    setBusy(true)
    registerConfirmation(ticket)
    reviewConfirmation(ticket.id, nativeEvent)
      .then(onResolved)
      .catch(() => onResolved('unavailable'))
      .finally(() => setBusy(false))
  }

  return (
    <Dialog
      open={ticket !== null}
      onOpenChange={(open) => {
        if (!open) onResolved('rejected')
      }}
    >
      <DialogContent className="rounded-[var(--radius-sheet)]">
        <DialogHeader>
          <DialogTitle>Esto necesita tu confirmación</DialogTitle>
          <DialogDescription>No se hará nada hasta que lo apruebes en la ventana de revisión.</DialogDescription>
        </DialogHeader>
        {ticket !== null ? (
          <div className="flex flex-col gap-2 rounded-md border border-destructive/40 bg-card p-4">
            <p className="text-sm font-medium text-foreground">{ticket.summary}</p>
            <p className="text-sm text-muted-foreground">
              {ticket.affected_count === 1
                ? 'Afecta a 1 elemento.'
                : `Afecta a ${ticket.affected_count} elementos.`}
            </p>
          </div>
        ) : null}
        <DialogFooter>
          <Button variant="outline" onClick={() => onResolved('rejected')}>
            Cerrar
          </Button>
          <Button variant="destructive" disabled={busy} onClick={review}>
            {busy ? 'Esperando tu decisión…' : 'Revisar y decidir'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
