/** HOY: esfera de 24 horas con la agenda real del día, las tareas que vencen y la aguja de «ahora». */
import { C, TAU } from '../gl/kit'
import { hm, type VEvent, type VTask } from '../model'
import { fit, inwardAt, type ModuleDef } from './base'

const SLOTS = [9.6, 12.6, 14.4, 16.2, 18.8, 20.2, 21.4, 10.8, 17.4, 22.2]
const pad2 = (n: number): string => String(n).padStart(2, '0')
const taskCol = (t: VTask) => (t.done ? C.cyan : t.tone === 'late' ? C.red : t.tone === 'soon' ? C.amber : C.ice)

export const hoy: ModuleDef = {
  id: 'hoy', name: 'Hoy', key: '1', rIn: 2.5, rOut: 3.1,
  home: { pos: [0, 0, 0], rx: -1.08, rz: 0.07, scale: 1, spin: 0 },
  kpi: ({ model }) => {
    if (!model.todayEvents && !model.todayTasks) return 'cargando la agenda…'
    const open = model.todayTasks?.filter((t) => !t.done).length ?? 0
    return `${model.todayEvents?.length ?? 0} en la agenda · ${open} tarea${open === 1 ? '' : 's'} para hoy`
  },
  buildHome(b, l, { model }) {
    const n = model.nowHour / 24, o = 0.5 - n, R = (h: number) => h / 24 + o // «ahora» al frente
    b.line(3.0, 0, 1, 0.07, { a: 0.95 }).scale(96, 2.97, 0.05, { major: 4, majorLen: 0.13, out: false, a: 0.8, c0: o, c1: 1 + o })
    b.arc(2.5, 2.56, o, 0.5, { st: 5, u1: n * 90, col: C.blue, a: 0.9 }).line(2.5, 0, 1, 0.03, { a: 0.35, col: C.blue })
    for (const e of model.todayEvents ?? []) b.arc(2.64, 2.84, R(e.start), R(e.end), { col: C[e.col], a: e.end < model.nowHour ? 0.4 : 0.9 })
    for (let h = 0; h < 24; h += 3) b.text(pad2(h), 3.24, R(h), 0.22, { a: 0.75, inward: inwardAt(R(h)) })
    b.tick(0.5, 2.36, 3.34, 0.07, { col: C.white })
    l.text(`HOY · ${hm(model.nowHour)}`, 3.5, 0.5, 0.2, { col: C.white, a: 0.95, inward: true })
  },
  buildDetail(b, { model }) {
    const n = model.nowHour / 24, R = (h: number) => h / 24
    b.line(4.5, 0, 1, 0.07).scale(144, 4.48, 0.06, { major: 6, majorLen: 0.15, out: false, a: 0.85 })
    for (let h = 0; h < 24; h++) b.text(pad2(h), 4.71, R(h), 0.2, { a: h % 6 ? 0.55 : 1, col: h % 6 ? C.cyan : C.ice, inward: h > 6 && h < 18 })
    b.arc(4.2, 4.3, 0, n, { st: 5, u1: n * 130, col: C.blue }).dash(2.75, 0, 1, 0.035, 150, { a: 0.5, col: C.blue })
    for (const e of model.todayEvents ?? []) {
      b.arc(3.62, 4.14, R(e.start), R(e.end), { col: C[e.col], a: e.end < model.nowHour ? 0.4 : 0.9, id: e.num })
      const mid = (e.start + e.end) / 2, room = (R(e.end) - R(e.start)) * TAU * 3.88 - 0.12
      const lab = room > 0.4 ? fit(b, e.title.toUpperCase(), 0.17, room) : ''
      if (lab) b.text(lab, 3.88, R(mid), 0.17, { col: C.white, a: 0.95, inward: mid > 6 && mid < 18 })
    }
    ;(model.todayTasks ?? []).slice(0, SLOTS.length).forEach((t, i) => {
      const a = R(SLOTS[i]!)
      b.arc(3.2, 3.52, a, a + 0.036, { st: t.done ? 0 : 6, col: taskCol(t), a: t.done ? 0.55 : 1, id: t.num })
      if (t.done) b.tick(a + 0.018, 3.28, 3.44, 0.05, { col: C.white })
    })
    if (model.todayEvents && !model.todayEvents.length && !model.todayTasks?.length) b.text('DÍA DESPEJADO', 3.4, 0.5, 0.2, { col: C.ice, a: 0.7, inward: true })
    b.tick(n, 2.62, 4.84, 0.07, { col: C.white }).arc(2.62, 4.6, n - 0.022, n, { col: C.cyan, a: 0.1, hit: false })
    b.text(`AHORA ${hm(model.nowHour)}`, 2.56, n, 0.17, { col: C.white, inward: inwardAt(n) })
  },
  tip(num, { model }) {
    const t = model.todayTasks?.find((x) => x.num === num)
    if (t) return { title: t.title, sub: `${t.projectName ?? 'sin proyecto'} · ${t.dueText}`, hint: `clic para ${t.done ? 'reabrirla' : 'marcarla como hecha'}`, tone: t.tone === 'late' ? 'late' : t.tone === 'soon' ? 'soon' : undefined }
    const e: VEvent | undefined = model.todayEvents?.find((x) => x.num === num)
    return e ? { title: e.title, sub: `${hm(e.start)} – ${hm(e.end)}${e.subject ? ` · ${e.subject}` : ''}${e.room ? ` · ${e.room}` : ''}` } : null
  },
  click(num, { model }) {
    const t = model.todayTasks?.find((x) => x.num === num)
    return t ? { kind: 'toggleTask', id: t.id } : { kind: 'select' }
  }
}
