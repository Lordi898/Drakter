/**
 * Contenido del panel de detalle de cada sección: cifras, un gráfico SVG y la lista de elementos, todo
 * del modelo de vista real. Los textos del usuario van como texto de React (nunca HTML).
 */
import type { ReactNode } from 'react'
import { ENTITY_TYPE_LABEL } from '@/modules/relationships/types'
import { INDEX_LABELS, TYPE_LABELS } from '@/modules/storage/types'
import { hhmm, type HmEvent, type HoloSnapshot, type PickInfo, type SectionId } from '../model'
import { fmtSize, unindexed } from '../scene/stations/almacen'

export interface DetailRow {
  readonly key: string
  readonly label: string
  readonly meta: string
  readonly color: string
  /** Al pulsar la fila se selecciona como si se hubiera tocado el holograma. */
  readonly pick: PickInfo | null
}

export interface DetailContent {
  readonly no: string
  readonly title: string
  readonly sub: string
  readonly kpis: readonly (readonly [string, string])[]
  readonly chart: ReactNode
  readonly rows: readonly DetailRow[]
  /** Mensaje en lugar de la lista (cargando, sin datos, error). */
  readonly state: string | null
}

const hex = (n: number | null, fallback = '#6fd6ff'): string => (n === null ? fallback : '#' + n.toString(16).padStart(6, '0'))
const PRIO_COLOR = { urgent: '#ffb050', high: '#ffd08a', medium: '#58c8ff', low: '#2f86c8' } as const
const MAX_ROWS = 40

/** Barras horizontales que crecen (transform: scaleX). */
function HBars({ rows }: { readonly rows: readonly { readonly l: string; readonly v: number; readonly max: number; readonly c?: string }[] }) {
  const H = 84, rh = H / Math.max(1, rows.length)
  return (
    <svg viewBox={`0 0 460 ${H}`} preserveAspectRatio="none" aria-hidden="true">
      {rows.map((r, i) => {
        const y = i * rh + rh / 2, w = Math.max(0, 290 * Math.min(1, r.v / Math.max(1, r.max)))
        return (
          <g key={r.l}>
            <text x="0" y={y + 4} fill="rgba(150,205,235,.8)" fontSize="11">{r.l}</text>
            <rect x="140" y={y - 2.5} width="290" height="5" fill="rgba(111,214,255,.12)" />
            {w > 0 ? <rect className="grow" style={{ ['--d' as string]: `${0.3 + i * 0.08}s` }} x="140" y={y - 2.5} width={w} height="5" fill={r.c ?? '#6fd6ff'} /> : null}
            <text className="fade" x={Math.min(450, 146 + w)} y={y - 6} fill="#eafaff" fontSize="10">{r.v}</text>
          </g>
        )
      })}
    </svg>
  )
}

/** Serie con área (hábitos, carga diaria). */
function Spark({ vals, max, left, right }: { readonly vals: readonly number[]; readonly max: number; readonly left: string; readonly right: string }) {
  const W = 460, H = 66, step = W / Math.max(1, vals.length - 1)
  const pts = vals.map((v, i) => `${(i * step).toFixed(1)},${(H - (v / Math.max(1, max)) * (H - 8)).toFixed(1)}`).join(' ')
  const last = vals.length - 1
  return (
    <svg viewBox={`0 0 ${W} ${H + 16}`} preserveAspectRatio="none" aria-hidden="true">
      {[0.25, 0.5, 0.75].map((f) => <line key={f} x1="0" x2={W} y1={H * f} y2={H * f} stroke="rgba(111,214,255,.1)" />)}
      <polygon className="fade" points={`0,${H} ${pts} ${W},${H}`} fill="rgba(111,214,255,.16)" />
      <polyline className="fade" style={{ ['--d' as string]: '0.25s' }} points={pts} fill="none" stroke="#bff2ff" strokeWidth="1.6" />
      {last >= 0 ? <circle cx={last * step} cy={H - ((vals[last] ?? 0) / Math.max(1, max)) * (H - 8)} r="3.5" fill="#fff" /> : null}
      <text x="0" y={H + 13} fill="rgba(150,205,235,.7)" fontSize="10">{left}</text>
      <text x={W} y={H + 13} textAnchor="end" fill="rgba(150,205,235,.7)" fontSize="10">{right}</text>
    </svg>
  )
}

/** Franja horaria del día con los eventos y la hora actual. */
function DayLine({ events, now }: { readonly events: readonly HmEvent[]; readonly now: number }) {
  const x = (h: number): number => ((Math.max(7, Math.min(24, h)) - 7) / 17) * 460
  return (
    <svg viewBox="0 0 460 70" preserveAspectRatio="none" aria-hidden="true">
      {Array.from({ length: 18 }, (_, i) => (
        <g key={i}>
          <line x1={x(7 + i)} x2={x(7 + i)} y1={i % 3 ? 44 : 38} y2="50" stroke="rgba(111,214,255,.35)" />
          {i % 3 === 0 ? <text x={x(7 + i)} y="64" fill="rgba(150,205,235,.7)" fontSize="10" textAnchor="middle">{7 + i}</text> : null}
        </g>
      ))}
      {events.filter((e) => !e.allDay).map((e, i) => (
        <rect key={e.id} className="grow" style={{ ['--d' as string]: `${0.3 + i * 0.1}s` }} x={x(e.start)} y={12 + (i % 2) * 12} width={Math.max(2, x(e.end) - x(e.start))} height="9" fill={hex(e.color, '#6cf2d6')} fillOpacity={e.end <= now ? 0.3 : 0.75} />
      ))}
      <line x1={x(now)} x2={x(now)} y1="4" y2="52" stroke="#fff" strokeWidth="1.5" />
      <circle cx={x(now)} cy="4" r="3" fill="#fff" />
    </svg>
  )
}

function loadState(load: 'loading' | 'ready' | 'error', empty: boolean, emptyText: string): string | null {
  if (load === 'loading') return 'Cargando datos del Workspace…'
  if (load === 'error') return 'No se pudieron leer los datos. Se reintentará al recuperar el enlace.'
  return empty ? emptyText : null
}

const evPick = (prefix: string, e: HmEvent, day: string): PickInfo => ({
  key: prefix + e.id,
  title: e.title,
  sub: `${day}${e.allDay ? 'todo el día' : `${hhmm(e.start)}–${hhmm(e.end)}`}`,
  lines: e.place ? [e.place] : [],
  ref: { kind: 'event', sourceType: e.sourceType, id: e.sourceId }
})

export function detailFor(id: SectionId, s: HoloSnapshot): DetailContent {
  switch (id) {
    case 'hoy': {
      const left = s.today.events.filter((e) => e.end > s.nowHours)
      return {
        no: '01', title: 'Hoy', sub: s.today.label,
        kpis: [[String(left.length), 'eventos por delante'], [String(s.today.dueToday - s.today.doneToday), 'tareas para hoy'], [String(s.today.doneToday), 'hechas hoy']],
        chart: <DayLine events={s.today.events} now={s.nowHours} />,
        rows: s.today.events.map((e) => ({ key: e.id, label: e.title, meta: e.allDay ? 'todo el día' : `${hhmm(e.start)}–${hhmm(e.end)}`, color: hex(e.color, '#6cf2d6'), pick: evPick('hoy:', e, '') })),
        state: loadState(s.today.load, s.today.events.length === 0, 'Hoy no hay nada en la agenda.')
      }
    }
    case 'calendario': {
      const per = s.calendar.days.map((_, i) => s.calendar.events.filter((e) => e.day === i).length)
      const upcoming = s.calendar.events.filter((e) => e.day > 0 || e.end > s.nowHours).slice(0, MAX_ROWS)
      return {
        no: '02', title: 'Calendario', sub: `${s.calendar.days[0] ?? ''} – ${s.calendar.days[s.calendar.days.length - 1] ?? ''} · ${s.timezone}`,
        kpis: [[String(s.calendar.events.length), 'en la semana'], [String(s.calendar.events.filter((e) => e.kind === 'clase').length), 'clases'], [String(s.calendar.subjects.length), 'asignaturas']],
        chart: <Spark vals={per} max={Math.max(4, ...per)} left={s.calendar.days[0] ?? ''} right={s.calendar.days[s.calendar.days.length - 1] ?? ''} />,
        rows: upcoming.map((e) => ({ key: e.id, label: e.title, meta: `${s.calendar.days[e.day] ?? ''} · ${e.allDay ? 'todo el día' : hhmm(e.start)}`, color: hex(e.color, e.kind === 'clase' ? '#8fb4ff' : '#6cf2d6'), pick: evPick('cal:', e, `${s.calendar.days[e.day] ?? ''} · `) })),
        state: loadState(s.calendar.load, upcoming.length === 0, 'No hay nada en los próximos días.')
      }
    }
    case 'tareas': {
      const items = s.tasks.items
      const open = items.filter((t) => t.column !== 2)
      const rank = { urgent: 0, high: 1, medium: 2, low: 3 } as const
      const sorted = [...open].sort((a, b) => Number(b.overdue) - Number(a.overdue) || rank[a.priority] - rank[b.priority])
      const by = (pr: keyof typeof rank): number => open.filter((t) => t.priority === pr).length
      return {
        no: '03', title: 'Tareas', sub: 'apiladas por estado · altura = estimación',
        kpis: [[String(items.filter((t) => t.column === 0).length), 'pendientes'], [String(items.filter((t) => t.column === 1).length), 'en curso'], [String(open.filter((t) => t.overdue).length), 'vencidas']],
        chart: <HBars rows={[{ l: 'Urgente', v: by('urgent'), max: Math.max(6, open.length), c: PRIO_COLOR.urgent }, { l: 'Alta', v: by('high'), max: Math.max(6, open.length), c: PRIO_COLOR.high }, { l: 'Media', v: by('medium'), max: Math.max(6, open.length), c: PRIO_COLOR.medium }, { l: 'Baja', v: by('low'), max: Math.max(6, open.length), c: PRIO_COLOR.low }]} />,
        rows: sorted.slice(0, MAX_ROWS).map((t) => ({ key: t.id, label: t.title, meta: [t.project, t.due].filter(Boolean).join(' · ') || '—', color: t.overdue ? '#ff7a5c' : PRIO_COLOR[t.priority], pick: { key: 'task:' + t.id, title: t.title, sub: t.project ?? 'sin proyecto', lines: t.due ? [`vence ${t.due}`] : [], ref: { kind: 'task', id: t.id } } })),
        state: loadState(s.tasks.load, open.length === 0, 'No hay tareas abiertas.')
      }
    }
    case 'proyectos': {
      const items = s.projects.items
      const next = items.filter((x) => x.due).map((x) => x.due!)[0]
      return {
        no: '04', title: 'Proyectos', sub: 'maquetas · lo sólido está hecho, los andamios quedan',
        kpis: [[String(items.length), 'activos'], [`${items.reduce((a, x) => a + x.completed, 0)}/${items.reduce((a, x) => a + x.total, 0)}`, 'tareas hechas'], [next ?? '—', 'próximo objetivo']],
        chart: <HBars rows={items.slice(0, 5).map((x) => ({ l: x.name.length > 18 ? x.name.slice(0, 17) + '…' : x.name, v: Math.round(x.progress * 100), max: 100 }))} />,
        rows: items.slice(0, MAX_ROWS).map((x) => ({ key: x.id, label: x.name, meta: `${Math.round(x.progress * 100)} %${x.due ? ` · ${x.due}` : ''}`, color: x.overdue ? '#ffb050' : '#67d8ff', pick: { key: 'proj:' + x.id, title: x.name, sub: `${Math.round(x.progress * 100)} %`, lines: [`${x.completed}/${x.total} tareas hechas`], ref: { kind: 'project', id: x.id } } })),
        state: loadState(s.projects.load, items.length === 0, 'No hay proyectos activos.')
      }
    }
    case 'habitos': {
      const items = s.habits.items
      const days = items[0]?.days.length ?? 28
      const rate = Array.from({ length: days }, (_, d) => items.filter((h) => h.days[d] === 'done').length)
      const scheduled = items.reduce((a, h) => a + h.days.filter((d) => d !== null).length, 0)
      const done = items.reduce((a, h) => a + h.days.filter((d) => d === 'done').length, 0)
      return {
        no: '05', title: 'Hábitos', sub: `${days} días · cada vuelta de la hélice es un hábito`,
        kpis: [[String(items.filter((h) => h.todayScheduled && !h.todayDone).length), 'por marcar hoy'], [`${Math.max(0, ...items.map((h) => h.streak))} d`, 'mejor racha viva'], [scheduled ? `${Math.round((done / scheduled) * 100)} %` : '—', 'cumplimiento']],
        chart: <Spark vals={rate} max={Math.max(1, items.length)} left={`hace ${days} días`} right="hoy" />,
        rows: items.map((h) => ({ key: h.id, label: h.name, meta: `${h.todayScheduled ? (h.todayDone ? 'hecho hoy' : 'pendiente hoy') : 'hoy no toca'} · racha ${h.streak}`, color: h.todayScheduled && !h.todayDone ? '#ffb050' : '#6fd6ff', pick: { key: `hab:${h.id}:today`, title: h.name, sub: h.todayDone ? 'hoy · cumplido' : h.todayScheduled ? 'hoy · pendiente' : 'hoy no toca', lines: [`Racha actual ${h.streak} · mejor ${h.best}`], ref: { kind: 'habit', id: h.id, day: 0 } } })),
        state: loadState(s.habits.load, items.length === 0, 'No hay hábitos activos.')
      }
    }
    case 'relaciones': {
      const deg = new Map<string, number>()
      for (const [a, b] of s.graph.edges) {
        deg.set(a, (deg.get(a) ?? 0) + 1)
        deg.set(b, (deg.get(b) ?? 0) + 1)
      }
      const kinds = [...new Set(s.graph.nodes.map((n) => n.kind))]
      const top = [...s.graph.nodes].sort((a, b) => (deg.get(b.id) ?? 0) - (deg.get(a.id) ?? 0)).slice(0, MAX_ROWS)
      return {
        no: '06', title: 'Relaciones', sub: 'red viva · los pulsos recorren los vínculos',
        kpis: [[String(s.graph.nodes.length), 'entidades'], [String(s.graph.edges.length), 'relaciones'], [String(kinds.length), 'tipos']],
        chart: <HBars rows={kinds.slice(0, 5).map((k) => ({ l: ENTITY_TYPE_LABEL[k], v: s.graph.nodes.filter((n) => n.kind === k).length, max: Math.max(5, s.graph.nodes.length) }))} />,
        rows: top.map((n) => ({ key: n.id, label: n.label, meta: `${ENTITY_TYPE_LABEL[n.kind].toLowerCase()} · ${deg.get(n.id) ?? 0} vínculos`, color: '#7ff0d8', pick: { key: 'g:' + n.id, title: n.label, sub: ENTITY_TYPE_LABEL[n.kind].toLowerCase(), lines: [], ref: { kind: 'entity', id: n.id, entityType: n.kind } } })),
        state: loadState(s.graph.load, s.graph.nodes.length === 0, 'Aún no hay relaciones entre entidades.')
      }
    }
    case 'almacen': {
      const items = s.files.items
      const types = [...new Set(items.map((f) => f.type))]
      const total = items.reduce((a, f) => a + (f.sizeBytes ?? 0), 0)
      return {
        no: '07', title: 'Almacén', sub: 'estantería de archivos · altura = tamaño · ámbar = sin indexar',
        kpis: [[String(s.files.total), 'recursos recientes'], [fmtSize(total), 'en disco'], [String(s.files.pending), 'por indexar']],
        chart: <HBars rows={types.slice(0, 5).map((t) => ({ l: TYPE_LABELS[t], v: items.filter((f) => f.type === t).length, max: Math.max(5, items.length) }))} />,
        rows: items.slice(0, MAX_ROWS).map((f) => ({ key: f.id, label: f.title, meta: `${f.folder ?? 'sin carpeta'} · ${fmtSize(f.sizeBytes)}`, color: unindexed(f) ? '#ffb050' : '#7fdcff', pick: { key: 'res:' + f.id, title: f.title, sub: `${f.folder ?? 'sin carpeta'} · ${fmtSize(f.sizeBytes)}`, lines: [`${TYPE_LABELS[f.type]} · ${INDEX_LABELS[f.index]}`], ref: { kind: 'resource', id: f.id } } })),
        state: loadState(s.files.load, items.length === 0, 'El almacén está vacío.')
      }
    }
  }
}
