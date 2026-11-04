import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/PageHeader'
import { CalendarDrawing } from './CalendarDrawing'

export function CalendarPage() {
  return (
    <>
      <PageHeader
        title="Calendario"
        summary="Eventos y bloques de tiempo, con vista diaria, semanal y mensual."
      />
      <EmptyState
        title="Aún no hay eventos"
        description="Aquí podrás crear eventos y bloques de tiempo con inicio, final y zona horaria, asociarlos a tareas, proyectos y asignaturas, y consultar tu disponibilidad."
        drawing={<CalendarDrawing />}
        pendingAction={{
          label: 'Crear evento',
          reason: 'Disponible cuando el espacio de trabajo esté conectado',
        }}
      />
    </>
  )
}
