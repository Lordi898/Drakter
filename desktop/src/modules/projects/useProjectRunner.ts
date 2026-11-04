import { useCallback, useState } from 'react'
import { notify } from '@/services/notify'
import { ApiError, ConfirmationNeeded, type ConfirmationTicket } from '../tasks/client'
import type { ConfirmationOutcome } from '../tasks/ConfirmationDialog'
import { toLoadError } from './useLoad'

export type RunProject = <T>(action: () => Promise<T>, success?: string) => Promise<boolean>

export interface ProjectRunner {
  readonly run: RunProject
  readonly ticket: ConfirmationTicket | null
  readonly resolveConfirmation: (outcome: ConfirmationOutcome) => void
}

/** Ejecuta una operación y traduce sus fallos. Devuelve `true` solo si se completó. */
export function useProjectRunner(onChanged: () => void): ProjectRunner {
  const [ticket, setTicket] = useState<ConfirmationTicket | null>(null)

  const run = useCallback<RunProject>(
    async (action, success) => {
      try {
        await action()
        if (success !== undefined) notify({ tone: 'success', title: success })
        onChanged()
        return true
      } catch (error) {
        if (error instanceof ConfirmationNeeded) {
          setTicket(error.ticket)
        } else if (error instanceof ApiError && error.code === 'revision_mismatch') {
          notify({
            tone: 'warning',
            title: 'El proyecto había cambiado',
            body: 'Se modificó mientras lo tenías abierto. He recargado los datos; vuelve a intentarlo.'
          })
          onChanged()
        } else if (error instanceof ApiError && error.code === 'conflict') {
          notify({ tone: 'error', title: 'No se puede hacer eso', body: error.message })
        } else {
          notify({ tone: 'error', title: 'No se pudo completar la operación', body: toLoadError(error).message })
        }
        return false
      }
    },
    [onChanged]
  )

  const resolveConfirmation = useCallback(
    (outcome: ConfirmationOutcome) => {
      setTicket(null)
      if (outcome === 'approved') notify({ tone: 'success', title: 'Acción confirmada' })
      onChanged()
    },
    [onChanged]
  )

  return { run, ticket, resolveConfirmation }
}
