import { useState } from 'react'
import { Trash2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { isDisconnected } from './api'
import { DeleteRelationshipDialog } from './DeleteRelationshipDialog'
import { useRelated } from './hooks'
import { RelationGraph } from './RelationGraph'
import { ENTITY_TYPE_LABEL, shortId, type RelatedItem } from './types'

export interface RelatedPanelProps {
  readonly entityId: string
  /** Se llama al pulsar un vecino; permite navegar el grafo. */
  readonly onSelectEntity?: (entityId: string) => void
  /** Cambia para forzar una recarga desde fuera. */
  readonly refreshKey?: number
  readonly onChanged?: () => void
}

interface Group {
  readonly key: string
  readonly heading: string
  readonly direction: 'in' | 'out'
  readonly items: RelatedItem[]
}

function groupItems(items: readonly RelatedItem[]): Group[] {
  const groups = new Map<string, Group>()
  for (const item of items) {
    const key = `${item.direction}:${item.relationship_type}`
    const group = groups.get(key) ?? { key, heading: item.label, direction: item.direction, items: [] }
    group.items.push(item)
    groups.set(key, group)
  }
  return [...groups.values()].sort((a, b) => (a.direction === b.direction ? 0 : a.direction === 'out' ? -1 : 1))
}

/** Relaciones de un elemento: entrantes, salientes y estructurales. Reutilizable desde otros módulos. */
export function RelatedPanel({ entityId, onSelectEntity, refreshKey = 0, onChanged }: RelatedPanelProps) {
  const [reload, setReload] = useState(0)
  const [pendingDelete, setPendingDelete] = useState<RelatedItem | null>(null)
  const result = useRelated(entityId, refreshKey + reload)

  if (result.state === 'loading') return <p role="status" className="text-sm text-muted-foreground">Cargando relaciones…</p>
  if (result.state === 'error' && isDisconnected(result.error)) {
    return <p className="text-sm text-muted-foreground">Las relaciones aparecerán cuando el espacio de trabajo esté conectado.</p>
  }
  if (result.state === 'error') {
    return <p role="alert" className="text-sm text-destructive">No se han podido cargar las relaciones de este elemento.</p>
  }

  const { data } = result
  const groups = groupItems(data.items)
  const title = data.entity_title

  return (
    <section aria-label={`Relaciones de ${title}`} className="grid gap-4">
      <div>
        <h2 className="text-lg font-semibold text-foreground">{title}</h2>
        <p className="text-sm text-muted-foreground">
          {ENTITY_TYPE_LABEL[data.entity_type]} · <span className="font-mono">{shortId(data.entity_id)}</span>
        </p>
      </div>

      {data.items.length === 0 ? (
        <p className="text-sm text-muted-foreground">Este elemento todavía no tiene relaciones.</p>
      ) : (
        <>
          <RelationGraph title={title} items={data.items} />
          {data.items.length > 12 ? (
            <p className="text-xs text-muted-foreground">
              El mapa muestra 12 vecinos; el resto está en la lista.
            </p>
          ) : null}
          {groups.map((group) => (
            <div key={group.key} className="grid gap-1">
              <h3 className="text-sm font-medium text-foreground">
                {group.direction === 'out' ? 'Salientes' : 'Entrantes'} · {group.heading}
              </h3>
              <ul className="grid gap-1">
                {group.items.map((item, i) => (
                  <li
                    key={`${item.relationship_id ?? 'v'}-${item.entity_id}-${i}`}
                    className="flex items-center gap-2 rounded-md border border-border bg-card px-3 py-2"
                  >
                    <button
                      type="button"
                      disabled={!onSelectEntity}
                      onClick={() => onSelectEntity?.(item.entity_id)}
                      className="min-w-0 flex-1 truncate text-left text-sm outline-none enabled:hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50"
                    >
                      {item.entity_title}
                    </button>
                    <span className="text-xs text-muted-foreground">{ENTITY_TYPE_LABEL[item.entity_type]}</span>
                    {item.archived ? <Badge variant="outline">Archivado</Badge> : null}
                    {item.virtual ? (
                      <Badge variant="secondary">Estructural</Badge>
                    ) : (
                      <Button
                        variant="ghost" size="icon-sm"
                        aria-label={`Eliminar relación con ${item.entity_title}`}
                        onClick={() => setPendingDelete(item)}
                      >
                        <Trash2 />
                      </Button>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </>
      )}

      <DeleteRelationshipDialog
        relationshipId={pendingDelete?.relationship_id ?? null}
        summary={pendingDelete ? `${title} · ${pendingDelete.label} · ${pendingDelete.entity_title}` : ''}
        onClose={() => setPendingDelete(null)}
        onDeleted={() => { setReload((n) => n + 1); onChanged?.() }}
      />
    </section>
  )
}
