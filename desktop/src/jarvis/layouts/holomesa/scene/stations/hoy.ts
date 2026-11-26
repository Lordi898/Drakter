/** HOY: el dial del día en el corazón de la mesa (eventos de hoy como arcos, aguja de «ahora»). */
import * as THREE from 'three'
import { hhmm, type HmEvent, type HoloSnapshot, type PickInfo } from '../../model'
import { arcSlab, circlePts } from '../geo'
import type { Materials } from '../materials'
import { base, billboard, C, face, instanced, stationState, tmpM, tmpP, tmpQ, tmpS, W, yAxis, type Station, type Tag } from './base'

const Y = 1.0
const ELAPSED_SEG = 96
/** Índices por segmento de `arcSlab`: 4 caras × 6. */
const IDX_PER_SEG = 24
const hourA = (h: number): number => -Math.PI / 2 + (h / 24) * Math.PI * 2

export function hoy(M: Materials): Station {
  const b = base(M, 'hoy', 'Hoy', '1', new THREE.Vector3(0, 0, 0.3), 2.0, 2.0)
  let evMeshes: { mesh: THREE.Mesh; ev: HmEvent }[] = []
  let events: readonly HmEvent[] = []
  let rings: THREE.Line[] = []
  let core: THREE.Mesh | null = null
  let tip: THREE.Mesh | null = null
  let needle: THREE.Group | null = null
  let elapsed: THREE.Mesh | null = null
  let nowH = 0
  let lastNowKey = -1
  let pickEv: HmEvent | null = null
  let doneLabel = ''

  const s: Station = {
    ...stationState(b),
    setData(snap: HoloSnapshot) {
      const root = b.rebuild()
      nowH = snap.nowHours
      events = snap.today.events.filter((e) => !e.allDay)
      const ticks = instanced(new THREE.BoxGeometry(0.018, 1, 0.04), b.reg(M.holoMat({ color: C.ice, fill: 0.2, edge: 0.5 })), 96)
      for (let i = 0; i < 96; i++) {
        const a = hourA(i / 4), big = i % 4 === 0, h = big ? (i % 24 === 0 ? 0.34 : 0.2) : 0.07
        tmpM.compose(tmpP.set(Math.cos(a) * 2.02, Y + (big ? 0.02 : 0), Math.sin(a) * 2.02), tmpQ.setFromAxisAngle(yAxis, -a), tmpS.set(1, h, 1))
        ticks.setMatrixAt(i, tmpM)
      }
      root.add(ticks)
      evMeshes = events.map((ev) => {
        const past = ev.end <= nowH, soon = ev.start > nowH && ev.start - nowH < 2
        const col = past ? 0x2f7fb8 : soon ? C.amber : (ev.color ?? C.ice)
        const mesh = new THREE.Mesh(
          arcSlab(1.55, 1.85, hourA(ev.start), hourA(Math.max(ev.end, ev.start + 0.25)), Y - 0.09, Y + 0.09, 10),
          b.reg(M.holoMat({ color: col, fill: past ? 0.05 : 0.22, edge: past ? 0.4 : 1.1 }))
        )
        root.add(mesh)
        return { mesh, ev }
      })
      // Arco del día transcurrido: geometría completa y `drawRange` según la hora (sin reconstruir).
      elapsed = new THREE.Mesh(arcSlab(1.36, 1.42, hourA(0), hourA(24), Y - 0.02, Y + 0.02, ELAPSED_SEG), b.reg(M.holoMat({ color: C.white, fill: 0.6 })))
      root.add(elapsed)
      needle = new THREE.Group()
      root.add(needle)
      const nb = new THREE.Mesh(new THREE.BoxGeometry(2.3, 0.025, 0.025), b.reg(M.holoMat({ color: C.white, fill: 0.9 })))
      nb.position.set(1.15, Y, 0)
      needle.add(nb)
      tip = billboard(M, C.white, 0.7, 1.2)
      b.reg(tip.material as THREE.ShaderMaterial)
      tip.position.set(2.25, Y, 0)
      needle.add(tip)
      const gyro = new THREE.Group()
      gyro.position.y = Y
      root.add(gyro)
      rings = [0.5, 0.68, 0.86].map((r, i) => {
        const g = new THREE.Line(new THREE.BufferGeometry().setFromPoints(circlePts(r, 96)), b.reg(M.lineMat(i === 1 ? C.white : C.ice, 0.75)))
        gyro.add(g)
        return g
      })
      core = billboard(M, 0x9be8ff, 1.1, 0.8)
      b.reg(core.material as THREE.ShaderMaterial)
      core.position.y = Y
      root.add(core)
      const spire = new THREE.Mesh(new THREE.BoxGeometry(0.03, Y - 0.1, 0.03), b.reg(M.holoMat({ color: 0x9be8ff, fill: 1.0, edge: 0.3 })))
      spire.position.y = (Y - 0.1) / 2 + 0.05
      root.add(spire)
      // Columna de 10 anillos: fracción de las tareas de hoy ya hechas.
      const { dueToday, doneToday } = snap.today
      const lit = dueToday > 0 ? Math.round((doneToday / dueToday) * 10) : 0
      const column = instanced(arcSlab(0.1, 0.13, 0, Math.PI * 2, 0, 0.012, 24), b.reg(M.holoMat({ color: C.ice, fill: 0.5 })), 10)
      for (let i = 0; i < 10; i++) {
        tmpM.makeTranslation(0, 0.1 + i * 0.075, 0)
        column.setMatrixAt(i, tmpM)
        column.setColorAt(i, new THREE.Color(i < lit ? 0x9be8ff : 0x123552))
      }
      root.add(column)
      doneLabel = dueToday > 0 ? `hechas ${doneToday}/${dueToday}` : ''
      const left = events.filter((e) => e.end > nowH).length
      s.metric = snap.today.load === 'ready' ? `${left} eventos por delante · ${Math.max(0, dueToday - doneToday)} tareas de hoy` : snap.today.load === 'error' ? 'sin datos' : 'cargando…'
      pickEv = null
      lastNowKey = -1
    },
    update(t, _dt, c) {
      b.apply(s)
      nowH = c.nowHours
      const k = c.reduced ? 0.15 : 1, think = c.agent === 'thinking' ? 3 : c.agent === 'executing' ? 2 : 1
      const [r0, r1, r2] = rings
      r0?.rotation.set(t * 0.7 * k * think, t * 0.4 * k, 0)
      r1?.rotation.set(Math.PI / 2 + Math.sin(t * 0.3) * 0.4, 0, t * 0.5 * k * think)
      r2?.rotation.set(t * 0.25 * k, 0, Math.PI / 3 + t * 0.35 * k)
      if (core) {
        face(core, c.camera)
        core.scale.setScalar((0.85 + Math.sin(t * 2.2) * 0.08 + c.voice * 0.5) * (0.4 + 0.6 * s.build))
      }
      if (tip) face(tip, c.camera)
      const key = Math.floor(nowH * 60)
      if (key !== lastNowKey) {
        lastNowKey = key
        if (needle) needle.rotation.y = -hourA(nowH)
        elapsed?.geometry.setDrawRange(0, Math.floor((nowH / 24) * ELAPSED_SEG) * IDX_PER_SEG)
      }
      for (const e of evMeshes) (e.mesh.material as THREE.ShaderMaterial).uniforms.uGain!.value = pickEv === e.ev ? 2.2 : 1
    },
    pick(rc): PickInfo | null {
      pickEv = null
      for (const e of evMeshes)
        if (rc.intersectObject(e.mesh, false).length) {
          pickEv = e.ev
          break
        }
      if (!pickEv) return null
      const ev = pickEv
      const when = ev.end <= nowH ? 'Ya terminado' : ev.start > nowH ? `Empieza en ${Math.round((ev.start - nowH) * 60)} min` : 'En curso'
      return {
        key: 'hoy:' + ev.id,
        title: ev.title,
        sub: `${hhmm(ev.start)}–${hhmm(ev.end)} · ${ev.kind}`,
        lines: [when, ...(ev.place ? [ev.place] : [])],
        ref: { kind: 'event', sourceType: ev.sourceType, id: ev.sourceId }
      }
    },
    clearPick() {
      pickEv = null
    },
    tags(): Tag[] {
      const out: Tag[] = events.map((e) => {
        const a = hourA((e.start + e.end) / 2)
        return { p: W(b.body, Math.cos(a) * 2.35, Y + 0.25, Math.sin(a) * 2.35), t: `${hhmm(e.start)} ${e.title}`, k: e.end <= nowH ? '' : 'hi' }
      })
      const a = hourA(nowH)
      out.push({ p: W(b.body, Math.cos(a) * 2.6, Y, Math.sin(a) * 2.6), t: `ahora ${hhmm(nowH)}`, k: 'hi' })
      if (doneLabel) out.push({ p: W(b.body, 0.2, 0.7, 0), t: doneLabel, k: '' })
      return out
    },
    dispose: () => b.dispose()
  }
  return s
}
