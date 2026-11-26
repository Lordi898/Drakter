/** TAREAS: bloques apilados por estado (pendiente, en curso, en espera); caen en cascada al construirse. */
import * as THREE from 'three'
import type { HmColumn, HmTask, HoloSnapshot, PickInfo } from '../../model'
import { PRIORITY_LABELS, TASK_STATUS_LABELS } from '@/modules/tasks/types'
import { arcSlab } from '../geo'
import type { Materials } from '../materials'
import { base, C, clamp01, clearInstancedPick, ease, instanced, pickInstanced, stationState, tmpM, tmpP, tmpQ, tmpS, W, yAxis, type Station, type Tag } from './base'

const PER_COLUMN = 24
const MAX_STACK = 2.9
const COL_NAMES = ['pendiente', 'en curso', 'en espera'] as const
const PRIO_RANK = { urgent: 0, high: 1, medium: 2, low: 3 } as const

const colorOf = (t: HmTask): number =>
  t.overdue ? 0xff7a5c : t.column === 2 ? C.past : t.priority === 'urgent' || t.priority === 'high' ? C.amber : t.priority === 'medium' ? 0x58c8ff : 0x2f86c8

export function tareas(M: Materials, pos: THREE.Vector3): Station {
  const b = base(M, 'tareas', 'Tareas', '3', pos, 1.45, 3.2)
  let list: { t: HmTask; ci: HmColumn; j: number; h: number; y: number }[] = []
  let tops = [0.1, 0.1, 0.1]
  let counts = [0, 0, 0]
  let blocks: THREE.InstancedMesh | null = null
  let picked = -1

  const s: Station = {
    ...stationState(b),
    setData(snap: HoloSnapshot) {
      const root = b.rebuild()
      const items = snap.tasks.items
      counts = [0, 1, 2].map((c) => items.filter((t) => t.column === c).length)
      list = []
      tops = [0.1, 0.1, 0.1]
      for (const ci of [0, 1, 2] as const) {
        const col = items
          .filter((t) => t.column === ci)
          .sort((a, c) => PRIO_RANK[c.priority] - PRIO_RANK[a.priority])
          .slice(-PER_COLUMN)
        const raw = col.map((t) => 0.06 + Math.min(8, (t.estimatedMin ?? 60) / 60) * 0.04)
        const total = raw.reduce((a, h) => a + h + 0.035, 0)
        const k = total > MAX_STACK ? MAX_STACK / total : 1
        col.forEach((t, j) => {
          const h = raw[j]! * k
          list.push({ t, ci, j, h, y: tops[ci]! + h / 2 })
          tops[ci]! += h + 0.035 * k
        })
      }
      blocks = instanced(new THREE.BoxGeometry(1, 1, 1), b.reg(M.holoMat({ color: C.ice, fill: 0.07, fresnel: 0.45 })), list.length)
      list.forEach((it, i) => blocks!.setColorAt(i, new THREE.Color(colorOf(it.t))))
      root.add(blocks)
      const plates = instanced(new THREE.BoxGeometry(0.92, 0.03, 0.66), b.reg(M.holoMat({ color: C.ice, fill: 0.15 })), 3)
      for (let i = 0; i < 3; i++) {
        tmpM.makeTranslation((i - 1) * 1.0, 0.04, 0)
        plates.setMatrixAt(i, tmpM)
      }
      root.add(plates)
      const all = counts[0]! + counts[1]! + counts[2]!
      // Anillo de la base: parte de lo abierto que ya está en curso.
      const liveFrac = all ? counts[1]! / all : 0
      if (liveFrac > 0)
        root.add(new THREE.Mesh(arcSlab(1.62, 1.7, -Math.PI / 2, -Math.PI / 2 + liveFrac * Math.PI * 2, 0.02, 0.06, 48), b.reg(M.holoMat({ color: C.white, fill: 0.5 }))))
      s.metric = snap.tasks.load !== 'ready' ? (snap.tasks.load === 'error' ? 'sin datos' : 'cargando…') : `${all} abiertas · ${counts[1]} en curso`
      picked = -1
    },
    update(t, _dt, c) {
      b.apply(s)
      if (!blocks) return
      list.forEach((it, i) => {
        const drop = 1 - ease(clamp01(s.build * 2.2 - i * 0.03))
        const live = it.t.column === 1 && !c.reduced
        const wob = live ? Math.sin(t * 2 + i) * 0.015 : 0
        const rot = ((it.j % 2) - 0.5) * 0.08 + (live ? Math.sin(t * 0.8 + i) * 0.05 : 0)
        tmpM.compose(tmpP.set((it.ci - 1) * 1.0, it.y + drop * 2.2 + wob, i === picked ? 0.12 : 0), tmpQ.setFromAxisAngle(yAxis, rot), tmpS.set(i === picked ? 0.86 : 0.78, it.h, 0.5))
        blocks!.setMatrixAt(i, tmpM)
      })
      blocks.instanceMatrix.needsUpdate = true
      blocks.computeBoundingSphere()
    },
    pick(rc): PickInfo | null {
      picked = pickInstanced(rc, blocks)
      const x = list[picked]?.t
      if (!x) return null
      return {
        key: 'task:' + x.id,
        title: x.title,
        sub: `${x.project ?? 'sin proyecto'} · ${TASK_STATUS_LABELS[x.status].toLowerCase()}`,
        lines: [
          `Prioridad ${PRIORITY_LABELS[x.priority].toLowerCase()}${x.due ? ` · vence ${x.due}` : ''}${x.overdue ? ' · vencida' : ''}`,
          ...(x.estimatedMin ? [`Estimación ${x.estimatedMin >= 60 ? `${(x.estimatedMin / 60).toFixed(1)} h` : `${x.estimatedMin} min`}`] : [])
        ],
        ref: { kind: 'task', id: x.id }
      }
    },
    clearPick() {
      picked = -1
      clearInstancedPick(blocks)
    },
    tags(): Tag[] {
      return COL_NAMES.map((n, i) => ({ p: W(b.body, (i - 1) * 1.0, tops[i]! + 0.18, 0), t: `${n} · ${counts[i]}`, k: i === 1 ? 'hi' : '' }))
    },
    dispose: () => b.dispose()
  }
  return s
}
