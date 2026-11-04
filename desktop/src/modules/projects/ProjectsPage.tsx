import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/PageHeader'
import { ProjectsDrawing } from './ProjectsDrawing'

export function ProjectsPage() {
  return (
    <div>
      <PageHeader
        title="Proyectos"
        summary="Aquí verás tus proyectos con su estado, fechas y progreso."
      />
      <EmptyState
        title="Todavía no hay proyectos"
        description="Cada proyecto tendrá objetivos, fechas y prioridad, y reunirá sus tareas, recursos y asignaturas para que consultes su progreso, sus dependencias y su actividad."
        drawing={<ProjectsDrawing />}
        pendingAction={{
          label: 'Crear proyecto',
          reason: 'Disponible cuando el espacio de trabajo esté conectado',
        }}
      />
    </div>
  )
}
