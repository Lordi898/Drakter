import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/PageHeader'
import { TasksDrawing } from './TasksDrawing'

export function TasksPage() {
  return (
    <>
      <PageHeader
        title="Tareas"
        summary="Aquí vivirán tus tareas, con subtareas anidadas, prioridad y fechas."
      />
      <EmptyState
        title="Todavía no hay tareas"
        description="Podrás crear, completar y reabrir tareas, anidar subtareas y vincularlas a proyectos y asignaturas. Esta página mostrará esa lista cuando exista."
        drawing={<TasksDrawing />}
        pendingAction={{
          label: 'Crear tarea',
          reason: 'Disponible cuando el espacio de trabajo esté conectado',
        }}
      />
    </>
  )
}
