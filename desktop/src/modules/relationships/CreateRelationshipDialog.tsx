import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { notify } from '@/services/notify'
import { createRelationship, humanError } from './api'
import { useRelationshipTypes } from './hooks'
import { isUuid, RELATIONSHIP_FALLBACK_LABEL, type RelationshipKind } from './types'

export interface CreateRelationshipDialogProps {
  readonly open: boolean
  readonly onOpenChange: (open: boolean) => void
  readonly onCreated: () => void
  readonly initialSourceId?: string
}

const FIELD =
  'h-9 w-full rounded-md border border-input bg-background px-3 font-mono text-sm outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 aria-invalid:border-destructive'

export function CreateRelationshipDialog(props: CreateRelationshipDialogProps) {
  // Se monta solo abierto para que el formulario arranque limpio cada vez.
  return (
    <Dialog open={props.open} onOpenChange={props.onOpenChange}>
      {props.open ? <Form {...props} /> : null}
    </Dialog>
  )
}

function Form({ onOpenChange, onCreated, initialSourceId = '' }: CreateRelationshipDialogProps) {
  const types = useRelationshipTypes()
  const [kind, setKind] = useState<RelationshipKind | ''>('')
  const [source, setSource] = useState(initialSourceId)
  const [target, setTarget] = useState('')
  const [touched, setTouched] = useState(false)
  const [busy, setBusy] = useState(false)

  const list = types.state === 'ready' ? types.data : []
  const current = list.find((t) => t.relationship_type === kind)
  const sourceOk = isUuid(source)
  const targetOk = isUuid(target)
  const valid = kind !== '' && sourceOk && targetOk

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setTouched(true)
    if (kind === '' || !sourceOk || !targetOk) return
    setBusy(true)
    try {
      await createRelationship({ source_id: source.trim(), target_id: target.trim(), relationship_type: kind })
      notify({ tone: 'success', title: 'Relación creada' })
      onOpenChange(false)
      onCreated()
    } catch (error) {
      notify({ tone: 'error', title: 'No se ha podido crear la relación', body: humanError(error) })
    } finally {
      setBusy(false)
    }
  }

  return (
    <DialogContent>
      <form onSubmit={(e) => void submit(e)} className="grid gap-4">
        <DialogHeader>
          <DialogTitle>Nueva relación</DialogTitle>
          <DialogDescription>
            Une dos elementos del espacio de trabajo. Necesitas el identificador de cada uno.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-2">
          <Label htmlFor="rel-type">Tipo de relación</Label>
          <Select value={kind} onValueChange={(v) => setKind(v as RelationshipKind)}>
            <SelectTrigger id="rel-type" className="w-full">
              <SelectValue placeholder={types.state === 'loading' ? 'Cargando tipos…' : 'Elige un tipo'} />
            </SelectTrigger>
            <SelectContent>
              {list.map((t) => (
                <SelectItem key={t.relationship_type} value={t.relationship_type}>
                  {t.label || RELATIONSHIP_FALLBACK_LABEL[t.relationship_type]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {types.state === 'error' ? (
            <p className="text-sm text-destructive">No se han podido cargar los tipos de relación.</p>
          ) : null}
          {current ? (
            <p className="text-sm text-muted-foreground">
              {current.description}
              {current.symmetric ? ' Es simétrica: da igual cuál va primero.' : ''}
            </p>
          ) : null}
        </div>

        <div className="grid gap-2">
          <Label htmlFor="rel-source">Origen (identificador)</Label>
          <input
            id="rel-source" className={FIELD} value={source} spellCheck={false} autoComplete="off"
            aria-invalid={touched && !sourceOk} onChange={(e) => setSource(e.target.value)}
          />
          {touched && !sourceOk ? <p className="text-sm text-destructive">Escribe un identificador válido (UUID).</p> : null}
        </div>

        <div className="grid gap-2">
          <Label htmlFor="rel-target">Destino (identificador)</Label>
          <input
            id="rel-target" className={FIELD} value={target} spellCheck={false} autoComplete="off"
            aria-invalid={touched && !targetOk} onChange={(e) => setTarget(e.target.value)}
          />
          {touched && !targetOk ? <p className="text-sm text-destructive">Escribe un identificador válido (UUID).</p> : null}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button type="submit" disabled={busy || (touched && !valid)}>Crear relación</Button>
        </DialogFooter>
      </form>
    </DialogContent>
  )
}
