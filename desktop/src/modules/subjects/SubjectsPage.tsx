import { CalendarDays, List, Plus } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/utils'
import { BackendUnavailableError, errorText } from '@/modules/calendar/workspaceClient'
import { archiveSubject, deleteSubject, listSubjects, unarchiveSubject } from './api'
import { colorOf } from './palette'
import { SubjectDetail } from './SubjectDetail'
import { SubjectDialog } from './SubjectDialog'
import { SubjectsDrawing } from './SubjectsDrawing'
import type { Subject } from './types'
import { useDeletion } from './useDeletion'
import { WeeklyTimetable } from './WeeklyTimetable'

type View = 'list' | 'timetable'
type Load =
  | { readonly status: 'loading' }
  | { readonly status: 'error'; readonly error: unknown }
  | { readonly status: 'ready'; readonly subjects: readonly Subject[] }

export function SubjectsPage() {
  const [load, setLoad] = useState<Load>({ status: 'loading' })
  const [includeArchived, setIncludeArchived] = useState(false)
  const [view, setView] = useState<View>('list')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [dialog, setDialog] = useState<Subject | 'new' | null>(null)
  const [attempt, setAttempt] = useState(0)
  const [reloadKey, setReloadKey] = useState(0)
  const [actionError, setActionError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    listSubjects(includeArchived).then(
      (page) => {
        if (!cancelled) setLoad({ status: 'ready', subjects: page.items })
      },
      (error: unknown) => {
        if (!cancelled) setLoad({ status: 'error', error })
      }
    )
    return () => {
      cancelled = true
    }
  }, [includeArchived, attempt])

  const refresh = useCallback(() => {
    setAttempt((n) => n + 1)
    setReloadKey((n) => n + 1)
  }, [])

  const subjects = load.status === 'ready' ? load.subjects : []
  const selected = subjects.find((s) => s.id === selectedId) ?? subjects[0] ?? null

  async function toggleArchive(subject: Subject) {
    setActionError(null)
    try {
      await (subject.archived_at ? unarchiveSubject(subject.id) : archiveSubject(subject.id))
      refresh()
    } catch (e) {
      setActionError(errorText(e))
    }
  }

  const [pendingDelete, setPendingDelete] = useState<Subject | null>(null)
  const deletion = useDeletion({
    onDeleted: () => {
      setSelectedId(null)
      refresh()
    },
    onArchive: async () => {
      if (pendingDelete) await archiveSubject(pendingDelete.id)
      refresh()
    },
    conflictTitle: 'No se puede eliminar la asignatura'
  })

  function openSubject(id: string) {
    setSelectedId(id)
    setView('list')
  }

  const headerActions = (
    <Button onClick={() => setDialog('new')} disabled={load.status === 'error'}>
      <Plus /> Nueva asignatura
    </Button>
  )

  if (load.status === 'error') {
    const unavailable = load.error instanceof BackendUnavailableError
    return (
      <>
        <PageHeader title="Asignaturas" summary="Tus asignaturas con su horario, su aula y sus clases." />
        <EmptyState
          title={unavailable ? 'Espacio de trabajo sin conexión' : 'No se pudieron cargar las asignaturas'}
          description={unavailable ? 'Las asignaturas se guardan en el espacio de trabajo, que todavía no está conectado. No se muestra nada hasta que lo esté.' : errorText(load.error)}
          drawing={<SubjectsDrawing />}
        />
        <Button className="mt-4" variant="outline" onClick={() => setAttempt((n) => n + 1)}>
          Reintentar
        </Button>
      </>
    )
  }

  const empty = load.status === 'ready' && subjects.length === 0

  return (
    <>
      <PageHeader
        title="Asignaturas"
        summary="Tus asignaturas con su horario, su aula y sus clases semanales."
        actions={headerActions}
      />
      {load.status === 'loading' ? <p className="text-muted-foreground">Cargando asignaturas…</p> : null}
      {empty && !includeArchived ? (
        <EmptyState
          title="Todavía no hay asignaturas"
          description="Crea la primera con su color y su profesor; después añade sus clases semanales y verás el horario aquí."
          drawing={<SubjectsDrawing />}
        />
      ) : null}
      {load.status === 'ready' && (!empty || includeArchived) ? (
        <div className="grid gap-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div role="tablist" aria-label="Vista" className="inline-flex rounded-md border border-border p-0.5">
              {([
                ['list', 'Asignaturas', List],
                ['timetable', 'Horario semanal', CalendarDays]
              ] as const).map(([value, label, Icon]) => (
                <button
                  key={value}
                  type="button"
                  role="tab"
                  aria-selected={view === value}
                  onClick={() => setView(value)}
                  className={cn(
                    'inline-flex items-center gap-2 rounded-sm px-3 py-1.5 text-sm outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50',
                    view === value ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'
                  )}
                >
                  <Icon className="size-4" aria-hidden="true" /> {label}
                </button>
              ))}
            </div>
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <Switch checked={includeArchived} onCheckedChange={setIncludeArchived} aria-label="Mostrar archivadas" />
              Mostrar archivadas
            </label>
          </div>
          {actionError ? (
            <p role="alert" className="text-sm text-destructive">
              {actionError}
            </p>
          ) : null}
          {deletion.failure}

          {view === 'timetable' ? (
            <WeeklyTimetable reloadKey={reloadKey} onOpenSubject={openSubject} />
          ) : (
            <div className="grid items-start gap-6 lg:grid-cols-[18rem_minmax(0,1fr)]">
              <ul aria-label="Asignaturas" className="grid gap-1">
                {subjects.map((s) => {
                  const active = s.id === selected?.id
                  return (
                    <li key={s.id}>
                      <button
                        type="button"
                        aria-current={active ? 'true' : undefined}
                        onClick={() => setSelectedId(s.id)}
                        className={cn(
                          'flex w-full items-center gap-3 rounded-md border px-3 py-2 text-left outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50',
                          active ? 'border-primary bg-accent' : 'border-border bg-card hover:bg-accent/60'
                        )}
                      >
                        <span className="size-3.5 shrink-0 rounded-sm" style={{ backgroundColor: colorOf(s.color) }} aria-hidden="true" />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-medium text-foreground">{s.name}</span>
                          <span className="block truncate text-xs text-muted-foreground">
                            {s.teacher ?? 'Sin profesor'} · {s.session_count} {s.session_count === 1 ? 'clase' : 'clases'}
                          </span>
                        </span>
                        {s.archived_at ? <Badge variant="outline">Archivada</Badge> : null}
                      </button>
                    </li>
                  )
                })}
              </ul>
              {selected ? (
                <SubjectDetail
                  key={selected.id}
                  subject={selected}
                  onEdit={() => setDialog(selected)}
                  onToggleArchive={() => void toggleArchive(selected)}
                  onDelete={() => {
                    setPendingDelete(selected)
                    void deletion.start(() => deleteSubject(selected.id))
                  }}
                  onChanged={refresh}
                />
              ) : (
                <p className="text-sm text-muted-foreground">No hay asignaturas archivadas.</p>
              )}
            </div>
          )}
        </div>
      ) : null}

      <SubjectDialog
        open={dialog !== null}
        subject={dialog === 'new' ? null : dialog}
        onClose={() => setDialog(null)}
        onSaved={(saved) => {
          setDialog(null)
          setSelectedId(saved.id)
          refresh()
        }}
      />
      {deletion.element}
    </>
  )
}
