import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/PageHeader'
import { StorageDrawing } from './StorageDrawing'

export function StoragePage() {
  return (
    <>
      <PageHeader
        title="Almacén"
        summary="Un catálogo de tus archivos, enlaces y notas que Drakter podrá buscar y abrir cuando lo necesite."
      />
      <EmptyState
        title="Todavía no hay recursos en el almacén"
        description="Aquí catalogarás imágenes, documentos, PDF, código, enlaces y notas, con etiquetas y búsqueda por texto. Drakter abrirá solo el recurso que necesite, bajo demanda."
        drawing={<StorageDrawing />}
        pendingAction={{ label: 'Añadir archivos', reason: 'Disponible cuando el espacio de trabajo esté conectado' }}
      />
    </>
  )
}
