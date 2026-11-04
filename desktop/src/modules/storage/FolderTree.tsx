import { useEffect, useState } from 'react'
import { ChevronRight, Folder as FolderIcon, Library } from 'lucide-react'
import { cn } from '@/lib/utils'
import { listFolders } from './api'
import { notifyError } from './errors'
import type { Folder } from './types'

interface Props {
  readonly selectedId: string | null
  readonly onSelect: (id: string | null) => void
  readonly reloadKey: number
}

export function FolderTree({ selectedId, onSelect, reloadKey }: Props) {
  const [roots, setRoots] = useState<readonly Folder[] | null>(null)

  useEffect(() => {
    let live = true
    listFolders(null)
      .then((folders) => live && setRoots(folders))
      .catch((error: unknown) => {
        if (live) setRoots([])
        notifyError('No se han podido cargar las carpetas', error)
      })
    return () => {
      live = false
    }
  }, [reloadKey])

  return (
    <nav aria-label="Carpetas" className="flex flex-col gap-0.5">
      <button
        type="button"
        onClick={() => onSelect(null)}
        aria-current={selectedId === null ? 'true' : undefined}
        className={rowClass(selectedId === null)}
      >
        <Library className="size-4" aria-hidden="true" />
        Todos los recursos
      </button>
      {roots === null ? <p className="px-2 py-1 text-sm text-muted-foreground">Cargando carpetas…</p> : null}
      {roots?.length === 0 ? <p className="px-2 py-1 text-sm text-muted-foreground">Aún no hay carpetas.</p> : null}
      <ul role="tree" aria-label="Árbol de carpetas">
        {roots?.map((folder) => (
          <FolderNode key={folder.id} folder={folder} depth={0} selectedId={selectedId} onSelect={onSelect} />
        ))}
      </ul>
    </nav>
  )
}

function rowClass(active: boolean): string {
  return cn(
    'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm outline-none transition-colors hover:bg-accent focus-visible:ring-[3px] focus-visible:ring-ring/50',
    active && 'bg-accent font-medium text-accent-foreground'
  )
}

function FolderNode({
  folder, depth, selectedId, onSelect
}: { folder: Folder; depth: number; selectedId: string | null; onSelect: (id: string | null) => void }) {
  const [open, setOpen] = useState(false)
  const [children, setChildren] = useState<readonly Folder[] | null>(null)
  const [loading, setLoading] = useState(false)

  function toggle() {
    const next = !open
    setOpen(next)
    if (next && children === null && !loading) {
      setLoading(true)
      listFolders(folder.id)
        .then(setChildren)
        .catch((error: unknown) => {
          setChildren([])
          notifyError('No se han podido cargar las subcarpetas', error)
        })
        .finally(() => setLoading(false))
    }
  }

  const selected = selectedId === folder.id
  return (
    <li role="treeitem" aria-expanded={open} aria-selected={selected}>
      <div className="flex items-center" style={{ paddingLeft: depth * 14 }}>
        <button
          type="button"
          onClick={toggle}
          aria-label={open ? `Contraer ${folder.name}` : `Expandir ${folder.name}`}
          className="grid size-6 shrink-0 place-items-center rounded-md outline-none hover:bg-accent focus-visible:ring-[3px] focus-visible:ring-ring/50"
        >
          <ChevronRight className={cn('size-4 transition-transform', open && 'rotate-90')} aria-hidden="true" />
        </button>
        <button type="button" onClick={() => onSelect(folder.id)} className={rowClass(selected)}>
          <FolderIcon className="size-4 shrink-0" aria-hidden="true" />
          <span className="truncate">{folder.name}</span>
          <span className="ml-auto text-xs text-muted-foreground">{folder.resource_count}</span>
        </button>
      </div>
      {open ? (
        <ul role="group">
          {loading ? <li className="py-1 pl-8 text-sm text-muted-foreground">Cargando…</li> : null}
          {children?.length === 0 ? <li className="py-1 pl-8 text-sm text-muted-foreground">Sin subcarpetas</li> : null}
          {children?.map((child) => (
            <FolderNode key={child.id} folder={child} depth={depth + 1} selectedId={selectedId} onSelect={onSelect} />
          ))}
        </ul>
      ) : null}
    </li>
  )
}
