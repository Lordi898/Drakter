/** CALENDARIO: torre de días (14 placas desde el lunes de esta semana; hoy sobresale). */
import * as THREE from 'three'
import { hhmm, type HmEvent, type HoloSnapshot, type PickInfo } from '../../model'
import { circlePts, segments } from '../geo'
import type { Materials } from '../materials'
import { base, C, clamp01, ease, instanced, pickInstanced, clearInstancedPick, stationState, tmpM, tmpP, tmpQ, tmpS, yAxis, type Station, type Tag } from './base'

const N = 14
const Y0 = 0.32
const DY = 0.215
/** Franja horaria visible en cada placa. */
const H0 = 7
const H1 = 24

const KIND_COLOR: Record<HmEvent['kind'], number> = { clase: C.steel, evento: C.teal, recordatorio: C.white, bloque: C.warm }
const KIND_Z: Record<HmEvent['kind'], number> = { clase: -0.32, evento: 0.12, recordatorio: 0.42, bloque: 0.42 }
const KIND_NAME: Record<HmEvent['kind'], string> = { clase: 'clase', evento: 'evento', recordatorio: 'recordatorio', bloque: 'bloque de tiempo' }

export function calendario(M: Materials, pos: THREE.Vector3): Station {
  const b = base(M, 'calendario', 'Calendario', '2', pos, 1.35, 3.5)
  const plateM: THREE.Matrix4[] = Array.from({ length: N }, () => new THREE.Matrix4())
  const local = new THREE.Matrix4()
  let plates: THREE.InstancedMesh | null = null
  let evMesh: THREE.InstancedMesh | null = null
  let evs: readonly HmEvent[] = []
  let days: readonly string[] = []
  let todayIdx = 0
  let busyDays = new Set<number>()
  let picked = -1

  const s: Station = {
    ...stationState(b),
    setData(snap: HoloSnapshot) {
      const root = b.rebuild()
      days = snap.calendar.days
      todayIdx = snap.calendar.todayIndex
      evs = snap.calendar.events.filter((e) => e.day >= 0 && e.day < N)
      busyDays = new Set(evs.filter((e) => e.kind !== 'clase').map((e) => e.day))
      plates = instanced(new THREE.BoxGeometry(1.7, 0.045, 1.25), b.reg(M.holoMat({ color: C.ice, fill: 0.06, fresnel: 0.25 })), N)
      for (let i = 0; i < N; i++) plates.setColorAt(i, new THREE.Color(i === todayIdx ? 0x9be8ff : i < todayIdx ? 0x1d5a86 : i % 7 >= 5 ? 0x4a8fd0 : 0x3a90d0))
      root.add(plates)
      evMesh = instanced(new THREE.BoxGeometry(1, 1, 1), b.reg(M.holoMat({ color: C.ice, fill: 0.45 })), evs.length)
      evs.forEach((e, i) => evMesh!.setColorAt(i, new THREE.Color(e.color ?? KIND_COLOR[e.kind])))
      root.add(evMesh)
      const spine = new THREE.LineSegments(
        segments([
          [new THREE.Vector3(0, 0.1, 0), new THREE.Vector3(0, Y0 + N * DY + 0.3, 0)],
          ...Array.from({ length: N }, (_, i) => [new THREE.Vector3(-1.05, Y0 + i * DY, 0.66), new THREE.Vector3(-0.92, Y0 + i * DY, 0.66)])
        ]),
        b.reg(M.lineMat(C.ice, 0.7))
      )
      root.add(spine)
      const todayRing = new THREE.Line(new THREE.BufferGeometry().setFromPoints(circlePts(1.25, 64)), b.reg(M.lineMat(C.white, 0.9)))
      todayRing.position.y = Y0 + todayIdx * DY
      root.add(todayRing)
      const week = evs.filter((e) => e.day >= todayIdx && e.day < todayIdx + 7).length
      const next = evs.find((e) => e.day > todayIdx || (e.day === todayIdx && e.start > snap.nowHours))
      s.metric =
        snap.calendar.load !== 'ready' ? (snap.calendar.load === 'error' ? 'sin datos' : 'cargando…')
          : `${week} en 7 días${next ? ` · próximo: ${next.title}` : ''}`
      picked = -1
    },
    update(t, _dt, c) {
      b.apply(s)
      if (!plates || !evMesh) return
      const k = c.reduced ? 0 : 1
      for (let i = 0; i < N; i++) {
        const today = i === todayIdx, rise = ease(clamp01(s.build * 1.6 - i * 0.04))
        const rot = Math.sin(t * 0.25) * 0.35 * k + (i - todayIdx) * 0.07 * (0.6 + 0.4 * Math.sin(t * 0.4)) * (k || 0.5)
        const pull = today ? 0.28 + Math.sin(t * 2) * 0.03 * k : 0
        tmpM.compose(tmpP.set(pull, Y0 + i * DY * rise, 0), tmpQ.setFromAxisAngle(yAxis, rot), tmpS.set(today ? 1.08 : 1, 1, today ? 1.08 : 1))
        plateM[i]!.copy(tmpM)
        plates.setMatrixAt(i, tmpM)
      }
      plates.instanceMatrix.needsUpdate = true
      evs.forEach((e, i) => {
        const st = e.allDay ? H0 : Math.max(H0, Math.min(H1 - 0.25, e.start)), en = e.allDay ? H1 : Math.max(st + 0.25, Math.min(H1, e.end))
        const x = -0.82 + ((st - H0) / (H1 - H0)) * 1.64, w = Math.max(0.06, ((en - st) / (H1 - H0)) * 1.64)
        local.compose(tmpP.set(x + w / 2, 0.06, KIND_Z[e.kind]), tmpQ.identity(), tmpS.set(w, i === picked ? 0.13 : 0.07, 0.2))
        tmpM.multiplyMatrices(plateM[e.day]!, local)
        evMesh!.setMatrixAt(i, tmpM)
      })
      evMesh.instanceMatrix.needsUpdate = true
      evMesh.computeBoundingSphere()
      plates.computeBoundingSphere()
    },
    pick(rc): PickInfo | null {
      picked = pickInstanced(rc, evMesh)
      const e = evs[picked]
      if (!e) return null
      return {
        key: 'cal:' + e.id,
        title: e.title,
        sub: `${days[e.day] ?? ''} · ${e.allDay ? 'todo el día' : `${hhmm(e.start)}–${hhmm(e.end)}`}`,
        lines: [KIND_NAME[e.kind], ...(e.place ? [e.place] : [])],
        ref: { kind: 'event', sourceType: e.sourceType, id: e.sourceId }
      }
    },
    clearPick() {
      picked = -1
      clearInstancedPick(evMesh)
    },
    tags(): Tag[] {
      return days.slice(0, N).map((d, i) => {
        tmpP.set(-0.95, 0.02, 0.62).applyMatrix4(plateM[i]!)
        return { p: b.body.localToWorld(tmpP.clone()), t: i === todayIdx ? `${d} · hoy` : d, k: i === todayIdx ? 'hi' : busyDays.has(i) && i > todayIdx ? 'warn' : '' }
      })
    },
    dispose: () => b.dispose()
  }
  return s
}
