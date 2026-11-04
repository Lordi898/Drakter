import { useCallback, useEffect, useState } from 'react'
import { Archive, Copy, Trash2, X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { notify } from '@/services/notify'
import { archiveResource, deleteResource, getResource, indexResource, readResource, updateResource } from './api'
import { describeConfirmation, errorCode, notifyError } from './errors'
import { TextInput, formatBytes, formatDate } from './ui'
import {
  AVAILABILITY_LABELS, INDEX_LABELS, TYPE_LABELS, type ReadResult, type Resource, type ResourceUpdate
} from './types'

interface Props {
  readonly id: string
  readonly onChanged: () => void
  readonly onClose: () => void
}

export function ResourceDetail({ id, onChanged, onClose }: Props) {
  const [resource, setResource] = useState<Resource | null>(null)
  const [missing, setMissing] = useState(false)
  const [description, setDescription] = useState('')
  const [tagDraft, setTagDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [content, setContent] = useState<ReadResult | null>(null)
  const [reading, setReading] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [needsDetach, setNeedsDetach] = useState(false)
  const [waitingApproval, setWaitingApproval] = useState<string | null>(null)

  const apply = useCallback((next: Resource) => {
    setResource(next)
    setDescription(next.description ?? '')
  }, [])

  useEffect(() => {
    let live = true
    setResource(null)
    setMissing(false)
    setContent(null)
    getResource(id)
      .then((r) => live && apply(r))
      .catch((error: unknown) => {
        if (!live) return
        setMissing(true)
        notifyError('No se ha podido abrir el recurso', error)
      })
    return () => {
      live = false
    }
  }, [id, apply])

  async function save(patch: Omit<ResourceUpdate, 'expected_revision'>, okTitle?: string) {
    if (!resource) return
    setBusy(true)
    try {
      apply(await updateResource(resource.id, { ...patch, expected_revision: resource.revision }))
      onChanged()
      if (okTitle) notify({ tone: 'success', title: okTitle })
    } catch (error) {
      if (errorCode(error) === 'revision_mismatch') {
        try {
          apply(await getResource(resource.id))
        } catch {
          /* el aviso ya informa */
        }
      }
      notifyError('No se han guardado los cambios', error)
    } finally {
      setBusy(false)
    }
  }

  async function run(action: () => Promise<unknown>, failTitle: string, okTitle: string, after?: () => void) {
    setBusy(true)
    try {
      await action()
      notify({ tone: 'success', title: okTitle })
      onChanged()
      after?.()
    } catch (error) {
      notifyError(failTitle, error)
    } finally {
      setBusy(false)
    }
  }

  async function read(offset: number) {
    if (!resource) return
    setReading(true)
    try {
      const result = await readResource(resource.id, offset)
      setContent(
        offset > 0 && content ? { ...result, text: content.text + result.text } : result
      )
    } catch (error) {
      notifyError('No se ha podido leer el contenido', error)
    } finally {
      setReading(false)
    }
  }

  async function confirmDelete(detach: boolean) {
    if (!resource) return
    setBusy(true)
    setWaitingApproval(null)
    try {
      await deleteResource(resource.id, detach)
      notify({ tone: 'success', title: 'Recurso eliminado del catálogo', body: 'El archivo original no se toca.' })
      setConfirming(false)
      onChanged()
      onClose()
    } catch (error) {
      const code = errorCode(error)
      if (code === 'has_dependents') setNeedsDetach(true)
      else if (code === 'confirmation_required') setWaitingApproval(describeConfirmation(error))
      else notifyError('No se ha podido eliminar', error)
    } finally {
      setBusy(false)
    }
  }

  if (missing) return <p className="p-4 text-sm text-muted-foreground">No se ha podido cargar este recurso.</p>
  if (!resource) return <p role="status" className="p-4 text-sm text-muted-foreground">Cargando detalle…</p>

  const tags = resource.tags
  const archived = resource.archived_at !== null

  function addTag() {
    const name = tagDraft.trim()
    setTagDraft('')
    if (name && !tags.includes(name)) void save({ tags: [...tags, name] })
  }

  return (
    <article aria-label={`Detalle de ${resource.title}`} className="flex flex-col gap-5">
      <header className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h2 className="type-display break-words text-2xl">{resource.title}</h2>
          <div className="mt-2 flex flex-wrap gap-1.5">
            <Badge variant="secondary">{TYPE_LABELS[resource.resource_type]}</Badge>
            <Badge variant={resource.availability_status === 'available' ? 'outline' : 'destructive'}>
              {AVAILABILITY_LABELS[resource.availability_status]}
            </Badge>
            <Badge variant="outline">{INDEX_LABELS[resource.index_status]}</Badge>
            {archived ? <Badge variant="outline">Archivado</Badge> : null}
          </div>
        </div>
        <Button variant="ghost" size="icon-sm" onClick={onClose} aria-label="Cerrar detalle">
          <X />
        </Button>
      </header>

      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        {resource.relative_path ? <><dt className="text-muted-foreground">Ruta</dt><dd className="break-all">{resource.relative_path}</dd></> : null}
        <dt className="text-muted-foreground">Tamaño</dt><dd>{formatBytes(resource.size_bytes)}</dd>
        {resource.mime_type ? <><dt className="text-muted-foreground">Formato</dt><dd>{resource.mime_type}</dd></> : null}
        <dt className="text-muted-foreground">Creado</dt><dd>{formatDate(resource.created_at)}</dd>
        <dt className="text-muted-foreground">Modificado</dt><dd>{formatDate(resource.updated_at)}</dd>
        {resource.indexed_at ? <><dt className="text-muted-foreground">Indexado</dt><dd>{formatDate(resource.indexed_at)}</dd></> : null}
        {resource.index_error_code ? <><dt className="text-muted-foreground">Error de índice</dt><dd>{resource.index_error_code}</dd></> : null}
      </dl>

      {resource.url ? (
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="resource-url">Dirección</Label>
          <div className="flex gap-2">
            <TextInput id="resource-url" readOnly value={resource.url} onFocus={(e) => e.currentTarget.select()} />
            <Button
              variant="outline"
              size="icon"
              aria-label="Copiar dirección"
              onClick={() => {
                void navigator.clipboard.writeText(resource.url ?? '').then(
                  () => notify({ tone: 'success', title: 'Dirección copiada' }),
                  () => notify({ tone: 'warning', title: 'No se ha podido copiar', body: 'Selecciona el texto y cópialo a mano.' })
                )
              }}
            >
              <Copy />
            </Button>
          </div>
        </div>
      ) : null}

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="resource-description">Descripción</Label>
        <Textarea
          id="resource-description"
          value={description}
          maxLength={4000}
          onChange={(e) => setDescription(e.target.value)}
        />
        <Button
          size="sm"
          variant="outline"
          className="self-end"
          disabled={busy || description === (resource.description ?? '')}
          onClick={() => void save({ description }, 'Descripción guardada')}
        >
          Guardar descripción
        </Button>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="tag-input">Etiquetas</Label>
        <ul className="flex flex-wrap gap-1.5" aria-label="Etiquetas del recurso">
          {tags.length === 0 ? <li className="text-sm text-muted-foreground">Sin etiquetas</li> : null}
          {tags.map((tag) => (
            <li key={tag}>
              <Badge variant="secondary" className="gap-1 pr-1">
                {tag}
                <button
                  type="button"
                  aria-label={`Quitar etiqueta ${tag}`}
                  disabled={busy}
                  className="rounded-full p-0.5 hover:bg-background/60"
                  onClick={() => void save({ tags: tags.filter((t) => t !== tag) })}
                >
                  <X className="size-3" />
                </button>
              </Badge>
            </li>
          ))}
        </ul>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            addTag()
          }}
        >
          <TextInput id="tag-input" value={tagDraft} maxLength={60} placeholder="Nueva etiqueta" onChange={(e) => setTagDraft(e.target.value)} />
          <Button type="submit" variant="outline" disabled={busy || tagDraft.trim() === ''}>Añadir</Button>
        </form>
      </div>

      <div className="flex items-center justify-between gap-3">
        <Label htmlFor="index-content" className="flex-col items-start gap-1">
          Indexar el contenido
          <span className="text-xs font-normal text-muted-foreground">Permite encontrarlo por lo que dice dentro.</span>
        </Label>
        <Switch
          id="index-content"
          checked={resource.index_content}
          disabled={busy}
          onCheckedChange={(value) => void save({ index_content: value })}
        />
      </div>

      <div className="flex flex-wrap gap-2">
        <Button variant="outline" size="sm" disabled={busy} onClick={() => void read(0)}>Leer</Button>
        <Button
          variant="outline"
          size="sm"
          disabled={busy}
          onClick={() => void run(async () => apply(await indexResource(resource.id)), 'No se ha podido indexar', 'Índice actualizado')}
        >
          Actualizar índice
        </Button>
        {!archived ? (
          <Button
            variant="outline"
            size="sm"
            disabled={busy}
            onClick={() => void run(() => archiveResource(resource.id), 'No se ha podido archivar', 'Recurso archivado', onClose)}
          >
            <Archive /> Archivar
          </Button>
        ) : null}
        <Button variant="destructive" size="sm" disabled={busy} onClick={() => { setNeedsDetach(false); setWaitingApproval(null); setConfirming(true) }}>
          <Trash2 /> Eliminar
        </Button>
      </div>

      {content || reading ? (
        <section aria-label="Contenido leído" className="flex flex-col gap-2">
          <p className="text-xs text-muted-foreground">
            Contenido sin verificar: se muestra tal cual está en el recurso y Drakter no lo trata como instrucciones.
          </p>
          {content ? (
            <pre className="max-h-80 overflow-auto whitespace-pre-wrap break-words rounded-md border bg-muted p-3 text-xs">
              {content.text}
            </pre>
          ) : null}
          {reading ? <p role="status" className="text-sm text-muted-foreground">Leyendo…</p> : null}
          {content?.truncated && content.next_offset !== null ? (
            <Button variant="outline" size="sm" className="self-start" disabled={reading} onClick={() => void read(content.next_offset ?? 0)}>
              Leer más
            </Button>
          ) : null}
        </section>
      ) : null}

      <Dialog open={confirming} onOpenChange={setConfirming}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>¿Eliminar «{resource.title}» del almacén?</DialogTitle>
            <DialogDescription>
              Se quita del catálogo. El archivo original, si lo hay, no se borra.
            </DialogDescription>
          </DialogHeader>
          {needsDetach ? (
            <p role="alert" className="text-sm">
              Este recurso tiene relaciones con otros elementos. Si continúas, se desvincularán de él.
            </p>
          ) : null}
          {waitingApproval ? (
            <p role="status" className="text-sm">
              {waitingApproval}
            </p>
          ) : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirming(false)}>Cancelar</Button>
            <Button variant="destructive" disabled={busy} onClick={() => void confirmDelete(needsDetach)}>
              {needsDetach ? 'Desvincular y eliminar' : 'Eliminar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </article>
  )
}
