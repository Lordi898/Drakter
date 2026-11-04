import { CalendarOff, Pencil, Plus, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { errorText } from '@/modules/calendar/workspaceClient'
import { deleteSession, listSessions } from './api'
import { ExceptionDialog } from './ExceptionDialog'
import { FormError } from './fields'
import { hhmm, validityText, weekdayName } from './format'
import { colorOf } from './palette'
import { SessionDialog } from './SessionDialog'
import type { ClassSession, ConflictItem, Subject } from './types'
import { useDeletion } from './useDeletion'

interface Props {
  readonly subject: Subject
  readonly onEdit: () => void
  readonly onToggleArchive: () => void
  readonly onDelete: () => void
  /** Cambió algo que afecta al horario o a los contadores. */
  readonly onChanged: () => void
}

function conflictText(items: readonly ConflictItem[]): string {
  const names = items.map((c) => `${c.title} (${(c.display_start ?? c.occurrence_local_start).replace('T', ' ').slice(0, 16)})`)
  return `La clase se ha guardado, pero se solapa con: ${names.slice(0, 3).join('; ')}${names.length > 3 ? ` y ${names.length - 3} más` : ''}.`
}

export function SubjectDetail({ subject, onEdit, onToggleArchive, onDelete, onChanged }: Props) {
  const [sessions, setSessions] = useState<readonly ClassSession[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [warning, setWarning] = useState<string | null>(null)
  const [editing, setEditing] = useState<ClassSession | 'new' | null>(null)
  const [excepting, setExcepting] = useState<ClassSession | null>(null)
  const [attempt, setAttempt] = useState(0)
  const archived = subject.archived_at !== null
  const subjectId = subject.id

  const reload = useCallback(() => setAttempt((n) => n + 1), [])
  const deletion = useDeletion({
    onDeleted: () => {
      reload()
      onChanged()
    },
    conflictTitle: 'No se puede eliminar la clase'
  })

  useEffect(() => {
    let cancelled = false
    setError(null)
    listSessions(subjectId).then(
      (page) => {
        if (!cancelled) setSessions(page.items)
      },
      (e: unknown) => {
        if (!cancelled) setError(errorText(e))
      }
    )
    return () => {
      cancelled = true
    }
  }, [subjectId, attempt, subject.revision])

  const sorted = [...(sessions ?? [])].sort(
    (a, b) => a.weekday - b.weekday || a.starts_local_time.localeCompare(b.starts_local_time)
  )

  return (
    <section aria-label={`Detalle de ${subject.name}`} className="grid content-start gap-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="mt-1.5 size-4 shrink-0 rounded-sm" style={{ backgroundColor: colorOf(subject.color) }} aria-hidden="true" />
          <div>
            <h2 className="flex items-center gap-2 text-2xl font-semibold text-foreground">
              {subject.name}
              {archived ? <Badge variant="outline">Archivada</Badge> : null}
            </h2>
            <p className="text-sm text-muted-foreground">{subject.teacher ? `Profesor/a: ${subject.teacher}` : 'Sin profesor asignado'}</p>
            {subject.description ? <p className="mt-2 max-w-[60ch] text-sm text-foreground">{subject.description}</p> : null}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={onEdit}>
            <Pencil /> Editar
          </Button>
          <Button variant="outline" size="sm" onClick={onToggleArchive}>
            {archived ? 'Desarchivar' : 'Archivar'}
          </Button>
          <Button variant="outline" size="sm" onClick={onDelete}>
            <Trash2 /> Eliminar
          </Button>
        </div>
      </div>

      <div className="grid gap-3">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-lg font-semibold text-foreground">Clases semanales</h3>
          <Button size="sm" onClick={() => setEditing('new')} disabled={archived}>
            <Plus /> Añadir clase
          </Button>
        </div>
        <p className="text-sm text-muted-foreground">
          Las clases aparecen en el calendario por proyección: no se crean eventos ni se duplican datos.
        </p>
        {warning ? (
          <p role="status" className="rounded-md border border-warning/60 px-3 py-2 text-sm text-foreground">
            {warning}
          </p>
        ) : null}
        <FormError message={error} />
        {deletion.failure}
        {error ? (
          <div>
            <Button size="sm" variant="outline" onClick={reload}>
              Reintentar
            </Button>
          </div>
        ) : null}
        {sessions && sorted.length === 0 ? (
          <p className="text-sm text-muted-foreground">Esta asignatura aún no tiene clases. Añade la primera con el botón de arriba.</p>
        ) : null}
        <ul className="grid gap-2">
          {sorted.map((s) => (
            <li key={s.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-card px-4 py-3">
              <div className="text-sm">
                <p className="font-medium text-foreground">
                  {weekdayName(s.weekday)}, {hhmm(s.starts_local_time)}–{hhmm(s.ends_local_time)}
                  {s.room ? ` · Aula ${s.room}` : ''}
                </p>
                <p className="text-muted-foreground">
                  {validityText(s.valid_from, s.valid_until)} · {s.timezone}
                </p>
              </div>
              <div className="flex gap-1">
                <Button variant="ghost" size="sm" onClick={() => setEditing(s)} aria-label={`Editar la clase del ${weekdayName(s.weekday).toLowerCase()}`}>
                  <Pencil /> Editar
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setExcepting(s)} aria-label={`Cancelar o cambiar una clase del ${weekdayName(s.weekday).toLowerCase()}`}>
                  <CalendarOff /> Excepción
                </Button>
                <Button variant="ghost" size="sm" onClick={() => void deletion.start(() => deleteSession(s.id))} aria-label={`Eliminar la clase del ${weekdayName(s.weekday).toLowerCase()}`}>
                  <Trash2 /> Eliminar
                </Button>
              </div>
            </li>
          ))}
        </ul>
      </div>

      <SessionDialog
        open={editing !== null}
        subjectId={subjectId}
        session={editing === 'new' ? null : editing}
        onClose={() => setEditing(null)}
        onSaved={(conflicts) => {
          setEditing(null)
          setWarning(conflicts.length > 0 ? conflictText(conflicts) : null)
          reload()
          onChanged()
        }}
      />
      <ExceptionDialog
        session={excepting}
        onClose={() => setExcepting(null)}
        onSaved={() => {
          setExcepting(null)
          setWarning(null)
          onChanged()
        }}
      />
      {deletion.element}
    </section>
  )
}
