import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/PageHeader'
import { SubjectsDrawing } from './SubjectsDrawing'

export function SubjectsPage() {
  return (
    <>
      <PageHeader
        title="Asignaturas"
        summary="Aquí tendrás tus asignaturas con su horario, su aula y los apuntes, tareas y proyectos que dependan de ellas."
      />
      <EmptyState
        title="Todavía no hay asignaturas"
        description="Cada asignatura tendrá sus sesiones de clase, incluidas las recurrentes, y reunirá los recursos relacionados. Cuando el espacio de trabajo esté conectado, podrás crearlas y consultarlas aquí."
        drawing={<SubjectsDrawing />}
        pendingAction={{ label: 'Crear asignatura', reason: 'Disponible cuando el espacio de trabajo esté conectado' }}
      />
    </>
  )
}
