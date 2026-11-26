/**
 * CALENDARIO Y ASIGNATURAS: rueda de los próximos siete días (hoy al frente) de 8 a 22 h con la agenda
 * real (eventos, bloques y clases) y una franja de 35 días con las tareas que vencen cada día.
 */
import { C } from '../gl/kit'
import { dayNum, dow3, hm } from '../model'
import { fit, inwardAt, type ModuleDef } from './base'

const clampH = (h: number) => Math.min(22, Math.max(8, h))
const STRIP = 1_000_000 // ids de la franja: STRIP + día

export const calendario: ModuleDef = {
  id: 'calendario', name: 'Calendario', key: '4', rIn: 6.3, rOut: 7.3,
  home: { pos: [0, 0, 0], rx: -1.16, rz: -0.03, scale: 1, spin: 0 },
  kpi: ({ model }) => {
    if (!model.week) return 'cargando la agenda…'
    const n = model.week.length, next = model.dueStrip?.findIndex((x, i) => i > 0 && x > 0) ?? -1
    return `${n} en los próximos 7 días${next > 0 ? ` · próximo vencimiento ${next === 1 ? 'mañana' : `en ${next} días`}` : ''}`
  },
  buildHome(b, l, { model }) {
    const o = 0.5 - 0.5 / 7
    b.line(7.2, 0, 1, 0.06, { a: 0.9 }).line(6.34, 0, 1, 0.03, { a: 0.3, col: C.blue }).scale(140, 7.2, 0.05, { major: 5, majorLen: 0.13, a: 0.6 })
    for (let d = 0; d < 7; d++) {
      const a = d / 7 + 0.004 + o, z = (d + 1) / 7 - 0.004 + o, td = d === 0
      b.arc(6.4, 7.08, a, z, { st: 6, a: td ? 0.95 : 0.3, col: td ? C.white : C.blue })
      if (!td) b.text(dow3(model.todayDow, d).toUpperCase(), 7.42, (d + 0.5) / 7 + o, 0.2, { a: 0.55, inward: inwardAt((d + 0.5) / 7 + o) })
    }
    for (const e of model.week ?? []) { if (e.allDay) continue; const r = (h: number) => 6.46 + ((clampH(h) - 8) / 14) * 0.56; b.arc(r(e.start), Math.max(r(e.end), r(e.start) + 0.03), e.day / 7 + 0.012 + o, (e.day + 1) / 7 - 0.012 + o, { col: C[e.col], a: 0.75 }) }
    l.text(`CALENDARIO · ${dow3(model.todayDow, 0).toUpperCase()} ${dayNum(model.todayKey, 0)}`, 7.44, 0.405, 0.2, { col: C.white, a: 0.95, inward: true })
    const late = model.dueStrip?.[1] ?? 0
    if (late) l.text(`${late} VENCE${late > 1 ? 'N' : ''} MAÑANA`, 7.44, 0.6, 0.2, { col: C.amber, a: 1, inward: true })
  },
  buildDetail(b, { model }) {
    const r = (h: number) => 2.9 + ((clampH(h) - 8) / 14) * 1.38, h = model.nowHour
    b.line(4.62, 0, 1, 0.06).dash(2.76, 0, 1, 0.035, 140, { a: 0.5, col: C.blue })
    for (const hh of [10, 12, 14, 16, 18, 20]) b.dash(r(hh), 0, 1, 0.02, 200, { a: 0.22, col: C.blue })
    for (let d = 0; d < 7; d++) {
      const td = d === 0
      b.arc(2.86, 4.32, d / 7 + 0.005, (d + 1) / 7 - 0.005, { st: 6, a: td ? 1 : 0.34, col: td ? C.white : C.blue })
      b.text(`${dow3(model.todayDow, d).toUpperCase()} ${dayNum(model.todayKey, d)}`, 4.44, (d + 0.5) / 7, 0.19, { col: td ? C.white : C.cyan, a: td ? 1 : 0.7, inward: d > 1 && d < 5 })
    }
    for (const e of model.week ?? []) {
      const a = e.day / 7 + 0.012, z = (e.day + 1) / 7 - 0.012, past = e.day === 0 && e.end < h
      if (e.allDay) { b.arc(4.24, 4.3, a, z, { col: C[e.col], a: 0.9, id: e.num }); continue }
      b.arc(r(e.start), Math.max(r(e.end), r(e.start) + 0.06), a, z, { col: C[e.col], a: past ? 0.34 : 0.9, id: e.num })
      if (e.end - e.start >= 1.4) { const t = fit(b, e.title.toUpperCase(), 0.135, (z - a) * 6.28 * 3.4); if (t) b.text(t, (r(e.start) + r(e.end)) / 2, (e.day + 0.5) / 7, 0.135, { col: C.white, a: past ? 0.5 : 0.95, inward: e.day > 1 && e.day < 5 }) }
    }
    if (h > 8 && h < 22) b.line(r(h), 0.004, 1 / 7 - 0.004, 0.07, { col: C.white })
    const strip = model.dueStrip ?? []
    for (let k = 0; k < 35; k++) {
      const n = strip[k] ?? 0, wk = (model.todayDow + k) % 7
      b.arc(4.68, 4.84, k / 35 + 0.002, (k + 1) / 35 - 0.002, { st: n || k === 0 ? 0 : 6, col: n ? (k <= 1 ? C.amber : C.cyan) : k === 0 ? C.white : C.blue, a: n ? 1 : k === 0 ? 0.9 : wk > 4 ? 0.3 : 0.7, id: n ? STRIP + k : 0, seg: 3 })
      if (n && k > 0) b.text(`${n}`, 4.95, (k + 0.5) / 35, 0.13, { col: k <= 1 ? C.amber : C.ice, inward: k > 9 && k < 26 })
    }
  },
  tip(num, { model }) {
    if (num >= STRIP) {
      const k = num - STRIP, n = model.dueStrip?.[k] ?? 0
      return { title: `${n} tarea${n === 1 ? '' : 's'} vence${n === 1 ? '' : 'n'}`, sub: k === 0 ? 'hoy' : k === 1 ? 'mañana' : `${dow3(model.todayDow, k)} ${dayNum(model.todayKey, k)} · en ${k} días`, tone: k <= 1 ? 'soon' : undefined }
    }
    const e = model.week?.find((x) => x.num === num)
    return e ? { title: e.title, sub: `${dow3(model.todayDow, e.day)} ${dayNum(model.todayKey, e.day)} · ${e.allDay ? 'todo el día' : `${hm(e.start)} – ${hm(e.end)}`}${e.subject ? ` · ${e.subject}` : ''}` } : null
  },
  click: () => ({ kind: 'select' })
}
