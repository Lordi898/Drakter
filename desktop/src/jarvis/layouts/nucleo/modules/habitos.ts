/** HÁBITOS: pistas concéntricas de 28 días (una por hábito activo) con la casilla de hoy marcable. */
import { C } from '../gl/kit'
import { addDays, type VHabit } from '../model'
import { type ModuleDef } from './base'

const MAX = 6
const C0 = 0.075, SP = 0.85 / 28
/** id de la casilla: num del hábito * 100 + día (27 = hoy). */
const cell = (h: VHabit, d: number) => h.num * 100 + d
const list = (hs: readonly VHabit[] | null) => (hs ?? []).slice(0, MAX)
const doneToday = (hs: readonly VHabit[]) => hs.filter((h) => h.todayScheduled && h.todayDone).length
const avgRate = (hs: readonly VHabit[]): number | null => { const r = hs.map((h) => h.rate).filter((x): x is number => x !== null); return r.length ? r.reduce((a, b) => a + b, 0) / r.length : null }

export const habitos: ModuleDef = {
  id: 'habitos', name: 'Hábitos', key: '2', rIn: 3.5, rOut: 4.45,
  home: { pos: [0, 0, 0], rx: -1.17, rz: -0.1, scale: 1, spin: 0.045 },
  kpi: ({ model }) => {
    if (!model.habits) return 'cargando hábitos…'
    const hs = model.habits, sched = hs.filter((h) => h.todayScheduled).length, r = avgRate(hs)
    return `${doneToday(hs)} de ${sched} hoy${r !== null ? ` · constancia ${Math.round(r * 100)} %` : ''}`
  },
  buildHome(b, l, { model }) {
    const hs = list(model.habits)
    hs.forEach((h, i) => {
      const r = 3.62 + i * 0.125
      for (let d = 0; d < 28; d++) { const v = h.days?.[d] ?? (d === 27 ? h.todayDone : null); b.arc(r - 0.036, r + 0.036, d / 28 + 0.003, (d + 1) / 28 - 0.003, { col: C[h.col], a: v ? 0.85 : v === false ? 0.16 : 0.06, seg: 3 }) }
    })
    b.line(4.38, 0, 1, 0.04, { a: 0.55 }).scale(28, 4.38, 0.05, { major: 7, majorLen: 0.12, a: 0.7 })
    const all = model.habits ?? [], r = avgRate(all)
    l.text(model.habits ? `HÁBITOS · ${doneToday(all)} DE ${all.filter((h) => h.todayScheduled).length} HOY${r !== null ? ` · CONSTANCIA ${Math.round(r * 100)} %` : ''}` : 'HÁBITOS', 4.66, 0.6, 0.2, { a: 0.85, inward: true })
  },
  buildDetail(b, { model }) {
    const hs = list(model.habits)
    b.line(4.62, 0, 1, 0.06).line(2.76, 0, 1, 0.04, { a: 0.5, col: C.blue })
    hs.forEach((h, i) => {
      const r = 2.92 + i * 0.285
      for (let d = 0; d < 28; d++) {
        const a = C0 + d * SP, v = d === 27 ? (h.todayScheduled ? h.todayDone : null) : h.days?.[d] ?? null
        const isToday = d === 27
        b.arc(r - 0.105, r + 0.105, a + 0.0025, a + SP - 0.0025, { st: v ? 0 : 6, col: C[h.col], a: v ? (isToday ? 1.15 : 0.9) : isToday ? 0.95 : v === false ? 0.3 : 0.08, id: isToday && h.todayScheduled ? cell(h, d) : h.days ? cell(h, d) : 0, seg: 4 })
      }
      b.text(h.name.toUpperCase().slice(0, 22), r, 0, 0.15, { col: C[h.col], a: 0.95 })
      if (h.streak !== null) b.text(String(h.streak), r, C0 + 28 * SP + 0.012, 0.19, { col: C.white, align: 'start' })
    })
    if (model.habits && !hs.length) b.text('SIN HÁBITOS ACTIVOS', 3.6, 0.5, 0.2, { a: 0.7, inward: true })
    for (let d = 0; d < 28; d++) {
      const key = addDays(model.todayKey, d - 27), wk = (model.todayDow - (27 - d) + 7 * 5) % 7
      b.text(String(Number(key.slice(8, 10))), 4.73, C0 + (d + 0.5) * SP, 0.14, { a: d === 27 ? 1 : wk > 4 ? 0.35 : 0.6, col: d === 27 ? C.white : C.cyan, inward: d > 7 && d < 21 })
      if (wk === 0) b.tick(C0 + d * SP, 2.78, 4.62, 0.025, { a: 0.5, col: C.blue })
    }
    b.tick(C0 + 27 * SP, 2.78, 4.66, 0.03, { col: C.white, a: 0.8 }).tick(C0 + 28 * SP, 2.78, 4.66, 0.03, { col: C.white, a: 0.8 })
    if (hs.some((h) => h.streak !== null)) b.text('RACHA', 4.74, C0 + 28 * SP + 0.03, 0.13, { a: 0.6 })
  },
  tip(num, { model }) {
    const h = model.habits?.find((x) => x.num === Math.floor(num / 100)), d = num % 100
    if (!h) return null
    const v = d === 27 ? h.todayDone : h.days?.[d]
    return { title: h.name, sub: `${d === 27 ? 'hoy' : addDays(model.todayKey, d - 27)} · ${v ? 'hecho' : v === false ? 'sin hacer' : 'no tocaba'}`, hint: d === 27 && h.todayScheduled ? `clic para ${h.todayDone ? 'desmarcarlo' : 'marcarlo'}` : undefined }
  },
  click(num, { model }) {
    const h = model.habits?.find((x) => x.num === Math.floor(num / 100))
    return h && num % 100 === 27 && h.todayScheduled ? { kind: 'toggleHabit', id: h.id } : { kind: 'select' }
  }
}
