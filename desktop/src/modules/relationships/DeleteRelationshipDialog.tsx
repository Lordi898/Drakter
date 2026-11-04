import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle
} from '@/components/ui/dialog'
import { notify } from '@/services/notify'
import { BackendError } from '@/modules/storage/backend'
import { deleteRelationship, humanError } from './api'

export interface DeleteRelationshipDialogProps {
  /** `null` cierra el diálogo. */
  readonly relationshipId: string | null
  /** Descripción legible de la relación, en texto plano. */
  readonly summary: string
  readonly onClose: () => void
  readonly onDeleted: () => void
}

export function DeleteRelationshipDialog({ relationshipId, summary, onClose, onDeleted }: DeleteRelationshipDialogProps) {
  const [busy, setBusy] = useState(false)
  const [waiting, setWaiting] = useState(false)

  const close = () => {
    setWaiting(false)
    onClose()
  }

  const confirm = async () => {
    if (relationshipId === null) return
    setBusy(true)
    try {
      await deleteRelationship(relationshipId)
      notify({ tone: 'success', title: 'Relación eliminada' })
      close()
      onDeleted()
    } catch (error) {
      if (error instanceof BackendError && error.code === 'confirmation_required') {
        setWaiting(true)
      } else {
        notify({ tone: 'error', title: 'No se ha podido eliminar la relación', body: humanError(error) })
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={relationshipId !== null} onOpenChange={(open) => { if (!open) close() }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Eliminar relación</DialogTitle>
          <DialogDescription>
            Vas a eliminar el vínculo «{summary}». Los dos elementos se conservan; solo desaparece la relación.
          </DialogDescription>
        </DialogHeader>
        {waiting ? (
          <p role="status" className="text-sm text-warning">
            La eliminación espera tu aprobación. Aprúebala en el panel de confirmaciones y vuelve a intentarlo.
          </p>
        ) : null}
        <DialogFooter>
          <Button variant="outline" onClick={close}>Cancelar</Button>
          <Button variant="destructive" disabled={busy} onClick={() => void confirm()}>
            {waiting ? 'Reintentar' : 'Eliminar'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
