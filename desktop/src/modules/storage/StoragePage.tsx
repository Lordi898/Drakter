import { useEffect, useState } from 'react'
import { Plus, Search } from 'lucide-react'
import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { CreateResourceDialog } from './CreateResourceDialog'
import { FolderTree } from './FolderTree'
import { LocationsPanel } from './LocationsPanel'
import { ResourceDetail } from './ResourceDetail'
import { ResourceList, type Filters } from './ResourceList'
import { StorageDrawing } from './StorageDrawing'
import { listLocations } from './api'
import { isDisconnected, notifyError } from './errors'
import { NativeSelect, TextInput } from './ui'
import { AVAILABILITY_LABELS, TYPE_LABELS, type StorageLocation } from './types'

const SUMMARY = 'Un catálogo de tus archivos, enlaces y notas que Drakter podrá buscar y abrir cuando lo necesite.'

function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), ms)
    return () => clearTimeout(timer)
  }, [value, ms])
  return debounced
}

function Disconnected({ onRetry }: { onRetry: () => void }) {
  return (
    <>
      <PageHeader title="Almacén" summary={SUMMARY} />
      <EmptyState
        title="El almacén no está conectado"
        description="Aquí catalogarás imágenes, documentos, PDF, código, enlaces y notas. Ahora mismo la aplicación no tiene conexión con el servicio local, así que no se muestra nada. En cuanto se conecte, tus recursos aparecerán aquí."
        drawing={<StorageDrawing />}
      />
      <Button variant="outline" className="mt-4" onClick={onRetry}>Reintentar la conexión</Button>
    </>
  )
}

export function StoragePage() {
  return <ConnectedStorage />
}

function ConnectedStorage() {
  const [locations, setLocations] = useState<readonly StorageLocation[] | null>(null)
  const [offline, setOffline] = useState(false)
  const [folderId, setFolderId] = useState<string | null>(null)
  const [searchText, setSearchText] = useState('')
  const [type, setType] = useState('')
  const [availability, setAvailability] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)
  const [locationsKey, setLocationsKey] = useState(0)
  const search = useDebounced(searchText, 300)

  useEffect(() => {
    let live = true
    listLocations()
      .then((l) => {
        if (!live) return
        setOffline(false)
        setLocations(l)
      })
      .catch((error: unknown) => {
        if (!live) return
        if (isDisconnected(error)) {
          setOffline(true)
          return
        }
        setLocations([])
        notifyError('No se han podido cargar las ubicaciones', error)
      })
    return () => {
      live = false
    }
  }, [locationsKey])

  const filters: Filters = { folderId, search, type, availability }
  const reload = () => setReloadKey((k) => k + 1)

  if (offline) return <Disconnected onRetry={() => setLocationsKey((k) => k + 1)} />
  if (locations === null) return <p role="status" className="text-sm text-muted-foreground">Conectando con el almacén…</p>

  return (
    <>
      <PageHeader
        title="Almacén"
        summary={SUMMARY}
        actions={
          <Button onClick={() => setCreating(true)}>
            <Plus /> Añadir recurso
          </Button>
        }
      />
      <div role="search" className="mb-4 flex flex-wrap gap-2">
        <div className="relative min-w-60 flex-1">
          <Search className="pointer-events-none absolute top-2.5 left-3 size-4 text-muted-foreground" aria-hidden="true" />
          <TextInput
            type="search"
            aria-label="Buscar en el almacén"
            placeholder="Buscar por título, descripción o contenido"
            className="pl-9"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
          />
        </div>
        <NativeSelect aria-label="Filtrar por tipo" className="w-40" value={type} onChange={(e) => setType(e.target.value)}>
          <option value="">Todos los tipos</option>
          {Object.entries(TYPE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </NativeSelect>
        <NativeSelect aria-label="Filtrar por disponibilidad" className="w-48" value={availability} onChange={(e) => setAvailability(e.target.value)}>
          <option value="">Cualquier disponibilidad</option>
          {Object.entries(AVAILABILITY_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </NativeSelect>
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-[16rem_minmax(0,1fr)] xl:grid-cols-[16rem_minmax(0,1fr)_24rem]">
        <aside className="flex flex-col gap-6">
          <FolderTree selectedId={folderId} onSelect={setFolderId} reloadKey={reloadKey} />
          <LocationsPanel
            locations={locations}
            onChanged={() => { setLocationsKey((k) => k + 1); reload() }}
          />
        </aside>
        <main aria-label="Lista de recursos">
          <ResourceList filters={filters} reloadKey={reloadKey} selectedId={selectedId} onSelect={setSelectedId} />
        </main>
        <aside aria-label="Detalle del recurso" className="lg:col-span-2 xl:col-span-1">
          {selectedId ? (
            <ResourceDetail key={selectedId} id={selectedId} onChanged={reload} onClose={() => setSelectedId(null)} />
          ) : (
            <p className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
              Elige un recurso de la lista para ver sus datos, etiquetas y contenido.
            </p>
          )}
        </aside>
      </div>

      <CreateResourceDialog
        open={creating}
        onOpenChange={setCreating}
        folderId={folderId}
        locations={locations ?? []}
        onCreated={reload}
      />
    </>
  )
}
