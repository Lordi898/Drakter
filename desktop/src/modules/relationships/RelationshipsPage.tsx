import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/PageHeader'
import { RelationshipsDrawing } from './RelationshipsDrawing'

export function RelationshipsPage() {
  return (
    <>
      <PageHeader
        title="Relaciones"
        summary="Los vínculos entre tareas, proyectos, asignaturas, documentos y otros elementos del espacio de trabajo."
      />
      <EmptyState
        title="Aún no hay relaciones"
        description="Aparecerán cuando vincules elementos del espacio de trabajo, por ejemplo una tarea con su proyecto o un documento con una asignatura. Cada vínculo tendrá un tipo, como pertenece a, depende de o hace referencia a."
        drawing={<RelationshipsDrawing />}
      />
    </>
  )
}
