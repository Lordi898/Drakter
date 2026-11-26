import { FileText, Link as LinkIcon, NotebookPen } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { AVAILABILITY_LABELS, TYPE_LABELS, type ResourceSummary } from './types'
import { useResources, type Filters } from './useStorage'

interface Props {
  readonly filters: Filters
  readonly reloadKey: number
  readonly selectedId: string | null
  readonly onSelect: (id: string) => void
}

export function ResourceList({ filters, reloadKey, selectedId, onSelect }: Props) {
  const { rows, hasMore, loading, failed, searching, loadMore, retry } = useResources(filters, reloadKey)

  if (loading && rows.length === 0) {
    return <p role="status" className="p-4 text-sm text-muted-foreground">Cargando recursos…</p>
  }
  if (failed && rows.length === 0) {
    return (
      <div className="flex flex-col items-start gap-2 p-4 text-sm">
        <p className="text-muted-foreground">No se han podido cargar los recursos.</p>
        <Button size="sm" variant="outline" onClick={retry}>Reintentar</Button>
      </div>
    )
  }
  if (rows.length === 0) {
    return (
      <p className="p-4 text-sm text-muted-foreground">
        {searching ? 'Ninguna coincidencia. Prueba con otras palabras o quita los filtros.' : 'No hay recursos aquí con estos filtros.'}
      </p>
    )
  }

  return (
    <div className="flex flex-col gap-2">
      <ul aria-label="Recursos" className="flex flex-col gap-1">
        {rows.map(({ resource, snippet }) => (
          <li key={resource.id}>
            <button
              type="button"
              onClick={() => onSelect(resource.id)}
              aria-current={selectedId === resource.id ? 'true' : undefined}
              className={cn(
                'flex w-full items-start gap-3 rounded-md border border-transparent px-3 py-2 text-left outline-none transition-colors hover:bg-accent focus-visible:ring-[3px] focus-visible:ring-ring/50',
                selectedId === resource.id && 'border-border bg-accent'
              )}
            >
              <TypeIcon type={resource.resource_type} />
              <span className="min-w-0 flex-1">
                <span className="block truncate font-medium">{resource.title}</span>
                {snippet ? <span className="block truncate text-xs text-muted-foreground">{snippet}</span> : null}
                <span className="mt-1 flex flex-wrap items-center gap-1.5">
                  <Badge variant="secondary">{TYPE_LABELS[resource.resource_type]}</Badge>
                  {resource.availability_status !== 'available' ? (
                    <Badge variant="outline">{AVAILABILITY_LABELS[resource.availability_status]}</Badge>
                  ) : null}
                  {resource.tags.map((tag) => (
                    <span key={tag} className="text-xs text-muted-foreground">#{tag}</span>
                  ))}
                </span>
              </span>
            </button>
          </li>
        ))}
      </ul>
      {hasMore ? (
        <Button variant="outline" size="sm" disabled={loading} onClick={loadMore} className="self-center">
          {loading ? 'Cargando…' : 'Cargar más'}
        </Button>
      ) : null}
    </div>
  )
}

function TypeIcon({ type }: { type: ResourceSummary['resource_type'] }) {
  const Icon = type === 'link' ? LinkIcon : type === 'note' || type === 'study_note' ? NotebookPen : FileText
  return <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
}
