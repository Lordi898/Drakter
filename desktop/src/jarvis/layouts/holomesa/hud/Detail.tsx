/** Panel de detalle de la sección abierta y acciones reales sobre el elemento seleccionado. */
import { useEffect, useState } from 'react'
import { todayIn } from '@/modules/calendar/dateUtils'
import { registerRecord } from '@/modules/habits/api'
import { completeTask } from '@/modules/tasks/api'
import type { SectionId as AppSection } from '@/navigation/sections'
import { describeError } from '@/services/api'
import type { HoloSnapshot, PickInfo, PickRef, SectionId } from '../model'
import { detailFor } from './sections'

/** Tema de datos que hay que recargar tras una acción. */
export type ReloadTopic = 'tasks' | 'habits' | 'today'

interface Action {
  readonly label: string
  readonly run: () => Promise<string>
  readonly warn?: boolean
}

const OPEN_IN: Record<PickRef['kind'], AppSection> = { task: 'tasks', event: 'calendar', project: 'projects', habit: 'habits', entity: 'relationships', resource: 'storage' }

function actionsFor(pick: PickInfo, snap: HoloSnapshot, reload: (t: ReloadTopic) => void, openInDrakter: (s: AppSection) => void): Action[] {
  const ref = pick.ref
  const out: Action[] = []
  if (ref.kind === 'task') {
    const task = snap.tasks.items.find((t) => t.id === ref.id)
    if (task)
      out.push({ label: 'Completar', run: async () => { await completeTask(task.id, task.revision); reload('tasks'); reload('today'); return 'Tarea completada.' } })
  }
  if (ref.kind === 'habit' && ref.day === 0) {
    const habit = snap.habits.items.find((h) => h.id === ref.id)
    if (habit?.todayScheduled && !habit.todayDone) {
      const date = todayIn(snap.timezone)
      out.push({ label: 'Marcar hecho hoy', run: async () => { await registerRecord(habit.id, date, 'done'); reload('habits'); reload('today'); return 'Hábito marcado.' } })
      out.push({ label: 'Saltar hoy', run: async () => { await registerRecord(habit.id, date, 'skipped'); reload('habits'); reload('today'); return 'Hoy queda como saltado.' } })
    }
  }
  out.push({ label: 'Abrir en Drakter', run: async () => { openInDrakter(OPEN_IN[ref.kind]); return '' } })
  return out
}

function Selected({ pick, snap, reload, openInDrakter, onDone }: {
  readonly pick: PickInfo
  readonly snap: HoloSnapshot
  readonly reload: (t: ReloadTopic) => void
  readonly openInDrakter: (s: AppSection) => void
  readonly onDone: () => void
}) {
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  useEffect(() => setMsg(null), [pick.key])
  const actions = actionsFor(pick, snap, reload, openInDrakter)
  const run = (a: Action): void => {
    setBusy(true)
    setMsg(null)
    a.run()
      .then((text) => {
        if (text) setMsg({ ok: true, text })
        onDone()
      })
      .catch((e: unknown) => setMsg({ ok: false, text: describeError(e, 'No se pudo completar la acción.') }))
      .finally(() => setBusy(false))
  }
  return (
    <div className="hm-sel" aria-live="polite">
      <b>{pick.title}</b>
      <div>{pick.sub}</div>
      {pick.lines.filter(Boolean).map((l) => <div key={l} style={{ color: 'var(--hm-dim)' }}>{l}</div>)}
      <div className="acts">
        {actions.map((a) => <button key={a.label} type="button" className={`hm-btn${a.warn ? ' warn' : ''}`} disabled={busy} onClick={() => run(a)}>{a.label}</button>)}
      </div>
      {msg ? <div className={msg.ok ? '' : 'err'} style={msg.ok ? { marginTop: 6, fontSize: 12 } : undefined}>{msg.text}</div> : null}
    </div>
  )
}

export function DetailPanel({ focus, snap, selected, onSelect, reload, openInDrakter, onActionDone }: {
  readonly focus: SectionId | null
  readonly snap: HoloSnapshot | null
  readonly selected: PickInfo | null
  readonly onSelect: (p: PickInfo) => void
  readonly reload: (t: ReloadTopic) => void
  readonly openInDrakter: (s: AppSection) => void
  readonly onActionDone: () => void
}) {
  // Se conserva la última sección mientras el panel se va (la transición de salida no queda vacía).
  const [shown, setShown] = useState<SectionId | null>(focus)
  useEffect(() => {
    if (focus) setShown(focus)
  }, [focus])
  const d = shown && snap ? detailFor(shown, snap) : null
  return (
    <div className="hm-detail-wrap" aria-hidden={focus === null}>
      <section className="hm-detail" aria-label={d ? `Detalle: ${d.title}` : undefined} key={shown ?? 'none'}>
        {d ? (
          <div className="front">
            <div className="hm-dh">
              <div className="no num">{d.no}</div>
              <div>
                <h2>{d.title}</h2>
                <p>{d.sub}</p>
              </div>
            </div>
            <div className="hm-kpis">
              {d.kpis.map(([v, l]) => (
                <div key={l} className="hm-kpi"><b className="num">{v}</b><span>{l}</span></div>
              ))}
            </div>
            <div className="hm-chart">{d.chart}</div>
            {selected && snap ? <Selected pick={selected} snap={snap} reload={reload} openInDrakter={openInDrakter} onDone={onActionDone} /> : null}
            {d.state ? <p className="hm-state">{d.state}</p> : null}
            <div className="hm-list" role="list">
              {d.rows.map((r, i) => (
                <button key={r.key} type="button" role="listitem" className="it" style={{ ['--c' as string]: r.color, ['--d' as string]: `${0.2 + Math.min(i, 12) * 0.04}s` }} onClick={() => r.pick && onSelect(r.pick)} tabIndex={focus ? 0 : -1}>
                  <i aria-hidden="true" />
                  <span>{r.label}</span>
                  <em>{r.meta}</em>
                </button>
              ))}
            </div>
          </div>
        ) : null}
      </section>
    </div>
  )
}
