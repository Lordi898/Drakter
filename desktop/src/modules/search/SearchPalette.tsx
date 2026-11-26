import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react'
import {
  CalendarDays,
  FileText,
  Flame,
  FolderKanban,
  GraduationCap,
  Radar,
  Search,
  SquareCheckBig,
  type LucideIcon
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog'
import { navigateTo } from '@/navigation/route'
import { jarvisAvailable, prefetchJarvis, requestUiMode } from '@/stores/uiMode'
import type { SectionId } from '@/navigation/sections'
import type { SearchEntityType, SearchItem } from './searchApi'
import { highlightTerms } from './highlight'
import { useGlobalSearch } from './useGlobalSearch'

const TYPE_META: Record<
  SearchEntityType,
  { label: string; icon: LucideIcon; section: SectionId }
> = {
  task: { label: 'Tareas', icon: SquareCheckBig, section: 'tasks' },
  project: { label: 'Proyectos', icon: FolderKanban, section: 'projects' },
  habit: { label: 'Hábitos', icon: Flame, section: 'habits' },
  calendar_event: { label: 'Eventos', icon: CalendarDays, section: 'calendar' },
  subject: { label: 'Asignaturas', icon: GraduationCap, section: 'subjects' },
  resource: { label: 'Recursos', icon: FileText, section: 'storage' }
}

interface Group {
  readonly type: SearchEntityType
  readonly items: readonly SearchItem[]
}

function groupItems(items: readonly SearchItem[]): Group[] {
  const map = new Map<SearchEntityType, SearchItem[]>()
  for (const item of items) {
    if (!(item.entity_type in TYPE_META)) continue
    const list = map.get(item.entity_type)
    if (list) list.push(item)
    else map.set(item.entity_type, [item])
  }
  return Array.from(map, ([type, list]) => ({ type, items: list }))
}

/** Acción «Abrir modo Jarvis»: aparece si lo escrito es el principio de «modo jarvis» o contiene «jarvis». */
function matchesJarvis(query: string): boolean {
  const q = query.trim().toLowerCase().normalize('NFD').replace(/\p{M}/gu, '').replace(/\s+/g, ' ')
  if (q.length < 3 || !jarvisAvailable()) return false
  return 'modo jarvis'.startsWith(q) || 'jarvis'.startsWith(q) || q.includes('jarvis')
}

function Snippet({ item, query }: { item: SearchItem; query: string }) {
  if (!item.snippet) return null
  return (
    <span className="block truncate text-xs text-muted-foreground">
      {highlightTerms(item.snippet, query).map((part, i) =>
        part.match ? (
          <mark key={i} className="rounded-xs bg-accent px-0.5 text-accent-foreground">
            {part.text}
          </mark>
        ) : (
          <span key={i}>{part.text}</span>
        )
      )}
    </span>
  )
}

export function SearchPalette() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const onKey = (event: globalThis.KeyboardEvent) => {
      if (
        event.ctrlKey &&
        !event.altKey &&
        !event.shiftKey &&
        !event.metaKey &&
        event.key.toLowerCase() === 'k'
      ) {
        event.preventDefault()
        setOpen(true)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const state = useGlobalSearch(query, open)
  const groups = useMemo(
    () => (state.status === 'ready' ? groupItems(state.items) : []),
    [state]
  )
  const flat = useMemo(() => groups.flatMap((g) => g.items), [groups])
  const command = matchesJarvis(query)
  // La acción, si la hay, ocupa la posición 0 y desplaza los resultados.
  const offset = command ? 1 : 0
  const total = flat.length + offset

  useEffect(() => {
    setActive(0)
  }, [flat, command])

  useEffect(() => {
    if (command) prefetchJarvis()
  }, [command])

  const optionId = (i: number) => `search-option-${i}`

  useEffect(() => {
    if (!open || total === 0) return
    listRef.current?.querySelector(`#${optionId(active)}`)?.scrollIntoView({ block: 'nearest' })
  }, [active, open, total])

  const changeOpen = (next: boolean) => {
    setOpen(next)
    if (!next) {
      setQuery('')
      setActive(0)
    }
  }

  const openItem = (item: SearchItem) => {
    changeOpen(false)
    navigateTo(TYPE_META[item.entity_type].section)
  }

  const openJarvis = () => {
    changeOpen(false)
    requestUiMode('jarvis', 'button')
  }

  const onInputKey = (event: KeyboardEvent<HTMLInputElement>) => {
    if (total === 0) return
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setActive((i) => (i + 1) % total)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActive((i) => (i - 1 + total) % total)
    } else if (event.key === 'Enter') {
      event.preventDefault()
      if (command && active === 0) {
        openJarvis()
        return
      }
      const item = flat[active - offset]
      if (item) openItem(item)
    }
  }

  const hasQuery = query.trim().length >= 1
  const showList = command || (state.status === 'ready' && flat.length > 0)

  let message: string | null = null
  if (!hasQuery) message = 'Escribe para buscar en tareas, proyectos, hábitos y más.'
  else if (state.status === 'loading') message = 'Buscando…'
  else if (state.status === 'unavailable')
    message =
      state.reason === 'not-connected'
        ? 'La búsqueda no está conectada'
        : 'La búsqueda no está disponible ahora mismo'
  else if (state.status === 'error') message = state.message
  else if (state.status === 'ready' && flat.length === 0 && !command) message = 'Sin resultados'

  let index = offset
  return (
    <Dialog open={open} onOpenChange={changeOpen}>
      <DialogContent
        showCloseButton={false}
        className="top-[20%] translate-y-0 gap-0 p-0 sm:max-w-xl"
        aria-describedby={undefined}
      >
        <DialogTitle className="sr-only">Búsqueda global</DialogTitle>
        <DialogDescription className="sr-only">
          Busca en el espacio de trabajo y abre la sección del resultado.
        </DialogDescription>
        <div className="flex items-center gap-2 border-b px-3">
          <Search className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          <input
            autoFocus
            type="text"
            role="combobox"
            aria-label="Buscar"
            aria-autocomplete="list"
            aria-controls="search-listbox"
            aria-expanded={showList}
            aria-activedescendant={showList ? optionId(active) : undefined}
            maxLength={200}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onInputKey}
            placeholder="Buscar…"
            className="h-12 w-full bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
          />
        </div>
        {message !== null && (
          <p role="status" className="px-4 py-6 text-center text-sm text-muted-foreground">
            {message}
          </p>
        )}
        <div
          ref={listRef}
          id="search-listbox"
          role="listbox"
          aria-label="Resultados"
          hidden={!showList}
          className="max-h-80 overflow-y-auto p-1"
        >
          {command ? (
            <div role="group" aria-label="Acciones">
              <div aria-hidden="true" className="px-2 pt-2 pb-1 text-xs font-medium text-muted-foreground">
                Acciones
              </div>
              <div
                id={optionId(0)}
                role="option"
                aria-selected={active === 0}
                onMouseMove={() => setActive(0)}
                onClick={openJarvis}
                className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm text-foreground aria-selected:bg-accent aria-selected:text-accent-foreground"
              >
                <Radar className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                <span className="flex-1">Abrir modo Jarvis</span>
                <kbd className="text-xs text-muted-foreground">Ctrl+Shift+J</kbd>
              </div>
            </div>
          ) : null}
          {groups.map((group) => {
            const meta = TYPE_META[group.type]
            const Icon = meta.icon
            return (
              <div key={group.type} role="group" aria-label={meta.label}>
                <div
                  aria-hidden="true"
                  className="px-2 pt-2 pb-1 text-xs font-medium text-muted-foreground"
                >
                  {meta.label}
                </div>
                {group.items.map((item) => {
                  const i = index++
                  const selected = i === active
                  return (
                    <div
                      key={`${item.entity_type}:${item.entity_id}`}
                      id={optionId(i)}
                      role="option"
                      aria-selected={selected}
                      onMouseMove={() => setActive(i)}
                      onClick={() => openItem(item)}
                      className="flex cursor-pointer items-start gap-2 rounded-md px-2 py-1.5 text-sm text-foreground aria-selected:bg-accent aria-selected:text-accent-foreground"
                    >
                      <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate">{item.title}</span>
                        <Snippet item={item} query={query} />
                      </span>
                      {item.entity_type === 'resource' && (
                        <Badge variant="outline" title="Contenido externo">
                          documento
                        </Badge>
                      )}
                    </div>
                  )
                })}
              </div>
            )
          })}
        </div>
      </DialogContent>
    </Dialog>
  )
}
