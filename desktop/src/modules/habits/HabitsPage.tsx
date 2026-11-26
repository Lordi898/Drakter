import { useState } from 'react'
import { Plus } from 'lucide-react'
import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { errorText } from '@/modules/calendar/workspaceApi'
import { registerRecord } from './api'
import { BackendState } from './BackendState'
import { todayIn } from './dates'
import { HabitDetail } from './HabitDetail'
import { HabitDialog } from './HabitDialog'
import { HabitRow } from './HabitRow'
import { HabitsDrawing } from './HabitsDrawing'
import type { Habit, RecordStatus } from './types'
import { useHabits } from './useHabits'

type DialogState = { readonly habit: Habit | null } | null

export function HabitsPage() {
  const [showArchived, setShowArchived] = useState(false)
  const { habits, error, reload: load } = useHabits(showArchived)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [dialog, setDialog] = useState<DialogState>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [markError, setMarkError] = useState<string | null>(null)

  async function mark(habit: Habit, status: RecordStatus) {
    setBusyId(habit.id)
    setMarkError(null)
    try {
      await registerRecord(habit.id, todayIn(habit.timezone), status)
      load()
    } catch (e) {
      setMarkError(errorText(e))
    } finally {
      setBusyId(null)
    }
  }

  const selected = habits?.find((h) => h.id === selectedId) ?? null
  const createButton = (
    <Button type="button" onClick={() => setDialog({ habit: null })}>
      <Plus aria-hidden="true" /> Crear hábito
    </Button>
  )

  const dialogEl = dialog ? (
    <HabitDialog
      key={dialog.habit?.id ?? 'new'}
      habit={dialog.habit}
      open
      onClose={() => setDialog(null)}
      onSaved={(saved) => {
        setDialog(null)
        if (!dialog.habit) setSelectedId(null)
        load()
        if (dialog.habit) setSelectedId(saved.id)
      }}
    />
  ) : null

  if (error) {
    return (
      <>
        <PageHeader title="Hábitos" summary="Rutinas con su frecuencia, sus días activos y el registro de cada cumplimiento." />
        <BackendState error={error} onRetry={load} />
      </>
    )
  }

  if (selected) {
    return (
      <>
        <PageHeader title="Hábitos" summary="Detalle, historial y estadísticas del hábito." />
        <HabitDetail
          key={selected.id}
          habit={selected}
          onBack={() => setSelectedId(null)}
          onEdit={(h) => setDialog({ habit: h })}
          onChanged={() => load()}
        />
        {dialogEl}
      </>
    )
  }

  return (
    <>
      <PageHeader
        title="Hábitos"
        summary="Rutinas con su frecuencia, sus días activos y el registro de cada cumplimiento."
        actions={
          <>
            <div className="flex items-center gap-2">
              <Switch id="habits-archived" checked={showArchived} onCheckedChange={setShowArchived} />
              <Label htmlFor="habits-archived">Ver archivados</Label>
            </div>
            {createButton}
          </>
        }
      />
      {habits === null ? (
        <p className="text-muted-foreground" role="status">
          Cargando hábitos…
        </p>
      ) : habits.length === 0 ? (
        <>
          <EmptyState
            title={showArchived ? 'No hay hábitos' : 'Aún no hay hábitos'}
            description="Crea un hábito, define cada cuánto se repite, registra si lo cumpliste y consulta su historial. Los registros se conservan aunque cambies la frecuencia."
            drawing={<HabitsDrawing />}
          />
        </>
      ) : (
        <>
          {markError ? (
            <p role="alert" className="mb-3 text-sm text-destructive">
              {markError}
            </p>
          ) : null}
          <ul className="flex max-w-4xl flex-col gap-2" aria-label="Hábitos">
            {habits.map((h) => (
              <HabitRow key={h.id} habit={h} busy={busyId === h.id} onOpen={(x) => setSelectedId(x.id)} onMark={(x, s) => void mark(x, s)} />
            ))}
          </ul>
        </>
      )}
      {dialogEl}
    </>
  )
}
