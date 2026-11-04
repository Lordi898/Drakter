import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { notify } from '@/services/notify'
import { createProject, listProjects } from './api'
import { ProjectDetail } from './ProjectDetail'
import { DEFAULT_FILTERS, ProjectFilters, type ProjectFilterValues } from './ProjectFilters'
import { ProjectForm } from './ProjectForm'
import { ProjectList } from './ProjectList'
import { LoadFailure, LoadingNote } from './ProjectStates'
import { ProjectsDrawing } from './ProjectsDrawing'
import type { Project, ProjectCreate, ProjectListParams } from './types'
import { toLoadError, type LoadError } from './useLoad'

function toParams(f: ProjectFilterValues): ProjectListParams {
  return {
    ...(f.q.trim() === '' ? {} : { q: f.q.trim() }),
    ...(f.status === 'all' ? {} : { status: [f.status] }),
    ...(f.priority === 'all' ? {} : { priority: [f.priority] }),
    archived: f.archived,
    sort: f.sort,
    limit: 25
  }
}

function useProjectList(filters: ProjectFilterValues) {
  const [items, setItems] = useState<readonly Project[]>([])
  const [cursor, setCursor] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<LoadError | null>(null)
  const [tick, setTick] = useState(0)
  const latest = useRef(0)
  const params = useMemo(() => toParams(filters), [filters])

  useEffect(() => {
    const id = ++latest.current
    setLoading(true)
    setError(null)
    listProjects(params)
      .then((page) => {
        if (id !== latest.current) return
        setItems(page.items)
        setCursor(page.next_cursor)
      })
      .catch((e: unknown) => {
        if (id !== latest.current) return
        setItems([])
        setCursor(null)
        setError(toLoadError(e))
      })
      .finally(() => {
        if (id === latest.current) setLoading(false)
      })
  }, [params, tick])

  const loadMore = useCallback(() => {
    if (cursor === null) return
    const id = ++latest.current
    setLoadingMore(true)
    listProjects({ ...params, cursor })
      .then((page) => {
        if (id !== latest.current) return
        setItems((c) => [...c, ...page.items])
        setCursor(page.next_cursor)
      })
      .catch((e: unknown) => {
        if (id === latest.current) notify({ tone: 'error', title: 'No se pudieron cargar más proyectos', body: toLoadError(e).message })
      })
      .finally(() => {
        if (id === latest.current) setLoadingMore(false)
      })
  }, [cursor, params])

  const reload = useCallback(() => setTick((n) => n + 1), [])
  return { items, hasMore: cursor !== null, loading, loadingMore, error, loadMore, reload }
}

export function ProjectsPage() {
  const [filters, setFilters] = useState<ProjectFilterValues>(DEFAULT_FILTERS)
  const [openId, setOpenId] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const list = useProjectList(filters)

  if (openId !== null) {
    return <ProjectDetail id={openId} onBack={() => setOpenId(null)} onChanged={list.reload} />
  }

  const filtered = filters.q.trim() !== '' || filters.status !== 'all' || filters.priority !== 'all' || filters.archived !== 'exclude'
  const create = (
    <Button onClick={() => setCreating(true)}>Crear proyecto</Button>
  )

  return (
    <div>
      <PageHeader
        title="Proyectos"
        summary="Tus proyectos con su objetivo, fechas, prioridad y progreso."
        actions={list.error === null ? create : undefined}
      />
      <ProjectFilters values={filters} onChange={setFilters} />

      {list.error !== null ? (
        <LoadFailure error={list.error} what="los proyectos" onRetry={list.reload} />
      ) : list.loading && list.items.length === 0 ? (
        <LoadingNote label="Cargando proyectos…" />
      ) : list.items.length === 0 ? (
        filtered ? (
          <EmptyState
            title="Ningún proyecto coincide"
            description="Prueba con otra búsqueda o quita algún filtro."
            drawing={<ProjectsDrawing />}
          />
        ) : (
          <div className="flex flex-col gap-4">
            <EmptyState
              title="Todavía no hay proyectos"
              description="Un proyecto reúne un objetivo, unas fechas y las tareas que lo hacen avanzar. Crea el primero cuando quieras."
              drawing={<ProjectsDrawing />}
            />
            <Button className="self-start" onClick={() => setCreating(true)}>
              Crear proyecto
            </Button>
          </div>
        )
      ) : (
        <ProjectList
          items={list.items}
          hasMore={list.hasMore}
          loadingMore={list.loadingMore}
          onLoadMore={list.loadMore}
          onOpen={setOpenId}
        />
      )}

      <ProjectForm
        open={creating}
        project={null}
        onClose={() => setCreating(false)}
        onStale={list.reload}
        onSubmit={async (data) => {
          const created = await createProject(data as ProjectCreate)
          notify({ tone: 'success', title: 'Proyecto creado' })
          list.reload()
          setOpenId(created.id)
        }}
      />
    </div>
  )
}
