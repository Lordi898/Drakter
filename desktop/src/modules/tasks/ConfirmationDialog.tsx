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
import { notify } from '@/services/notify'
import { confirmations, type ConfirmationTicket } from './client'
import { errorMessage } from './useTasks'

export type ConfirmationOutcome = 'approved' | 'rejected'

export interface ConfirmationDialogProps {
  /** Ticket devuelto por el backend; `null` mantiene el diálogo cerrado. */
  readonly ticket: ConfirmationTicket | null
  /** Se llama tras aprobar o rechazar en el backend. Nada se ejecuta sin la aprobación explícita. */
  readonly onResolved: (outcome: ConfirmationOutcome) => void
}

/** Muestra siempre lo que el backend pide confirmar. Cerrar sin aprobar equivale a rechazar. */
export function ConfirmationDialog({ ticket, onResolved }: ConfirmationDialogProps) {
  const [busy, setBusy] = useState(false)

  async function resolve(outcome: ConfirmationOutcome) {
    if (ticket === null || busy) return
    setBusy(true)
    try {
      if (outcome === 'approved') await confirmations.approve(ticket.id)
      else await confirmations.reject(ticket.id)
      onResolved(outcome)
    } catch (error) {
      notify({
        tone: 'error',
        title: outcome === 'approved' ? 'No se pudo confirmar la acción' : 'No se pudo descartar la acción',
        body: errorMessage(error)
      })
      onResolved('rejected')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog
      open={ticket !== null}
      onOpenChange={(open) => {
        if (!open) void resolve('rejected')
      }}
    >
      <DialogContent className="rounded-[var(--radius-sheet)]">
        <DialogHeader>
          <DialogTitle>Esto necesita tu confirmación</DialogTitle>
          <DialogDescription>No se hará nada hasta que lo apruebes.</DialogDescription>
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
          <Button variant="outline" disabled={busy} onClick={() => void resolve('rejected')}>
            Cancelar
          </Button>
          <Button variant="destructive" disabled={busy} onClick={() => void resolve('approved')}>
            {busy ? 'Procesando…' : 'Confirmar'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
