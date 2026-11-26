/**
 * Sector Relaciones (rumbo 257°, sección `relationships`): grafo 3D con las relaciones reales del
 * Workspace (los 60 elementos más conectados), selección por clic, conexiones del seleccionado con
 * «Quitar» (el backend pide confirmación: diálogo nativo de main) y los más conectados.
 * Crear relaciones se hace en Drakter: aquí solo se ve, se selecciona y se quita con aprobación.
 */
import { useContext, useEffect, useMemo, useRef, useState } from 'react'
import { useJarvisData } from '@/jarvis/data'
import { deleteRelationship } from '@/modules/relationships/api'
import { ENTITY_TYPE_LABEL, RELATIONSHIP_FALLBACK_LABEL, shortId, type EntityType, type RelationshipOut } from '@/modules/relationships/types'
import { useConfirmations } from '@/stores/confirmations'
import { Panel, WorldContext } from '../Panel'
import { createGraph, type GraphPart } from '../stage/parts'
import { D, FAR, NEAR } from '../stage/world'
import { Kpis, SnapNote, useAction, useVisorNav } from './common'

const TOPICS = ['relationships', 'entityNames'] as const
const S = 5
const MAX_NODES = 60
const LABELS = 10
const TYPE_COLOR: Record<EntityType, string> = {
  project: '#8be9ff', task: '#5fb4ff', habit: '#a8f0ff', subject: '#e9fcff', class_session: '#bfe9ff',
  calendar_event: '#7fd0ff', time_block: '#2f8cff', resource: '#3d8bff', folder: '#2a63c9'
}
const LEGEND: readonly EntityType[] = ['project', 'task', 'subject', 'habit', 'calendar_event', 'resource']

interface Node { readonly id: string; readonly type: EntityType; readonly name: string; readonly degree: number }

export function Relaciones() {
  const { relationships, entityNames } = useJarvisData(TOPICS)
  const { openInDrakter } = useVisorNav()
  const { busy, run } = useAction()
  const world = useContext(WorldContext)
  const rels = relationships.data ?? []
  const [sel, setSel] = useState<string | null>(null)

  const { nodes, edges, index, total } = useMemo(() => {
    const deg = new Map<string, { type: EntityType; n: number }>()
    for (const r of rels) {
      for (const [id, type] of [[r.source_id, r.source_type], [r.target_id, r.target_type]] as const) {
        const d = deg.get(id); if (d) d.n++; else deg.set(id, { type, n: 1 })
      }
    }
    const names = entityNames.data
    const list: Node[] = [...deg.entries()].sort((a, b) => b[1].n - a[1].n).slice(0, MAX_NODES)
      .map(([id, d]) => ({ id, type: d.type, degree: d.n, name: names?.get(id)?.name ?? `${ENTITY_TYPE_LABEL[d.type]} ${shortId(id)}` }))
    const index = new Map(list.map((n, i) => [n.id, i]))
    const edges: (readonly [number, number])[] = []
    for (const r of rels) { const a = index.get(r.source_id), b = index.get(r.target_id); if (a !== undefined && b !== undefined && a !== b) edges.push([a, b]) }
    return { nodes: list, edges, index, total: deg.size }
  }, [rels, entityNames.data])

  // 3D: el grafo se rehace solo cuando cambian nodos o aristas.
  const partRef = useRef<GraphPart | null>(null)
  useEffect(() => {
    if (!world) return
    const g = createGraph(world)
    partRef.current = g
    return () => { g.dispose(); partRef.current = null }
  }, [world])
  useEffect(() => {
    partRef.current?.setData(nodes.map((n) => ({ id: n.id, color: TYPE_COLOR[n.type], size: 20 + Math.min(n.degree, 8) * 4 })), edges)
  }, [nodes, edges, world])
  const selIdx = sel ? index.get(sel) ?? -1 : -1

  // Puntero: resaltado y selección en el grafo; etiquetas de los más conectados por ref (sin React por fotograma).
  const labelsRef = useRef<HTMLDivElement>(null)
  const hoverRef = useRef(-1)
  useEffect(() => {
    if (!world) return
    const g = (): GraphPart | null => partRef.current
    const onMove = (e: PointerEvent): void => {
      if (world.sector !== S) return
      const i = g()?.pick(e.clientX, e.clientY) ?? -1
      if (i !== hoverRef.current) { hoverRef.current = i; g()?.setHighlight(i, selIdx) }
    }
    const onClick = (e: MouseEvent): void => {
      if (world.sector !== S || (e.target as HTMLElement | null)?.closest?.('.jv-visor-pnl button, .jv-visor-pnl input, .jv-visor-glass button')) return
      const i = g()?.pick(e.clientX, e.clientY) ?? -1
      if (i >= 0) setSel(nodes[i]!.id)
    }
    g()?.setHighlight(hoverRef.current, selIdx)
    const els = labelsRef.current ? [...labelsRef.current.children] as HTMLElement[] : []
    let shown = true
    const offFrame = world.onFrame(() => {
      const box = labelsRef.current
      if (!box) return
      const on = world.near(S, 0.6)
      if (on !== shown) { shown = on; box.style.display = on ? '' : 'none' }
      if (!on) return
      els.forEach((el, k) => {
        const s = g()?.screenOf(k)
        if (!s) return
        const tr = s.visible ? `translate3d(${(s.x + 12).toFixed(1)}px,${(s.y - 8).toFixed(1)}px,0)` : 'translate3d(-999px,0,0)'
        if (el.dataset.tr !== tr) { el.dataset.tr = tr; el.style.transform = tr }
      })
    })
    addEventListener('pointermove', onMove, { passive: true })
    addEventListener('click', onClick)
    return () => { offFrame(); removeEventListener('pointermove', onMove); removeEventListener('click', onClick) }
  }, [world, nodes, selIdx])

  // Tras aprobar o rechazar una confirmación, se relee el grafo.
  const pending = useConfirmations().length
  const prevPending = useRef(pending)
  useEffect(() => { if (pending < prevPending.current) relationships.reload(); prevPending.current = pending }, [pending, relationships])

  const selected = selIdx >= 0 ? nodes[selIdx]! : null
  const links: { r: RelationshipOut; other: string; otherType: EntityType; out: boolean }[] = selected
    ? rels.filter((r) => r.source_id === selected.id || r.target_id === selected.id).map((r) => {
      const out = r.source_id === selected.id, other = out ? r.target_id : r.source_id, otherType = out ? r.target_type : r.source_type
      return { r, out, otherType, other: entityNames.data?.get(other)?.name ?? `${ENTITY_TYPE_LABEL[otherType]} ${shortId(other)}` }
    })
    : []
  const week = Date.now() - 7 * 86400000
  const types = new Set(rels.map((r) => r.relationship_type)).size

  return (
    <>
      <Panel sector={S} R={FAR} y={30} w={780} h={560} alpha={0.3} title="Grafo de relaciones" code="REL-01" className="graph">
        <SnapNote snap={relationships} empty="Aún no hay relaciones. Vincula tareas, proyectos o recursos en Drakter." isEmpty={rels.length === 0} />
        <div className="g-leg">{LEGEND.map((t) => <span key={t}><i style={{ background: TYPE_COLOR[t] }} />{ENTITY_TYPE_LABEL[t].toLowerCase()}</span>)}</div>
        {total > MAX_NODES && <p className="jv-visor-note small">Se muestran los {MAX_NODES} elementos más conectados.</p>}
        {!world && nodes.slice(0, 12).map((n) => <button type="button" key={n.id} className="jv-visor-deg" onClick={() => setSel(n.id)}><b>{n.name}</b><em>{n.degree}</em></button>)}
      </Panel>
      {world && (
        <div className="jv-visor-glabels" ref={labelsRef} aria-hidden="true">
          {nodes.slice(0, LABELS).map((n) => <span key={n.id} className={n.id === sel ? 'on' : ''}>{n.name}</span>)}
        </div>
      )}

      <Panel sector={S} dA={-26} R={NEAR} y={10} w={330} h={440} side title="Seleccionado" code="REL-02">
        {!selected ? <p className="jv-visor-note">Pulsa un nodo del grafo, o uno de «Más conectados», para ver sus conexiones.</p> : (
          <>
            <div className="jv-visor-gsel"><i style={{ background: TYPE_COLOR[selected.type] }} /><div><b>{selected.name}</b><small>{ENTITY_TYPE_LABEL[selected.type]}  ·  {links.length} conexiones</small></div></div>
            <div className="jv-visor-links">
              {links.slice(0, 8).map(({ r, other, otherType, out }) => (
                <div key={r.id} className="gs-l" data-lock={`${other}  ${ENTITY_TYPE_LABEL[otherType]}`}>
                  <i style={{ background: TYPE_COLOR[otherType] }} />
                  <span><small>{out ? RELATIONSHIP_FALLBACK_LABEL[r.relationship_type] : `← ${RELATIONSHIP_FALLBACK_LABEL[r.relationship_type]}`}</small>{other}</span>
                  <button type="button" className="ghost" disabled={busy !== null} data-lock={`Quitar relación con ${other} (pide confirmación)`} onClick={() => run(r.id, () => deleteRelationship(r.id), 'Relación quitada', relationships.reload)}>{busy === r.id ? '…' : 'Quitar'}</button>
                </div>
              ))}
              {links.length > 8 && <button type="button" className="link" onClick={() => openInDrakter('relationships')}>{links.length - 8} más en Drakter</button>}
            </div>
          </>
        )}
      </Panel>

      <Panel sector={S} dA={26} R={NEAR} y={10} w={330} h={440} side title="Más conectados" code="REL-03">
        <SnapNote snap={relationships} empty="Sin conexiones todavía." isEmpty={nodes.length === 0} />
        {nodes.slice(0, 8).map((n) => (
          <button type="button" key={n.id} className={`jv-visor-deg ${n.id === sel ? 'on' : ''}`} data-lock={`${n.name}  ${n.degree} enlaces`} onClick={() => setSel(n.id)}>
            <b>{n.name}</b><span>{ENTITY_TYPE_LABEL[n.type].toLowerCase()}</span><i style={{ ['--v' as string]: Math.min(1, n.degree / Math.max(1, nodes[0]!.degree)) }} /><em>{n.degree}</em>
          </button>
        ))}
      </Panel>

      <Panel sector={S} R={D - 110} y={-300} w={640} h={100} side title="Red" code="REL-04" className="kpis">
        <Kpis items={[
          [relationships.data ? total : '–', 'elementos'],
          [relationships.data ? (rels.length >= 1000 ? '1000+' : rels.length) : '–', 'relaciones'],
          [relationships.data ? types : '–', 'tipos usados'],
          [relationships.data ? rels.filter((r) => Date.parse(r.created_at) > week).length : '–', 'nuevas en 7 días'],
          [nodes[0]?.name ?? '–', 'más conectado']
        ]} />
      </Panel>
    </>
  )
}
