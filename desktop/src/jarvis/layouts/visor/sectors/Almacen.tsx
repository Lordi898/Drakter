/**
 * Sector Almacén (rumbo 309°, sección `storage`): buscar en el Almacén (búsqueda real del backend),
 * núcleo 3D de documentos coloreado por estado de indexación, indexación por tipo, recientes e
 * indicadores. Nada destructivo desde el HUD; «abrir» lleva al Almacén de Drakter.
 * Fragmentos y títulos son datos no confiables: se pintan como texto plano.
 * Los recuentos de indexación son sobre la muestra de recientes (D1), y así se dice.
 */
import { useContext, useEffect, useMemo, useRef, useState } from 'react'
import { useJarvisData } from '@/jarvis/data'
import { searchResources } from '@/modules/storage/api'
import { TYPE_LABELS, type IndexStatus, type ResourceSummary, type SearchHit } from '@/modules/storage/types'
import { describeError } from '@/services/api'
import { drawStorage } from '../charts'
import { Panel, WorldContext } from '../Panel'
import { createDocCore, type DocCorePart } from '../stage/parts'
import { D, FAR, NEAR } from '../stage/world'
import { Chart2D, Kpis, SnapNote, useVisorNav } from './common'

const TOPICS = ['resources', 'folders', 'resourceIndex'] as const
const S = 6
const INDEX_ES: Record<IndexStatus, string> = { indexed: 'indexados', pending: 'en cola', none: 'sin indexar', failed: 'con error', skipped: 'omitidos' }
const CORE_COLOR: Record<IndexStatus, string> = { indexed: '#8be9ff', pending: '#3d8bff', none: '#2a63c9', failed: '#ffb547', skipped: '#3d5a70' }

const sizeText = (b: number | null): string => (b === null ? '' : b < 1024 ? `${b} B` : b < 1048576 ? `${Math.round(b / 1024)} KB` : `${(b / 1048576).toFixed(1).replace('.', ',')} MB`)

function useSearch(q: string): { readonly hits: readonly SearchHit[] | null; readonly error: string | null; readonly loading: boolean } {
  const [state, setState] = useState<{ hits: readonly SearchHit[] | null; error: string | null; loading: boolean }>({ hits: null, error: null, loading: false })
  useEffect(() => {
    const text = q.trim()
    if (text.length < 2) { setState({ hits: null, error: null, loading: false }); return }
    let alive = true
    setState((s) => ({ ...s, loading: true }))
    const t = window.setTimeout(() => {
      searchResources(text, '')
        .then((p) => { if (alive) setState({ hits: p.items, error: null, loading: false }) })
        .catch((e: unknown) => { if (alive) setState({ hits: null, error: describeError(e, 'No se ha podido buscar.'), loading: false }) })
    }, 300)
    return () => { alive = false; window.clearTimeout(t) }
  }, [q])
  return state
}

function Row({ r, snippet, onOpen }: { readonly r: ResourceSummary; readonly snippet?: string; readonly onOpen: () => void }) {
  return (
    <button type="button" className={`jv-visor-file t-${r.resource_type} ix-${r.index_status}`} data-lock={`Abrir en Drakter: ${r.title}`} onClick={onOpen}>
      <i>{TYPE_LABELS[r.resource_type]}</i>
      <span><b>{r.title}</b><small>{snippet ?? `${INDEX_ES[r.index_status]}${r.size_bytes !== null ? `  ·  ${sizeText(r.size_bytes)}` : ''}  ·  ${new Date(r.updated_at).toLocaleDateString('es-ES', { day: 'numeric', month: 'short' })}`}</small></span>
    </button>
  )
}

export function Almacen() {
  const { resources, folders, resourceIndex } = useJarvisData(TOPICS)
  const { openInDrakter } = useVisorNav()
  const world = useContext(WorldContext)
  const [q, setQ] = useState('')
  const search = useSearch(q)
  const recent = resources.data ?? []
  const idx = resourceIndex.data
  const inFolders = (folders.data ?? []).reduce((s, f) => s + f.resource_count, 0)
  const total = Math.max(inFolders, recent.length)
  const indexedPct = idx && idx.sample ? Math.round((idx.counts.indexed / idx.sample) * 100) : null

  // 3D: un punto por documento (con tope), repartidos según la indexación de la muestra.
  const partRef = useRef<DocCorePart | null>(null)
  useEffect(() => {
    if (!world) return
    const p = createDocCore(world)
    partRef.current = p
    return () => { p.dispose(); partRef.current = null }
  }, [world])
  useEffect(() => {
    if (!idx || !idx.sample) { partRef.current?.setData([]); return }
    const groups = (Object.keys(INDEX_ES) as IndexStatus[]).filter((s) => idx.counts[s] > 0).map((s) => {
      const n = Math.round((idx.counts[s] / idx.sample) * total)
      return [CORE_COLOR[s], n, s === 'indexed' ? n : s === 'failed' ? n : 0] as const
    })
    partRef.current?.setData(groups)
  }, [idx, total, world])

  const byType = useMemo(() => {
    const m = new Map<string, number>()
    for (const r of recent) m.set(r.resource_type, (m.get(r.resource_type) ?? 0) + 1)
    return { rows: [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6).map(([t, count], i) => ({ label: TYPE_LABELS[t as keyof typeof TYPE_LABELS] ?? t, count, tone: (i % 2 ? 'blue' : 'ice') as 'blue' | 'ice' })) }
  }, [recent])
  const open = (): void => openInDrakter('storage')

  return (
    <>
      <Panel sector={S} R={FAR} y={30} w={780} h={560} alpha={0.32} title="Almacén" code="ALM-01" className="alm">
        <div className="alm-r">
          <form onSubmit={(e) => e.preventDefault()} role="search">
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar en el Almacén…" aria-label="Buscar en el Almacén" autoComplete="off" />
          </form>
          <div className="alm-res">
            {q.trim().length >= 2 ? (
              <>
                {search.loading && !search.hits && <p className="jv-visor-note">Buscando…</p>}
                {search.error && <p className="jv-visor-note warn">{search.error}</p>}
                {search.hits && search.hits.length === 0 && <p className="jv-visor-note">Nada con «{q.trim()}».</p>}
                {search.hits?.slice(0, 7).map((h) => <Row key={h.resource.id} r={h.resource} snippet={h.snippet.replace(/\s+/g, ' ').slice(0, 120)} onOpen={open} />)}
              </>
            ) : (
              <>
                <SnapNote snap={resources} empty="El Almacén está vacío. Añade una ubicación en Drakter." isEmpty={recent.length === 0} />
                {recent.slice(0, 7).map((r) => <Row key={r.id} r={r} onOpen={open} />)}
              </>
            )}
          </div>
        </div>
        <div className="alm-core" data-lock={`${total} documentos`}><b>{folders.data || resources.data ? total.toLocaleString('es-ES') : '–'}</b><span>documentos</span></div>
      </Panel>

      <Panel sector={S} dA={-26} R={NEAR} y={10} w={330} h={440} side title="Indexación" code="ALM-02">
        <SnapNote snap={resourceIndex} empty="Sin recursos que indexar." isEmpty={!idx || idx.sample === 0} />
        {idx && idx.sample > 0 && (
          <>
            <div className="jv-visor-count" data-lock={`${indexedPct} % indexado`}><b>{indexedPct} %</b><span>indexado, en los {idx.sample} más recientes</span></div>
            <div className="jv-visor-meter"><i style={{ transform: `scaleX(${(indexedPct ?? 0) / 100})` }} /></div>
            <ul className="jv-visor-ixs">
              {(Object.keys(INDEX_ES) as IndexStatus[]).filter((s) => idx.counts[s] > 0).map((s) => <li key={s} className={`ix-${s}`}><b>{idx.counts[s]}</b>{INDEX_ES[s]}</li>)}
            </ul>
            {byType.rows.length > 0 && <Chart2D sector={S} w={296} h={180} sig={JSON.stringify(byType)} lock="Recursos por tipo" draw={(x, w, h, b) => drawStorage(x, w, h, byType, b)} />}
          </>
        )}
      </Panel>

      <Panel sector={S} dA={26} R={NEAR} y={10} w={330} h={440} side title="Carpetas" code="ALM-03">
        <SnapNote snap={folders} empty="No hay carpetas en la raíz." isEmpty={(folders.data ?? []).length === 0} />
        {(folders.data ?? []).slice(0, 8).map((f) => (
          <button type="button" key={f.id} className="jv-visor-deg" data-lock={`Abrir en Drakter: ${f.name}`} onClick={open}>
            <b>{f.name}</b><span>carpeta</span><i style={{ ['--v' as string]: inFolders ? f.resource_count / inFolders : 0 }} /><em>{f.resource_count}</em>
          </button>
        ))}
      </Panel>

      <Panel sector={S} R={D - 110} y={-300} w={640} h={100} side title="Estado" code="ALM-04" className="kpis">
        <Kpis items={[
          [folders.data ? folders.data.length : '–', 'carpetas raíz'],
          [folders.data ? inFolders : '–', 'en carpetas'],
          [idx ? idx.counts.indexed : '–', 'indexados'],
          [idx ? idx.counts.pending : '–', 'en cola'],
          [idx ? idx.counts.failed : '–', 'con error', (idx?.counts.failed ?? 0) > 0]
        ]} />
      </Panel>
    </>
  )
}
