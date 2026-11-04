import { useCallback, useEffect, useRef, useState } from 'react'
import { FileText, Link as LinkIcon, NotebookPen } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { listResources, searchResources } from './api'
import { notifyError } from './errors'
import { AVAILABILITY_LABELS, TYPE_LABELS, type ResourceSummary } from './types'

export interface Filters {
  readonly folderId: string | null
  readonly search: string
  readonly type: string
  readonly availability: string
}

interface Props {
  readonly filters: Filters
  readonly reloadKey: number
  readonly selectedId: string | null
  readonly onSelect: (id: string) => void
}

interface Row {
  readonly resource: ResourceSummary
  readonly snippet?: string
}

export function ResourceList({ filters, reloadKey, selectedId, onSelect }: Props) {
  const [rows, setRows] = useState<readonly Row[]>([])
  const [cursor, setCursor] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const generation = useRef(0)
  const searching = filters.search.trim() !== ''

  const fetchPage = useCallback(
    async (after: string | null) => {
      const mine = ++generation.current
      setLoading(true)
      setFailed(false)
      try {
        let page: { rows: Row[]; next: string | null }
        if (searching) {
          const result = await searchResources(filters.search.trim(), filters.type, after)
          const kept = result.items.filter(
            (hit) => filters.availability === '' || hit.resource.availability_status === filters.availability
          )
          page = { rows: kept.map((hit) => ({ resource: hit.resource, snippet: hit.snippet })), next: result.next_cursor }
        } else {
          const result = await listResources({
            folderId: filters.folderId, type: filters.type, availability: filters.availability, cursor: after
          })
          page = { rows: result.items.map((resource) => ({ resource })), next: result.next_cursor }
        }
        if (mine !== generation.current) return
        setRows((prev) => (after ? [...prev, ...page.rows] : page.rows))
        setCursor(page.next)
      } catch (error) {
        if (mine !== generation.current) return
        setFailed(true)
        notifyError('No se han podido cargar los recursos', error)
      } finally {
        if (mine === generation.current) setLoading(false)
      }
    },
    [filters.folderId, filters.search, filters.type, filters.availability, searching]
  )

  useEffect(() => {
    void fetchPage(null)
  }, [fetchPage, reloadKey])

  if (loading && rows.length === 0) {
    return <p role="status" className="p-4 text-sm text-muted-foreground">Cargando recursos…</p>
  }
  if (failed && rows.length === 0) {
    return (
      <div className="flex flex-col items-start gap-2 p-4 text-sm">
        <p className="text-muted-foreground">No se han podido cargar los recursos.</p>
        <Button size="sm" variant="outline" onClick={() => void fetchPage(null)}>Reintentar</Button>
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
      {cursor ? (
        <Button variant="outline" size="sm" disabled={loading} onClick={() => void fetchPage(cursor)} className="self-center">
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
