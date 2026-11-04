import { useState } from 'react'
import { FolderPlus, RefreshCw, ScanSearch, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { notify } from '@/services/notify'
import { createLocation, deleteLocation, refreshIndex, scanLocation, updateLocation } from './api'
import { canPickDirectory, pickDirectory } from './bridge'
import { describeConfirmation, errorCode, notifyError } from './errors'
import type { StorageLocation } from './types'

interface Props {
  readonly locations: readonly StorageLocation[] | null
  readonly onChanged: () => void
}

function lastSegment(path: string): string {
  const parts = path.split(/[\\/]/).filter(Boolean)
  return parts[parts.length - 1] ?? path
}

export function LocationsPanel({ locations, onChanged }: Props) {
  const [busyId, setBusyId] = useState<string | null>(null)
  const [removing, setRemoving] = useState<StorageLocation | null>(null)
  const [waiting, setWaiting] = useState<string | null>(null)
  const pickable = canPickDirectory()

  async function guard(id: string, task: () => Promise<void>, failTitle: string) {
    setBusyId(id)
    try {
      await task()
    } catch (error) {
      notifyError(failTitle, error)
    } finally {
      setBusyId(null)
    }
  }

  async function add() {
    const path = await pickDirectory()
    if (!path) return
    await guard('new', async () => {
      await createLocation(path, lastSegment(path))
      notify({ tone: 'success', title: 'Ubicación añadida', body: 'Es de solo lectura y Drakter no puede leerla hasta que lo permitas.' })
      onChanged()
    }, 'No se ha podido añadir la ubicación')
  }

  async function toggle(location: StorageLocation, patch: { agent_read?: boolean; enabled?: boolean }) {
    await guard(location.id, async () => {
      await updateLocation(location.id, patch)
      onChanged()
    }, 'No se ha podido cambiar la ubicación')
  }

  async function scan(location: StorageLocation) {
    await guard(location.id, async () => {
      const r = await scanLocation(location.id)
      notify({
        tone: 'success',
        title: `Escaneo de «${location.label}» terminado`,
        body: `${r.added} nuevos, ${r.updated} actualizados, ${r.moved} movidos, ${r.missing} no encontrados.${r.truncated ? ' Se alcanzó el límite: queda contenido sin revisar.' : ''}`
      })
      onChanged()
    }, 'No se ha podido escanear')
  }

  async function refresh() {
    await guard('refresh', async () => {
      const r = await refreshIndex()
      notify({
        tone: 'success',
        title: 'Índice refrescado',
        body: `${r.checked} revisados, ${r.reindexed} reindexados, ${r.missing} no encontrados, ${r.failed} con error.`
      })
      onChanged()
    }, 'No se ha podido refrescar el índice')
  }

  async function confirmRemove() {
    if (!removing) return
    setWaiting(null)
    setBusyId(removing.id)
    try {
      await deleteLocation(removing.id)
      notify({ tone: 'success', title: 'Ubicación quitada', body: 'Tus archivos no se han tocado.' })
      setRemoving(null)
      onChanged()
    } catch (error) {
      if (errorCode(error) === 'confirmation_required') setWaiting(describeConfirmation(error))
      else notifyError('No se ha podido quitar la ubicación', error)
    } finally {
      setBusyId(null)
    }
  }

  return (
    <section aria-label="Ubicaciones" className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Ubicaciones</h2>
        <div className="flex gap-1">
          <Button variant="ghost" size="icon-sm" aria-label="Refrescar el índice" title="Refrescar el índice" disabled={busyId !== null} onClick={() => void refresh()}>
            <RefreshCw />
          </Button>
          <Button variant="outline" size="sm" disabled={!pickable || busyId !== null} onClick={() => void add()}>
            <FolderPlus /> Añadir
          </Button>
        </div>
      </div>
      {!pickable ? (
        <p className="text-xs text-muted-foreground">
          Elegir una carpeta necesita el selector nativo, que esta versión del puente todavía no ofrece.
        </p>
      ) : null}
      {locations === null ? <p role="status" className="text-sm text-muted-foreground">Cargando ubicaciones…</p> : null}
      {locations?.length === 0 ? <p className="text-sm text-muted-foreground">Aún no has añadido ninguna carpeta.</p> : null}
      <ul className="flex flex-col gap-2">
        {locations?.map((location) => {
          const busy = busyId === location.id
          return (
            <li key={location.id} className="flex flex-col gap-2 rounded-md border bg-card p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate font-medium">{location.label}</p>
                  <p className="truncate text-xs text-muted-foreground" title={location.path}>{location.path}</p>
                </div>
                <div className="flex shrink-0">
                  <Button variant="ghost" size="icon-sm" aria-label={`Escanear ${location.label}`} title="Escanear" disabled={busy || !location.enabled} onClick={() => void scan(location)}>
                    <ScanSearch />
                  </Button>
                  <Button variant="ghost" size="icon-sm" aria-label={`Quitar ${location.label}`} title="Quitar" disabled={busy} onClick={() => { setWaiting(null); setRemoving(location) }}>
                    <Trash2 />
                  </Button>
                </div>
              </div>
              <div className="flex items-center justify-between gap-2">
                <Label htmlFor={`enabled-${location.id}`} className="font-normal">Activa</Label>
                <Switch id={`enabled-${location.id}`} size="sm" checked={location.enabled} disabled={busy} onCheckedChange={(v) => void toggle(location, { enabled: v })} />
              </div>
              <div className="flex items-center justify-between gap-2">
                <Label htmlFor={`agent-${location.id}`} className="font-normal">Permitir que Drakter lea esta ubicación</Label>
                <Switch id={`agent-${location.id}`} size="sm" checked={location.agent_read} disabled={busy} onCheckedChange={(v) => void toggle(location, { agent_read: v })} />
              </div>
            </li>
          )
        })}
      </ul>

      <Dialog open={removing !== null} onOpenChange={(open) => { if (!open) setRemoving(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>¿Quitar «{removing?.label}» del almacén?</DialogTitle>
            <DialogDescription>
              Se quita la ubicación y sus recursos del catálogo. Los archivos de tu disco no se borran.
            </DialogDescription>
          </DialogHeader>
          {waiting ? <p role="status" className="text-sm">{waiting}</p> : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => setRemoving(null)}>Cancelar</Button>
            <Button variant="destructive" disabled={busyId !== null} onClick={() => void confirmRemove()}>Quitar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  )
}
