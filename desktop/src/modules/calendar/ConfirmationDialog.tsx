import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { reviewConfirmation, type ConfirmationTicket, type TrustedGesture } from './workspaceApi'

export interface ConfirmationDialogProps {
  readonly confirmation: ConfirmationTicket | null
  /** `true` si se aprobó (main ejecutó la acción); `false` en cualquier otro caso. */
  readonly onResolved: (approved: boolean) => void
}

/** Paso obligatorio antes de borrar: la aprobación la decide el diálogo nativo de main, no este componente. */
export function ConfirmationDialog({ confirmation, onResolved }: ConfirmationDialogProps) {
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  async function review(proof: TrustedGesture): Promise<void> {
    if (!confirmation) return
    setBusy(true)
    setMessage(null)
    try {
      const outcome = await reviewConfirmation(confirmation.id, proof)
      if (outcome === 'approved') onResolved(true)
      else if (outcome === 'rejected') onResolved(false)
      else if (outcome === 'expired') setMessage('La confirmación ha caducado. Inténtalo de nuevo.')
      else if (outcome === 'conflict') setMessage('El elemento ha cambiado; no se ha borrado. Recarga y vuelve a intentarlo.')
      else if (outcome === 'failed') setMessage('No se pudo completar. Comprueba si el elemento sigue ahí antes de repetir.')
      else setMessage('Las confirmaciones aún no están disponibles; no se ha borrado nada.')
    } catch {
      setMessage('No se pudo revisar la confirmación; no se ha borrado nada.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog
      open={confirmation !== null}
      onOpenChange={(open) => {
        if (!open) {
          setMessage(null)
          onResolved(false)
        }
      }}
    >
      <DialogContent aria-describedby="confirmation-summary">
        <DialogHeader>
          <DialogTitle>Confirmar acción</DialogTitle>
          <DialogDescription id="confirmation-summary">{confirmation?.summary}</DialogDescription>
        </DialogHeader>
        {confirmation?.affected_count != null ? (
          <p className="text-sm text-muted-foreground">Elementos afectados: {confirmation.affected_count}</p>
        ) : null}
        {message ? (
          <p role="alert" className="text-sm text-destructive">
            {message}
          </p>
        ) : null}
        <DialogFooter>
          <Button variant="outline" disabled={busy} onClick={() => onResolved(false)}>
            Cerrar
          </Button>
          <Button disabled={busy} onClick={(event) => void review(event)}>
            {busy ? 'Revisando…' : 'Revisar'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
