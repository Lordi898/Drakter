import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/PageHeader'
import { HabitsDrawing } from './HabitsDrawing'

export function HabitsPage() {
  return (
    <>
      <PageHeader
        title="Hábitos"
        summary="Rutinas con su frecuencia, sus días activos y el registro de cada cumplimiento."
      />
      <EmptyState
        title="Aún no hay hábitos"
        description="Aquí podrás crear hábitos, definir cada cuánto se repiten, registrar si los cumpliste y consultar su historial. El historial se conserva aunque cambies un hábito."
        drawing={<HabitsDrawing />}
        pendingAction={{
          label: 'Crear hábito',
          reason: 'Disponible cuando el espacio de trabajo esté conectado',
        }}
      />
    </>
  )
}
