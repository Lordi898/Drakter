/** HÁBITOS: hélice de anillos (uno por hábito) × 28 días; la racha viva como arco de luz. */
import * as THREE from 'three'
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js'
import type { HmHabit, HmHabitDay, HoloSnapshot, PickInfo } from '../../model'
import { arcSlab, pairs, segments } from '../geo'
import type { Materials } from '../materials'
import { base, C, clearInstancedPick, instanced, pickInstanced, stationState, tmpM, tmpP, tmpQ, yAxis, W, type Station, type Tag } from './base'

const ND = 28
const MAX_HABITS = 5
const R = 1.02
const yOf = (h: number): number => 0.45 + h * 0.52
const aOf = (h: number, d: number): number => (d / ND) * Math.PI * 1.75 + h * 0.42 - Math.PI * 0.4

const DAY_TEXT: Record<Exclude<HmHabitDay, null>, string> = { done: 'cumplido', skipped: 'saltado', missed: 'no cumplido', open: 'pendiente' }

export function habitos(M: Materials, pos: THREE.Vector3): Station {
  const b = base(M, 'habitos', 'Hábitos', '5', pos, 1.35, 3.1)
  let helix: THREE.Group | null = null
  let habits: readonly HmHabit[] = []
  let cubes: THREE.InstancedMesh | null = null
  let picked = -1
  let now = new Date()

  const s: Station = {
    ...stationState(b),
    setData(snap: HoloSnapshot) {
      const root = b.rebuild()
      now = snap.now
      habits = snap.habits.items.slice(0, MAX_HABITS)
      helix = new THREE.Group()
      root.add(helix)
      cubes = instanced(new THREE.BoxGeometry(1, 1, 1), b.reg(M.holoMat({ color: C.ice, fill: 0.14, fresnel: 0.4 })), habits.length * ND)
      habits.forEach((hb, h) =>
        hb.days.slice(-ND).forEach((st, d) => {
          const a = aOf(h, d), today = d === ND - 1, done = st === 'done'
          const sz = done ? 0.085 : st === null ? 0.025 : 0.04
          tmpM.compose(tmpP.set(Math.cos(a) * R, yOf(h), Math.sin(a) * R), tmpQ.setFromAxisAngle(yAxis, -a), new THREE.Vector3().setScalar(today ? sz * 1.5 : sz))
          cubes!.setMatrixAt(h * ND + d, tmpM)
          const inStreak = d >= ND - hb.streak
          const col = today && st === 'open' ? C.amber : today ? 0xffffff : done ? (inStreak ? 0xbdf2ff : 0x4fb8f0) : st === 'missed' ? 0x24506f : C.dark
          cubes!.setColorAt(h * ND + d, new THREE.Color(col))
        })
      )
      helix.add(cubes)
      const arcs = habits.filter((hb) => hb.streak > 0).map((hb) => {
        const h = habits.indexOf(hb), from = Math.max(0, ND - hb.streak)
        return arcSlab(R + 0.09, R + 0.13, aOf(h, from), aOf(h, ND - 1), yOf(h) - 0.012, yOf(h) + 0.012, Math.max(2, Math.min(ND, hb.streak)))
      })
      if (arcs.length) {
        helix.add(new THREE.Mesh(mergeGeometries(arcs), b.reg(M.holoMat({ color: C.white, fill: 0.8 }))))
        for (const g of arcs) g.dispose()
      }
      const guides = habits.map((_, h) =>
        Array.from({ length: 40 }, (_, k) => {
          const a = aOf(h, (k / 39) * (ND - 1))
          return new THREE.Vector3(Math.cos(a) * (R - 0.08), yOf(h), Math.sin(a) * (R - 0.08))
        })
      )
      if (guides.length) helix.add(new THREE.LineSegments(segments(pairs(guides)), b.reg(M.lineMat(C.ice, 0.35, true))))
      helix.add(new THREE.LineSegments(segments([[new THREE.Vector3(0, 0.1, 0), new THREE.Vector3(0, yOf(Math.max(0, habits.length - 1)) + 0.5, 0)]]), b.reg(M.lineMat(C.ice, 0.5))))
      const best = habits.reduce<HmHabit | null>((a, c) => (!a || c.streak > a.streak ? c : a), null)
      const pending = snap.habits.items.filter((x) => x.todayScheduled && !x.todayDone).length
      s.metric =
        snap.habits.load !== 'ready' ? (snap.habits.load === 'error' ? 'sin datos' : 'cargando…')
          : best ? `${best.name} · racha de ${best.streak} d${pending ? ` · ${pending} por marcar hoy` : ''}` : 'sin hábitos activos'
      picked = -1
    },
    update(_t, dt, c) {
      b.apply(s)
      if (helix) helix.rotation.y += dt * (c.reduced ? 0 : 0.1 * (picked >= 0 ? 0.1 : 1))
    },
    pick(rc): PickInfo | null {
      picked = pickInstanced(rc, cubes)
      if (picked < 0) return null
      const hb = habits[Math.floor(picked / ND)], d = picked % ND
      if (!hb) return null
      const st = hb.days.slice(-ND)[d] ?? null
      const date = new Date(now)
      date.setDate(date.getDate() - (ND - 1 - d))
      return {
        key: 'hab:' + hb.id + ':' + d,
        title: hb.name,
        sub: `${d === ND - 1 ? 'hoy' : date.toLocaleDateString('es-ES', { weekday: 'short', day: 'numeric', month: 'short' })} · ${st ? DAY_TEXT[st] : 'no tocaba'}`,
        lines: [`Racha actual ${hb.streak} · mejor ${hb.best}`, ...(hb.goal ? [`Objetivo: ${hb.goal}`] : [])],
        ref: { kind: 'habit', id: hb.id, day: d - (ND - 1) }
      }
    },
    clearPick() {
      picked = -1
      clearInstancedPick(cubes)
    },
    tags(): Tag[] {
      if (!helix) return []
      return habits.map((hb, h) => {
        const a = aOf(h, ND - 1)
        return { p: W(helix!, Math.cos(a) * (R + 0.22), yOf(h), Math.sin(a) * (R + 0.22)), t: `${hb.name} · ${hb.streak} d`, k: hb.todayScheduled && !hb.todayDone ? 'warn' : hb.streak >= 10 ? 'hi' : '' }
      })
    },
    dispose: () => b.dispose()
  }
  return s
}
