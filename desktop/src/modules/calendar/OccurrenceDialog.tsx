import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { cancelOccurrence, requestEventDeletion, requestTimeBlockDeletion } from './api'
import { dateTimeLabel, shortDayLabel, systemTimeZone } from './dateUtils'
import { describeFailure } from './formUtils'
import { KIND_STYLES, STATUS_LABELS } from './kinds'
import { describeRrule } from './recurrence'
import { normalizeKind, type AgendaItem } from './types'
import type { ConfirmationTicket } from './workspaceApi'

export interface OccurrenceDialogProps {
  readonly item: AgendaItem | null
  readonly overlapping: boolean
  readonly onClose: () => void
  readonly onEdit: (item: AgendaItem) => void
  /** Se canceló una ocurrencia: hay que recargar la agenda. */
  readonly onChanged: () => void
  readonly onConfirmationRequired: (confirmation: ConfirmationTicket) => void
}

function whenText(item: AgendaItem): string {
  if (item.all_day && item.start_date) {
    const last = item.end_date_exclusive ?? item.start_date
    return `${shortDayLabel(item.start_date)} (todo el día${last > item.start_date ? ', varios días' : ''})`
  }
  if (item.display_start && item.display_end) return `${dateTimeLabel(item.display_start)} – ${dateTimeLabel(item.display_end)}`
  return '—'
}

export function OccurrenceDialog({ item, overlapping, onClose, onEdit, onChanged, onConfirmationRequired }: OccurrenceDialogProps) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  if (!item) return null
  const kind = normalizeKind(item.kind)
  const isClass = item.source_type === 'class_session'
  const isEvent = item.source_type === 'calendar_event'

  async function run(action: () => Promise<void>): Promise<void> {
    if (!item) return
    setBusy(true)
    setError(null)
    try {
      await action()
    } catch (caught) {
      setError(describeFailure(caught, item.timezone).message)
    } finally {
      setBusy(false)
    }
  }

  const askDeletion = (): Promise<void> =>
    run(async () => {
      if (!item) return
      const confirmation = await (isEvent ? requestEventDeletion(item.source_id) : requestTimeBlockDeletion(item.source_id))
      onClose()
      onConfirmationRequired(confirmation)
    })

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{item.title}</DialogTitle>
          <DialogDescription>
            {KIND_STYLES[kind].label} · {STATUS_LABELS[item.status] ?? item.status}
          </DialogDescription>
        </DialogHeader>
        <dl className="grid grid-cols-[6rem_1fr] gap-x-3 gap-y-2 text-sm">
          <dt className="text-muted-foreground">Cuándo</dt>
          <dd>{whenText(item)}</dd>
          {item.timezone !== systemTimeZone() ? (
            <>
              <dt className="text-muted-foreground">Zona horaria</dt>
              <dd>{item.timezone}</dd>
            </>
          ) : null}
          {item.location ? (
            <>
              <dt className="text-muted-foreground">Lugar</dt>
              <dd>{item.location}</dd>
            </>
          ) : null}
          {item.recurring ? (
            <>
              <dt className="text-muted-foreground">Repetición</dt>
              <dd>Forma parte de una serie{item.modified ? ' (esta ocurrencia está modificada)' : ''}</dd>
            </>
          ) : null}
          {item.room ? (
            <>
              <dt className="text-muted-foreground">Aula</dt>
              <dd>{item.room}</dd>
            </>
          ) : null}
          {item.task_id ? (
            <>
              <dt className="text-muted-foreground">Tarea</dt>
              <dd className="break-all font-mono text-xs">{item.task_id}</dd>
            </>
          ) : null}
          {item.description ? (
            <>
              <dt className="text-muted-foreground">Notas</dt>
              <dd className="whitespace-pre-wrap">{item.description}</dd>
            </>
          ) : null}
        </dl>
        {overlapping ? (
          <p role="status" className="rounded-md border border-warning/60 bg-warning/10 px-3 py-2 text-sm">
            Se solapa con otro elemento de tu agenda.
          </p>
        ) : null}
        {isClass ? (
          <p className="text-sm text-muted-foreground">Las clases se gestionan desde Asignaturas; aquí son de solo lectura.</p>
        ) : null}
        {error ? <p role="alert" className="text-sm text-destructive">{error}</p> : null}
        {isClass ? (
          <DialogFooter>
            <Button variant="outline" onClick={onClose}>Cerrar</Button>
          </DialogFooter>
        ) : (
          <DialogFooter className="gap-2 sm:justify-between">
            <div className="flex flex-wrap gap-2">
              {isEvent && item.recurring ? (
                <Button
                  variant="outline"
                  disabled={busy}
                  onClick={() =>
                    void run(async () => {
                      await cancelOccurrence(item.source_id, item.occurrence_local_start)
                      onClose()
                      onChanged()
                    })
                  }
                >
                  Cancelar solo esta ocurrencia
                </Button>
              ) : null}
              <Button variant="destructive" disabled={busy} onClick={() => void askDeletion()}>
                {isEvent && item.recurring ? 'Borrar toda la serie' : 'Borrar'}
              </Button>
            </div>
            <Button disabled={busy} onClick={() => onEdit(item)}>
              {item.recurring ? 'Editar serie' : 'Editar'}
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  )
}
