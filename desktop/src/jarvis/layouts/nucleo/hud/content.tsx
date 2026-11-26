/**
 * Contenido de los cuatro paneles radiales de cada sección, con datos reales del modelo. Todo texto
 * de datos se pinta como texto de React (nunca HTML). Las acciones las ejecuta `index.tsx` con la API.
 */
import type { CSSProperties, ReactNode } from 'react'
import type { EntityType } from '@/modules/relationships/types'
import { CSS, type ColorName } from '../gl/kit'
import { ENTITY_ES, REL_ES, dayNum, dow3, hm, indexLabel, type NucleoModel, type VTask } from '../model'
import type { Mod, ModuleId } from '../modules/base'
import { TYPE_COL, nearOf, type RelState } from '../modules/relaciones'
import type { AlmState } from '../modules/almacen'

export type Slot = 'lt' | 'lb' | 'rt' | 'rb'
export interface PanelDef { readonly slot: Slot; readonly title: string; readonly meta?: string; readonly hero?: { big: string; small: string; tone?: 'soon' | 'late' }; readonly body: ReactNode }
export interface Acts {
  toggleTask(t: VTask): void
  toggleHabit(id: string): void
  select(id: ModuleId, num: number): void
  filter(type: EntityType | null): void
  say(text: string): void
  busy: ReadonlySet<string>
}

const v = (o: Record<string, string | number>): CSSProperties => o as CSSProperties
const Dot = ({ c }: { c: ColorName | string }) => <i className="dot" style={v({ '--c': CSS[c as ColorName] ?? c })} />
const Bar = ({ p, c = 'cyan', n }: { p: number; c?: ColorName; n?: ReactNode }) => (
  <><span className="bar" style={v({ '--p': Math.max(0, Math.min(1, p)), '--c': CSS[c] })}><i /></span>{n !== undefined ? <b className="num">{n}</b> : null}</>
)
const Row = ({ a, b, cls = '', onClick, lock, on }: { a: ReactNode; b?: ReactNode; cls?: string; onClick?: () => void; lock?: string; on?: boolean }) =>
  onClick ? (
    <li><button type="button" className={`row ${cls} ${on ? 'on' : ''}`} onClick={onClick} data-lock={lock}><span>{a}</span><span className="r">{b}</span></button></li>
  ) : (
    <li className={`row ${cls} ${on ? 'on' : ''}`} data-lock={lock}><span>{a}</span><span className="r">{b}</span></li>
  )
const Kpi = ({ n, l }: { n: ReactNode; l: string }) => <div className="kpi"><b>{n}</b><span>{l}</span></div>
const Loading = () => <p className="sayp dim">Cargando…</p>
const mins = (h: number) => { const m = Math.max(0, Math.round(h * 60)); return m >= 60 ? `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, '0')}` : `${m} min` }

export function panelsFor(id: ModuleId, model: NucleoModel, m: Mod, acts: Acts): readonly PanelDef[] {
  switch (id) {
    case 'hoy': return hoyPanels(model, acts)
    case 'tareas': return tareasPanels(model, m, acts)
    case 'habitos': return habitosPanels(model, acts)
    case 'calendario': return calendarioPanels(model, m, acts)
    case 'relaciones': return relPanels(m as Mod<RelState>, acts)
    case 'almacen': return almPanels(model, m as Mod<AlmState>, acts)
  }
}

function hoyPanels(model: NucleoModel, acts: Acts): PanelDef[] {
  const h = model.nowHour, ev = model.todayEvents, tt = model.todayTasks
  const cur = ev?.find((e) => e.start <= h && e.end > h), next = ev?.find((e) => e.start > h)
  const hero = !ev ? undefined : cur ? { big: mins(cur.end - h), small: `quedan de ${cur.title}` } : next ? { big: mins(next.start - h), small: `para ${next.title}`, tone: next.start - h < 0.5 ? ('soon' as const) : undefined } : { big: 'Libre', small: 'no queda nada en la agenda' }
  const done = tt?.filter((t) => t.done).length ?? 0, late = tt?.filter((t) => t.tone === 'late').length ?? 0
  return [
    { slot: 'lt', title: 'Ahora y siguiente', meta: hm(h), hero, body: ev ? (
      <>
        <ul className="rows">{ev.filter((e) => e.end > h && e !== cur).slice(0, 3).map((e) => <Row key={e.id} a={<><Dot c={e.col} />{e.title}</>} b={hm(e.start)} lock={`${e.title} · ${hm(e.start)}`} />)}</ul>
        <p className="note">{next ? `Siguiente a las ${hm(next.start)}` : 'Agenda del día completada'} · día al {Math.round((h / 24) * 100)} %</p>
      </>
    ) : <Loading /> },
    { slot: 'lb', title: 'Tareas de hoy', meta: tt ? `${done} de ${tt.length}` : undefined, body: tt ? (tt.length ? (
      <ul className="rows chk">{tt.map((t) => <Row key={t.id} cls={`${t.done ? 'done' : ''} ${t.tone}`} a={<><i className="box" />{t.title}</>} b={t.dueText} lock={`${t.done ? 'Reabrir' : 'Completar'}: ${t.title}`} onClick={acts.busy.has(t.id) ? undefined : () => acts.toggleTask(t)} />)}</ul>
    ) : <p className="sayp dim">Nada vence hoy.</p>) : <Loading /> },
    { slot: 'rt', title: 'Parte de Drakter', meta: 'a demanda', body: (
      <>
        <p className="sayp">{ev && tt ? `${ev.length} en la agenda, ${tt.length - done} tarea${tt.length - done === 1 ? '' : 's'} pendiente${tt.length - done === 1 ? '' : 's'} para hoy${late ? `, ${late} ya vencida${late > 1 ? 's' : ''}` : ''}.` : 'Reuniendo el día…'}</p>
        <p className="sayp dim">Drakter puede repasarlo contigo y proponerte un orden.</p>
        <button type="button" className="btn" data-lock="Pedir el parte del día" onClick={() => acts.say('Dame el parte de hoy: agenda, tareas que vencen y qué me recomiendas priorizar.')}>Pídeme el parte del día</button>
      </>
    ) },
    { slot: 'rb', title: 'El día en cifras', meta: model.todayKey, body: (
      <div className="kpis">
        <Kpi n={ev ? ev.length : '—'} l="en la agenda" />
        <Kpi n={tt ? `${done}/${tt.length}` : '—'} l="tareas de hoy" />
        <Kpi n={model.habits ? `${model.habits.filter((x) => x.todayDone).length}/${model.habits.filter((x) => x.todayScheduled).length}` : '—'} l="hábitos" />
        <Kpi n={late} l="vencidas" />
      </div>
    ) }
  ]
}

function tareasPanels(model: NucleoModel, m: Mod, acts: Acts): PanelDef[] {
  const ts = model.tasks, sel = ts?.find((t) => t.num === m.sel)
  const soon = (ts ?? []).filter((t) => !t.done && t.dueDays !== null && t.dueDays <= 3).sort((a, b) => (a.dueDays ?? 0) - (b.dueDays ?? 0)).slice(0, 6)
  const load = Array.from({ length: 7 }, (_, d) => model.dueStrip?.[d] ?? 0), mx = Math.max(1, ...load)
  const open = ts?.filter((t) => !t.done).length ?? 0, late = ts?.filter((t) => t.tone === 'late').length ?? 0
  return [
    { slot: 'lt', title: 'Proyectos', meta: model.projects ? `${model.projects.length} activos` : undefined, hero: ts ? { big: String(open), small: `tareas abiertas${late ? ` · ${late} vencida${late > 1 ? 's' : ''}` : ''}`, tone: late ? 'late' : undefined } : undefined, body: model.projects ? (
      <ul className="rows">{model.projects.map((p) => <Row key={p.id} a={<><Dot c={p.col} />{p.name}</>} b={<Bar p={p.percent} c={p.col} n={Math.round(p.percent * 100)} />} lock={`${p.name} · ${Math.round(p.percent * 100)} %`}
        onClick={() => { const t = ts?.find((x) => x.projectId === p.id && !x.done); if (t) acts.select('tareas', t.num) }} />)}</ul>
    ) : <Loading /> },
    { slot: 'lb', title: 'Vencen pronto', meta: `${soon.length} tareas`, body: soon.length ? (
      <ul className="rows">{soon.map((t) => <Row key={t.id} cls={t.tone} on={t.num === m.sel} a={<><i className={`pr p${t.prio}`} />{t.title}</>} b={t.dueText} lock={t.title} onClick={() => acts.select('tareas', t.num)} />)}</ul>
    ) : <p className="sayp dim">Nada vence en los próximos tres días.</p> },
    { slot: 'rt', title: 'Tarea seleccionada', meta: sel?.projectName ?? '—', body: sel ? (
      <>
        <p className="lead">{sel.title}</p>
        <p className={`sub ${sel.tone}`}>{sel.dueText} · prioridad {['baja', 'alta', 'urgente'][sel.prio - 1]}</p>
        <ul className="rows"><Row a="Proyecto" b={sel.projectName ?? 'sin proyecto'} /></ul>
        <button type="button" className="btn" disabled={acts.busy.has(sel.id)} onClick={() => acts.toggleTask(sel)}>{sel.done ? 'Reabrir la tarea' : 'Marcar como hecha'}</button>
      </>
    ) : <p className="sayp dim">Toca un satélite para ver la tarea. Los rombos ámbar vencen hoy o mañana; los rojos ya vencieron.</p> },
    { slot: 'rb', title: 'Carga de la semana', meta: 'vencen por día', body: (
      <div className="cols">{load.map((n, i) => <div key={i} className={`cb ${i === 0 ? 'hi' : ''}`} style={v({ '--p': n / mx })}><b>{n || ''}</b><i /><span>{dow3(model.todayDow, i)}</span></div>)}</div>
    ) }
  ]
}

function habitosPanels(model: NucleoModel, acts: Acts): PanelDef[] {
  const hs = model.habits
  if (!hs) return [{ slot: 'lt', title: 'Hoy', body: <Loading /> }]
  const withHist = hs.filter((h) => h.days), rates = withHist.map((h) => h.rate).filter((x): x is number => x !== null)
  const avg = rates.length ? rates.reduce((a, b) => a + b, 0) / rates.length : null
  const byDow = Array.from({ length: 7 }, (_, w) => {
    let n = 0, k = 0
    for (const h of withHist) h.days!.forEach((d, i) => { if (d === null) return; if ((model.todayDow - (27 - i) + 35) % 7 === w) { k++; if (d) n++ } })
    return k ? n / k : null
  })
  const valid = byDow.filter((x): x is number => x !== null), best = valid.length ? byDow.indexOf(Math.max(...valid)) : -1, worst = valid.length ? byDow.indexOf(Math.min(...valid)) : -1
  const sched = hs.filter((h) => h.todayScheduled)
  return [
    { slot: 'lt', title: 'Hoy', meta: `${sched.filter((h) => h.todayDone).length} de ${sched.length}`, hero: { big: `${sched.filter((h) => h.todayDone).length}/${sched.length}`, small: 'hábitos hechos hoy' }, body: (
      <ul className="rows chk">{sched.map((h) => <Row key={h.id} cls={h.todayDone ? 'done' : ''} a={<><i className="box" />{h.name}</>} b={h.streak !== null ? `racha ${h.streak}` : ''} lock={`${h.todayDone ? 'Desmarcar' : 'Marcar'}: ${h.name}`} onClick={acts.busy.has(h.id) ? undefined : () => acts.toggleHabit(h.id)} />)}
        {!sched.length ? <li className="note">Hoy no toca ningún hábito.</li> : null}</ul>
    ) },
    { slot: 'lb', title: 'Rachas', meta: 'días seguidos', body: withHist.length ? (
      <ul className="rows">{[...withHist].sort((a, b) => (b.streak ?? 0) - (a.streak ?? 0)).map((h) => <Row key={h.id} a={<><Dot c={h.col} />{h.name}</>} b={<Bar p={(h.streak ?? 0) / 14} c={h.col} n={h.streak ?? 0} />} />)}</ul>
    ) : <p className="sayp dim">Sin historial todavía.</p> },
    { slot: 'rt', title: 'Constancia', meta: '28 días', body: avg !== null ? (
      <><div className="kpis one"><Kpi n={`${Math.round(avg * 100)} %`} l="de los días que tocaba" /></div>
        <ul className="rows">{withHist.map((h) => <Row key={h.id} a={<><Dot c={h.col} />{h.name}</>} b={<Bar p={h.rate ?? 0} c={h.col} n={h.rate !== null ? Math.round(h.rate * 100) : '—'} />} />)}</ul></>
    ) : <p className="sayp dim">Sin historial todavía.</p> },
    { slot: 'rb', title: 'Por día de la semana', meta: best >= 0 ? `mejor: ${dow3(0, best)}` : undefined, body: valid.length ? (
      <><div className="cols">{byDow.map((x, i) => <div key={i} className={`cb ${i === best ? 'hi' : i === worst ? 'lo' : ''}`} style={v({ '--p': x === null ? 0 : 0.18 + (0.82 * (x - (byDow[worst] ?? 0))) / Math.max(0.01, (byDow[best] ?? 1) - (byDow[worst] ?? 0)) })}><b>{x === null ? '' : Math.round(x * 100)}</b><i /><span>{dow3(0, i)}</span></div>)}</div>
        {worst >= 0 && worst !== best ? <p className="note">El {dow3(0, worst)} es tu día más flojo: {Math.round((byDow[worst] ?? 0) * 100)} %.</p> : null}</>
    ) : <p className="sayp dim">Sin historial todavía.</p> }
  ]
}

function calendarioPanels(model: NucleoModel, m: Mod, acts: Acts): PanelDef[] {
  const wk = model.week, h = model.nowHour, sel = wk?.find((e) => e.num === m.sel)
  const up = (wk ?? []).filter((e) => e.day > 0 || e.start > h).sort((a, b) => a.day - b.day || a.start - b.start).slice(0, 5)
  const perDay = Array.from({ length: 7 }, (_, d) => (wk ?? []).filter((e) => e.day === d && !e.allDay).reduce((a, e) => a + (e.end - e.start), 0)), mx = Math.max(1, ...perDay)
  const due = (model.tasks ?? []).filter((t) => !t.done && t.dueDays !== null && t.dueDays >= 0 && t.dueDays < 35).sort((a, b) => (a.dueDays ?? 0) - (b.dueDays ?? 0)).slice(0, 5)
  const nextDue = model.dueStrip?.findIndex((x) => x > 0) ?? -1
  return [
    { slot: 'lt', title: sel ? 'Evento' : 'Próximos', meta: sel ? dow3(model.todayDow, sel.day) : '7 días', hero: !sel && nextDue >= 0 ? { big: nextDue === 0 ? 'Hoy' : nextDue === 1 ? '1 día' : `${nextDue} días`, small: 'para el próximo vencimiento', tone: nextDue <= 1 ? 'soon' : undefined } : undefined, body: sel ? (
      <><p className="lead">{sel.title}</p><p className="sub">{dow3(model.todayDow, sel.day)} {dayNum(model.todayKey, sel.day)} · {sel.allDay ? 'todo el día' : `${hm(sel.start)} – ${hm(sel.end)}`}</p>
        <ul className="rows">{sel.subject ? <Row a="Asignatura" b={sel.subject} /> : null}{sel.room ? <Row a="Lugar" b={sel.room} /> : null}<Row a="Tipo" b={sel.kind} /></ul></>
    ) : wk ? (
      <ul className="rows">{up.map((e) => <Row key={e.id} a={<><Dot c={e.col} />{e.title}</>} b={`${e.day === 0 ? 'hoy' : dow3(model.todayDow, e.day)} ${e.allDay ? '' : hm(e.start)}`} onClick={() => acts.select('calendario', e.num)} lock={e.title} />)}
        {!up.length ? <li className="note">Nada más en los próximos siete días.</li> : null}</ul>
    ) : <Loading /> },
    { slot: 'lb', title: 'Asignaturas', meta: 'horas esta semana', body: model.subjects ? (model.subjects.length ? (
      <ul className="rows">{model.subjects.map((s) => <Row key={s.id} a={<><Dot c={s.col} />{s.name}</>} b={<Bar p={s.weekHours / Math.max(1, ...model.subjects!.map((x) => x.weekHours))} c={s.col} n={`${String(Math.round(s.weekHours * 10) / 10).replace('.', ',')} h`} />} />)}</ul>
    ) : <p className="sayp dim">Sin asignaturas.</p>) : <Loading /> },
    { slot: 'rt', title: 'Vencimientos', meta: '35 días', body: due.length ? (
      <ul className="rows">{due.map((t) => <Row key={t.id} cls={t.tone} a={<><Dot c={t.tone === 'soon' || t.tone === 'late' ? 'amber' : 'cyan'} />{t.title}</>} b={t.dueText} lock={t.title} />)}</ul>
    ) : <p className="sayp dim">Ninguna tarea con fecha en las próximas cinco semanas.</p> },
    { slot: 'rb', title: 'Horas ocupadas', meta: 'por día', body: (
      <div className="cols">{perDay.map((x, i) => <div key={i} className={`cb ${i === 0 ? 'hi' : ''}`} style={v({ '--p': x / mx })}><b>{x ? String(Math.round(x * 10) / 10).replace('.', ',') : ''}</b><i /><span>{dow3(model.todayDow, i)}</span></div>)}</div>
    ) }
  ]
}

function relPanels(m: Mod<RelState>, acts: Acts): PanelDef[] {
  const s = m.s, nodes = s.nodes, sel = nodes.find((n) => n.num === m.sel)
  const rels = sel ? s.edges.filter((e) => nodes[e.a]!.num === sel.num || nodes[e.b]!.num === sel.num) : []
  const byRel = new Map<string, number>()
  for (const e of s.edges) byRel.set(e.rel, (byRel.get(e.rel) ?? 0) + 1)
  const relMax = Math.max(1, ...byRel.values())
  const hubs = [...nodes].sort((a, b) => b.deg - a.deg).slice(0, 6)
  const types = [...new Set(nodes.map((n) => n.type))]
  const near = sel ? nearOf(s, sel.num) : null
  return [
    { slot: 'lt', title: sel ? ENTITY_ES[sel.type] : 'Entidad', meta: sel ? `${sel.deg} vínculos` : 'ninguna fijada', hero: !sel ? { big: String(nodes.length), small: `entidades · ${s.edges.length} vínculos` } : undefined, body: sel ? (
      <><p className="lead">{sel.name}</p>
        <ul className="rows">{rels.slice(0, 6).map((e, i) => { const out = nodes[e.a]!.num === sel.num, o = nodes[out ? e.b : e.a]!; return <Row key={i} a={<><Dot c={TYPE_COL[o.type]} />{o.name}</>} b={out ? REL_ES[e.rel as keyof typeof REL_ES] : `← ${REL_ES[e.rel as keyof typeof REL_ES]}`} onClick={() => acts.select('relaciones', o.num)} lock={o.name} /> })}</ul>
        {near ? <p className="note">{near.size - 1} entidades a un salto.</p> : null}</>
    ) : <p className="sayp dim">Pasa por una entidad para iluminar sus vínculos y tócala para fijarla. Cada línea es una fila de la tabla común de relaciones.</p> },
    { slot: 'lb', title: 'Tipos de vínculo', meta: `${s.edges.length} en total`, body: (
      <ul className="rows">{[...byRel.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6).map(([k, n]) => <Row key={k} a={REL_ES[k as keyof typeof REL_ES] ?? k} b={<Bar p={n / relMax} n={n} />} />)}</ul>
    ) },
    { slot: 'rt', title: 'Más conectadas', meta: 'nodos centrales', body: (
      <ul className="rows">{hubs.map((n) => <Row key={n.id} on={n.num === m.sel} a={<><Dot c={TYPE_COL[n.type]} />{n.name}</>} b={<Bar p={n.deg / Math.max(1, hubs[0]?.deg ?? 1)} c={TYPE_COL[n.type]} n={n.deg} />} onClick={() => acts.select('relaciones', n.num)} lock={n.name} />)}</ul>
    ) },
    { slot: 'rb', title: 'Leyenda', meta: s.filter ? 'filtrando' : 'toca para filtrar', body: (
      <ul className="rows two">{types.map((t) => <Row key={t} on={s.filter === t} a={<><Dot c={TYPE_COL[t]} />{ENTITY_ES[t]}</>} b={nodes.filter((n) => n.type === t).length} onClick={() => acts.filter(s.filter === t ? null : t)} lock={`Filtrar: ${ENTITY_ES[t]}`} />)}</ul>
    ) }
  ]
}

function almPanels(model: NucleoModel, m: Mod<AlmState>, acts: Acts): PanelDef[] {
  const st = model.store
  if (!st) return [{ slot: 'lt', title: 'Índice', body: <Loading /> }]
  const g = st.groups.find((x) => x.num === m.s.group) ?? st.groups[0]
  const inG = g && st.byFolder ? st.recent.filter((r) => r.folderId === g.key) : []
  return [
    { slot: 'lt', title: 'Índice', meta: `muestra de ${st.sample} recientes`, hero: { big: st.sample ? `${Math.round((st.indexed / st.sample) * 100)} %` : '—', small: `indexado${st.pending ? ` · ${st.pending} pendientes` : ''}` }, body: (
      <><div className="kpis"><Kpi n={st.total} l={st.byFolder ? 'en carpetas' : 'recursos recientes'} /><Kpi n={st.groups.length} l={st.byFolder ? 'carpetas' : 'tipos'} /></div>
        <ul className="rows">{st.index.map((x) => <Row key={x.key} cls={x.key === 'failed' ? 'late' : x.key === 'pending' ? 'soon' : ''} a={x.name} b={<Bar p={x.count / Math.max(1, st.sample)} c={x.key === 'failed' ? 'red' : x.key === 'pending' ? 'amber' : 'cyan'} n={x.count} />} />)}</ul></>
    ) },
    { slot: 'lb', title: 'Recientes', meta: 'últimos cambios', body: st.recent.length ? (
      <ul className="rows">{st.recent.slice(0, 6).map((r) => <Row key={r.id} cls={r.status === 'failed' ? 'late' : r.status === 'pending' ? 'soon' : ''} a={<><i className="tag">{r.type.slice(0, 3)}</i>{r.title}</>} b={r.status === 'indexed' ? r.when : indexLabel(r.status)} lock={r.title} />)}</ul>
    ) : <p className="sayp dim">Sin recursos.</p> },
    { slot: 'rt', title: g?.name ?? 'Carpeta', meta: g ? `${g.count} recursos` : undefined, body: g ? (g.kids.length ? (
      <ul className="rows">{g.kids.map((k) => <Row key={k.key} a={k.name} b={<Bar p={k.count / Math.max(1, g.count)} c={k.key === 'failed' ? 'red' : k.key === 'pending' ? 'amber' : g.col} n={k.count} />} />)}</ul>
    ) : inG.length ? (
      <ul className="rows">{inG.slice(0, 5).map((r) => <Row key={r.id} a={<><i className="tag">{r.type.slice(0, 3)}</i>{r.title}</>} b={r.when} lock={r.title} />)}</ul>
    ) : <p className="sayp dim">Ninguno de los recursos recientes está en esta carpeta.</p>) : <p className="sayp dim">Toca un sector del disco.</p> },
    { slot: 'rb', title: st.byFolder ? 'Carpetas' : 'Por tipo', meta: `${st.groups.length}`, body: (
      <ul className="rows">{st.groups.map((x) => <Row key={x.key} on={x.num === g?.num} a={<><Dot c={x.col} />{x.name}</>} b={<Bar p={x.count / Math.max(1, st.groups[0]?.count ?? 1)} c={x.col} n={x.count} />} onClick={() => acts.select('almacen', x.num)} lock={x.name} />)}</ul>
    ) }
  ]
}
