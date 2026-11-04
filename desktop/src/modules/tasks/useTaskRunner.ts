import { useCallback, useState } from 'react'
import { notify } from '@/services/notify'
import { ApiError, ConfirmationNeeded, type ConfirmationTicket } from './client'
import type { ConfirmationOutcome } from './ConfirmationDialog'
import { errorMessage } from './useTasks'

/** Ejecuta una operación y traduce sus fallos. Devuelve `undefined` si no se llegó a completar. */
export type RunTask = <T>(action: () => Promise<T>, success?: string) => Promise<T | undefined>

export interface TaskRunner {
  readonly run: RunTask
  readonly ticket: ConfirmationTicket | null
  readonly resolveConfirmation: (outcome: ConfirmationOutcome) => void
}

/**
 * `onChanged` recarga lo que haya en pantalla: tras éxito, tras una revisión desfasada
 * y tras resolver una confirmación.
 */
export function useTaskRunner(onChanged: () => void): TaskRunner {
  const [ticket, setTicket] = useState<ConfirmationTicket | null>(null)

  const run = useCallback<RunTask>(
    async (action, success) => {
      try {
        const result = await action()
        if (success !== undefined) notify({ tone: 'success', title: success })
        onChanged()
        return result
      } catch (error) {
        if (error instanceof ConfirmationNeeded) {
          setTicket(error.ticket)
        } else if (error instanceof ApiError && error.code === 'revision_mismatch') {
          notify({
            tone: 'warning',
            title: 'La tarea había cambiado',
            body: 'Alguien la modificó mientras la editabas. He recargado los datos; vuelve a intentarlo.'
          })
          onChanged()
        } else if (error instanceof ApiError && error.code === 'conflict') {
          notify({ tone: 'error', title: 'No se puede hacer eso', body: error.message })
        } else {
          notify({ tone: 'error', title: 'No se pudo completar la operación', body: errorMessage(error) })
        }
        return undefined
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
