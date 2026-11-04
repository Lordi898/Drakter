import { useCallback, useState } from 'react'
import { ApiError } from '@/services/api'
import type { ApiErrorDetail } from '@/services/protocol'
import { notify } from '@/services/notify'
import type { ReviewOutcome } from '@/stores/confirmations'
import { errorMessage } from './useTasks'

export type PendingTicket = NonNullable<ApiError['confirmation']>

/**
 * Ejecuta una operación y traduce sus fallos. Devuelve `undefined` si no se llegó a completar.
 * `onInvalid` recibe los errores 422 por campo, para pintarlos junto a su campo.
 */
export type RunTask = <T>(
  action: () => Promise<T>,
  success?: string,
  onInvalid?: (details: readonly ApiErrorDetail[]) => void
) => Promise<T | undefined>

export interface TaskRunner {
  readonly run: RunTask
  readonly ticket: PendingTicket | null
  readonly resolveConfirmation: (outcome: ReviewOutcome) => void
}

/**
 * `onChanged` recarga lo que haya en pantalla: tras éxito, tras una revisión desfasada
 * y tras aprobarse una confirmación.
 */
export function useTaskRunner(onChanged: () => void): TaskRunner {
  const [ticket, setTicket] = useState<PendingTicket | null>(null)

  const run = useCallback<RunTask>(
    async (action, success, onInvalid) => {
      try {
        const result = await action()
        if (success !== undefined) notify({ tone: 'success', title: success })
        onChanged()
        return result
      } catch (error) {
        if (error instanceof ApiError && error.code === 'confirmation_required' && error.confirmation) {
          setTicket(error.confirmation)
        } else if (error instanceof ApiError && error.code === 'revision_mismatch') {
          notify({
            tone: 'warning',
            title: 'La tarea había cambiado',
            body: 'Se modificó mientras la editabas. He recargado los datos; vuelve a intentarlo.'
          })
          onChanged()
        } else if (error instanceof ApiError && error.code === 'conflict') {
          notify({
            tone: 'error',
            title: 'No se puede hacer eso',
            body: error.details[0]?.message ?? error.message
          })
        } else if (error instanceof ApiError && error.code === 'hierarchy_cycle') {
          notify({
            tone: 'error',
            title: 'Esa estructura no es posible',
            body: 'Una tarea no puede colgar de sí misma ni de una de sus subtareas, y las subtareas tienen un nivel máximo.'
          })
        } else if (error instanceof ApiError && error.status === 422 && onInvalid && error.details.length > 0) {
          onInvalid(error.details)
        } else {
          notify({ tone: 'error', title: 'No se pudo completar la operación', body: errorMessage(error) })
        }
        return undefined
      }
    },
    [onChanged]
  )

  const resolveConfirmation = useCallback(
    (outcome: ReviewOutcome) => {
      if (outcome === 'dismissed') return
      setTicket(null)
      if (outcome === 'approved') {
        notify({ tone: 'success', title: 'Acción confirmada' })
        onChanged()
      } else if (outcome === 'expired' || outcome === 'unavailable') {
        notify({
          tone: 'warning',
          title: outcome === 'expired' ? 'La confirmación ha caducado' : 'No se pudo revisar la confirmación',
          body: 'No se ha hecho ningún cambio. Vuelve a intentarlo.'
        })
      }
    },
    [onChanged]
  )

  return { run, ticket, resolveConfirmation }
}
