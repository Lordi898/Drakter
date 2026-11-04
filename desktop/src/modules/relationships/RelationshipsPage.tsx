import { useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { isBackendAvailable } from '@/modules/storage/backend'
import { CreateRelationshipDialog } from './CreateRelationshipDialog'
import { DeleteRelationshipDialog } from './DeleteRelationshipDialog'
import { useRelationshipList, useRelationshipTypes } from './hooks'
import { RelatedPanel } from './RelatedPanel'
import { RelationshipsDrawing } from './RelationshipsDrawing'
import {
  ENTITY_TYPES, ENTITY_TYPE_LABEL, RELATIONSHIP_FALLBACK_LABEL, RELATIONSHIP_TYPES, shortId,
  type EntityType, type RelationshipKind, type RelationshipOut
} from './types'

const ALL = 'all'

export function RelationshipsPage() {
  if (!isBackendAvailable()) {
    return (
      <>
        <PageHeader
          title="Relaciones"
          summary="Los vínculos entre tareas, proyectos, asignaturas, documentos y otros elementos del espacio de trabajo."
        />
        <EmptyState
          title="Las relaciones aparecerán al conectar el espacio de trabajo"
          description="Todavía no hay conexión con el backend, así que no se puede leer ni crear ningún vínculo. Cuando esté conectado podrás explorar las relaciones, ver las de cada elemento y crearlas o eliminarlas."
          drawing={<RelationshipsDrawing />}
          pendingAction={{ label: 'Nueva relación', reason: 'Disponible cuando el espacio de trabajo esté conectado' }}
        />
      </>
    )
  }
  return <ConnectedPage />
}

function ConnectedPage() {
  const [kind, setKind] = useState<RelationshipKind | typeof ALL>(ALL)
  const [entityType, setEntityType] = useState<EntityType | typeof ALL>(ALL)
  const [selected, setSelected] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [deleting, setDeleting] = useState<RelationshipOut | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const types = useRelationshipTypes()

  const list = useRelationshipList(
    {
      ...(kind === ALL ? {} : { relationship_type: kind }),
      ...(entityType === ALL ? {} : { entity_type: entityType })
    },
    refreshKey
  )
  const refresh = () => setRefreshKey((n) => n + 1)
  const labelOf = (k: RelationshipKind) =>
    (types.state === 'ready' ? types.data.find((t) => t.relationship_type === k)?.label : undefined) ??
    RELATIONSHIP_FALLBACK_LABEL[k]

  return (
    <>
      <PageHeader
        title="Relaciones"
        summary="Los vínculos entre tareas, proyectos, asignaturas, documentos y otros elementos del espacio de trabajo."
        actions={
          <Button onClick={() => setCreating(true)}>
            <Plus /> Nueva relación
          </Button>
        }
      />

      <div className="mb-6 flex flex-wrap items-end gap-4">
        <div className="grid gap-1.5">
          <Label htmlFor="filter-kind">Tipo de relación</Label>
          <Select value={kind} onValueChange={(v) => setKind(v as RelationshipKind | typeof ALL)}>
            <SelectTrigger id="filter-kind" className="w-52"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>Todos</SelectItem>
              {RELATIONSHIP_TYPES.map((k) => <SelectItem key={k} value={k}>{labelOf(k)}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="filter-entity">Tipo de elemento</Label>
          <Select value={entityType} onValueChange={(v) => setEntityType(v as EntityType | typeof ALL)}>
            <SelectTrigger id="filter-entity" className="w-52"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>Todos</SelectItem>
              {ENTITY_TYPES.map((t) => <SelectItem key={t} value={t}>{ENTITY_TYPE_LABEL[t]}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <section aria-label="Lista de relaciones" className="min-w-0">
          {list.error ? (
            <p role="alert" className="text-destructive">No se han podido cargar las relaciones.</p>
          ) : null}
          {!list.loading && !list.error && list.items.length === 0 ? (
            <EmptyState
              title="No hay relaciones con estos filtros"
              description="Crea una con «Nueva relación» o cambia los filtros para ver otras."
              drawing={<RelationshipsDrawing />}
            />
          ) : (
            <ul className="grid gap-2">
              {list.items.map((r) => (
                <li key={r.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border border-border bg-card px-3 py-2 text-sm">
                  <Endpoint id={r.source_id} type={r.source_type} onSelect={setSelected} />
                  <span className="text-muted-foreground">→ {labelOf(r.relationship_type)} →</span>
                  <Endpoint id={r.target_id} type={r.target_type} onSelect={setSelected} />
                  <Button
                    className="ml-auto" variant="ghost" size="icon-sm"
                    aria-label={`Eliminar relación ${labelOf(r.relationship_type)} entre ${ENTITY_TYPE_LABEL[r.source_type]} ${shortId(r.source_id)} y ${ENTITY_TYPE_LABEL[r.target_type]} ${shortId(r.target_id)}`}
                    onClick={() => setDeleting(r)}
                  >
                    <Trash2 />
                  </Button>
                </li>
              ))}
            </ul>
          )}
          {list.loading ? <p role="status" className="mt-3 text-sm text-muted-foreground">Cargando…</p> : null}
          {list.hasMore && !list.loading ? (
            <Button className="mt-3" variant="outline" onClick={list.loadMore}>Cargar más</Button>
          ) : null}
        </section>

        <aside aria-label="Relaciones del elemento" className="min-w-0 rounded-md border border-border bg-card/50 p-4 lg:self-start">
          {selected ? (
            <RelatedPanel entityId={selected} onSelectEntity={setSelected} refreshKey={refreshKey} onChanged={refresh} />
          ) : (
            <p className="text-sm text-muted-foreground">
              Pulsa el origen o el destino de una relación para ver todas las relaciones de ese elemento.
            </p>
          )}
        </aside>
      </div>

      <CreateRelationshipDialog
        open={creating}
        onOpenChange={setCreating}
        onCreated={refresh}
        {...(selected ? { initialSourceId: selected } : {})}
      />
      <DeleteRelationshipDialog
        relationshipId={deleting?.id ?? null}
        summary={deleting ? `${ENTITY_TYPE_LABEL[deleting.source_type]} ${shortId(deleting.source_id)} ${labelOf(deleting.relationship_type)} ${ENTITY_TYPE_LABEL[deleting.target_type]} ${shortId(deleting.target_id)}` : ''}
        onClose={() => setDeleting(null)}
        onDeleted={refresh}
      />
    </>
  )
}

function Endpoint({ id, type, onSelect }: { id: string; type: EntityType; onSelect: (id: string) => void }) {
  return (
    <button
      type="button"
      onClick={() => onSelect(id)}
      className="rounded-sm px-1 outline-none hover:bg-accent focus-visible:ring-[3px] focus-visible:ring-ring/50"
      title={id}
    >
      {ENTITY_TYPE_LABEL[type]} <span className="font-mono text-xs text-muted-foreground">{shortId(id)}</span>
    </button>
  )
}
