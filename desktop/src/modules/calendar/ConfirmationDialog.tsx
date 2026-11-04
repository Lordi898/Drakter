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
import {
  approveConfirmation,
  errorText,
  rejectConfirmation,
  type ConfirmationRequired
} from './workspaceClient'

export interface ConfirmationDialogProps {
  readonly confirmation: ConfirmationRequired | null
  /** `true` si se aprobó y el backend ejecutó la acción; `false` si se rechazó. */
  readonly onResolved: (approved: boolean) => void
}

/** Paso obligatorio antes de cualquier acción destructiva: el backend solo ejecuta tras aprobar aquí. */
export function ConfirmationDialog({ confirmation, onResolved }: ConfirmationDialogProps) {
  const [busy, setBusy] = useState<'approve' | 'reject' | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function resolve(approved: boolean): Promise<void> {
    if (!confirmation) return
    setBusy(approved ? 'approve' : 'reject')
    setError(null)
    try {
      if (approved) await approveConfirmation(confirmation.confirmation_id)
      else await rejectConfirmation(confirmation.confirmation_id)
      onResolved(approved)
    } catch (caught) {
      setError(errorText(caught))
    } finally {
      setBusy(null)
    }
  }

  return (
    <Dialog
      open={confirmation !== null}
      onOpenChange={(open) => {
        if (!open && busy === null) void resolve(false)
      }}
    >
      <DialogContent showCloseButton={false} aria-describedby="confirmation-summary">
        <DialogHeader>
          <DialogTitle>Confirmar acción</DialogTitle>
          <DialogDescription id="confirmation-summary">{confirmation?.summary}</DialogDescription>
        </DialogHeader>
        {confirmation?.affected_count != null ? (
          <p className="text-sm text-muted-foreground">Elementos afectados: {confirmation.affected_count}</p>
        ) : null}
        {error ? (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        ) : null}
        <DialogFooter>
          <Button variant="outline" disabled={busy !== null} onClick={() => void resolve(false)}>
            {busy === 'reject' ? 'Rechazando…' : 'Rechazar'}
          </Button>
          <Button variant="destructive" disabled={busy !== null} onClick={() => void resolve(true)}>
            {busy === 'approve' ? 'Aprobando…' : 'Aprobar'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
