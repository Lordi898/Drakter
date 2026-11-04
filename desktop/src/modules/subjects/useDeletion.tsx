import { useState, type ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { ConfirmationDialog } from '@/modules/calendar/ConfirmationDialog'
import {
  ApiError,
  confirmationOf,
  errorText,
  type ConfirmationTicket
} from '@/modules/calendar/workspaceApi'
import type { DeleteResult } from './api'
import { FormError } from './fields'

interface Options {
  /** Se llama tras aprobar o ejecutar el borrado. */
  readonly onDeleted: () => void
  /** Si el backend rechaza por vínculos (`conflict`), permite ofrecer archivar. */
  readonly onArchive?: () => Promise<void>
  readonly conflictTitle?: string
}

/**
 * Flujo de borrado: DELETE -> 409 confirmation_required -> ConfirmationDialog.
 * `element` debe renderizarse una vez; `start(fn)` ejecuta la llamada DELETE.
 */
export function useDeletion({ onDeleted, onArchive, conflictTitle = 'No se puede eliminar' }: Options) {
  const [confirmation, setConfirmation] = useState<ConfirmationTicket | null>(null)
  const [conflict, setConflict] = useState<string | null>(null)
  const [failure, setFailure] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function start(call: () => Promise<DeleteResult>) {
    setFailure(null)
    try {
      await call()
      onDeleted()
    } catch (e) {
      const ticket = confirmationOf(e)
      if (ticket) setConfirmation(ticket)
      else if (e instanceof ApiError && e.code === 'has_dependents') setConflict(errorText(e))
      else setFailure(errorText(e))
    }
  }

  async function archiveInstead() {
    if (!onArchive) return
    setBusy(true)
    try {
      await onArchive()
      setConflict(null)
    } catch (e) {
      setFailure(errorText(e))
      setConflict(null)
    } finally {
      setBusy(false)
    }
  }

  const element: ReactNode = (
    <>
      <ConfirmationDialog
        confirmation={confirmation}
        onResolved={(approved) => {
          setConfirmation(null)
          if (approved) onDeleted()
        }}
      />
      <Dialog open={conflict !== null} onOpenChange={(open) => (open ? undefined : setConflict(null))}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{conflictTitle}</DialogTitle>
            <DialogDescription>{conflict}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConflict(null)} disabled={busy}>
              Cerrar
            </Button>
            {onArchive ? (
              <Button onClick={() => void archiveInstead()} disabled={busy}>
                {busy ? 'Archivando…' : 'Archivar en su lugar'}
              </Button>
            ) : null}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )

  return { start, element, failure: <FormError message={failure} /> }
}
