import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { notify } from '@/services/notify'
import { createResource } from './api'
import { notifyError } from './errors'
import { NativeSelect, TextInput } from './ui'
import type { ResourceCreate, StorageLocation } from './types'

type Kind = 'note' | 'link' | 'file'

interface Props {
  readonly open: boolean
  readonly onOpenChange: (open: boolean) => void
  readonly folderId: string | null
  readonly locations: readonly StorageLocation[]
  readonly onCreated: () => void
}

const KINDS: readonly { id: Kind; label: string }[] = [
  { id: 'note', label: 'Nota' },
  { id: 'link', label: 'Enlace' },
  { id: 'file', label: 'Archivo' }
]

export function CreateResourceDialog({ open, onOpenChange, folderId, locations, onCreated }: Props) {
  const [kind, setKind] = useState<Kind>('note')
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [url, setUrl] = useState('')
  const [locationId, setLocationId] = useState('')
  const [path, setPath] = useState('')
  const [busy, setBusy] = useState(false)

  const usable = locations.filter((l) => l.enabled)
  const chosenLocation = locationId || usable[0]?.id || ''

  function build(): ResourceCreate | null {
    const t = title.trim()
    if (!t) return null
    const folder = folderId ? { folder_id: folderId } : {}
    if (kind === 'note') return { title: t, note_body: body, resource_type: 'note', ...folder }
    if (kind === 'link') return url.trim() ? { title: t, url: url.trim(), resource_type: 'link', ...folder } : null
    return chosenLocation && path.trim()
      ? { title: t, location_id: chosenLocation, relative_path: path.trim(), ...folder }
      : null
  }

  const payload = build()

  async function submit() {
    if (!payload) return
    setBusy(true)
    try {
      await createResource(payload)
      notify({ tone: 'success', title: 'Recurso añadido' })
      setTitle(''); setBody(''); setUrl(''); setPath('')
      onOpenChange(false)
      onCreated()
    } catch (error) {
      notifyError('No se ha podido añadir el recurso', error)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Añadir recurso</DialogTitle>
          <DialogDescription>Una nota, un enlace o un archivo de una de tus ubicaciones.</DialogDescription>
        </DialogHeader>
        <form
          className="grid gap-4"
          onSubmit={(e) => {
            e.preventDefault()
            void submit()
          }}
        >
          <div role="radiogroup" aria-label="Tipo de recurso" className="flex gap-1 rounded-md bg-muted p-1">
            {KINDS.map((k) => (
              <button
                key={k.id}
                type="button"
                role="radio"
                aria-checked={kind === k.id}
                onClick={() => setKind(k.id)}
                className={`flex-1 rounded-sm px-3 py-1 text-sm outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 ${
                  kind === k.id ? 'bg-background font-medium shadow-xs' : 'text-muted-foreground'
                }`}
              >
                {k.label}
              </button>
            ))}
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="new-title">Título</Label>
            <TextInput id="new-title" value={title} maxLength={300} onChange={(e) => setTitle(e.target.value)} required />
          </div>
          {kind === 'note' ? (
            <div className="grid gap-1.5">
              <Label htmlFor="new-body">Texto de la nota</Label>
              <Textarea id="new-body" className="min-h-32" value={body} onChange={(e) => setBody(e.target.value)} />
            </div>
          ) : null}
          {kind === 'link' ? (
            <div className="grid gap-1.5">
              <Label htmlFor="new-url">Dirección (http o https)</Label>
              <TextInput id="new-url" type="url" inputMode="url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://" required />
            </div>
          ) : null}
          {kind === 'file' ? (
            usable.length === 0 ? (
              <p role="status" className="text-sm text-muted-foreground">
                Primero añade una ubicación activa desde el panel de ubicaciones.
              </p>
            ) : (
              <>
                <div className="grid gap-1.5">
                  <Label htmlFor="new-location">Ubicación</Label>
                  <NativeSelect id="new-location" value={chosenLocation} onChange={(e) => setLocationId(e.target.value)}>
                    {usable.map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}
                  </NativeSelect>
                </div>
                <div className="grid gap-1.5">
                  <Label htmlFor="new-path">Ruta dentro de la ubicación</Label>
                  <TextInput id="new-path" value={path} onChange={(e) => setPath(e.target.value)} placeholder="carpeta/documento.pdf" required />
                </div>
              </>
            )
          ) : null}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
            <Button type="submit" disabled={busy || !payload}>Añadir</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
