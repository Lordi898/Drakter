/** ALMACÉN: estantería curva de archivos de luz; altura = tamaño, ámbar = sin indexar; haz de indexado. */
import * as THREE from 'three'
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js'
import { INDEX_LABELS, TYPE_LABELS, type ResourceType } from '@/modules/storage/types'
import type { HmFile, HoloSnapshot, PickInfo } from '../../model'
import { arcSlab } from '../geo'
import type { Materials } from '../materials'
import { base, billboard, C, clearInstancedPick, face, instanced, pickInstanced, stationState, tmpM, tmpP, tmpQ, tmpS, W, yAxis, type Station, type Tag } from './base'

const ROWS = 4
const PER = 42
const R = 1.38
const A0 = -Math.PI / 2 - 1.25
const A1 = -Math.PI / 2 + 1.25
const rowY = (r: number): number => 0.2 + r * 0.58

const KC: Record<ResourceType, number> = {
  pdf: 0x7fdcff, document: 0x9fb8ff, text: 0xb9d9ff, note: 0xc6e6ff, study_note: 0xc6e6ff, image: 0x6cf2d6,
  code: 0xdff6ff, archive: 0x3f8fe0, link: 0x8fe0ff, other: 0x6f9fc0
}

export function fmtSize(bytes: number | null): string {
  if (bytes === null) return '—'
  const kb = bytes / 1024
  return kb > 1024 * 1024 ? `${(kb / 1024 / 1024).toFixed(1)} GB` : kb > 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(kb))} KB`
}

export const unindexed = (f: HmFile): boolean => f.index === 'pending' || f.index === 'failed'

export function almacen(M: Materials, pos: THREE.Vector3): Station {
  const b = base(M, 'almacen', 'Almacén', '7', pos, 1.55, 2.7)
  let files: HmFile[] = []
  let hs: number[] = []
  let fm: THREE.InstancedMesh | null = null
  let scanArm: THREE.Group | null = null
  let scanGlow: THREE.Mesh | null = null
  let rowNames: string[] = []
  let pending = 0
  let indexing = false
  let picked = -1

  const s: Station = {
    ...stationState(b),
    setData(snap: HoloSnapshot) {
      const root = b.rebuild()
      // Agrupados por carpeta: cada balda empieza a leerse por su carpeta.
      files = [...snap.files.items].sort((a, c) => (a.folder ?? '').localeCompare(c.folder ?? '')).slice(0, ROWS * PER)
      const shelves = mergeGeometries(Array.from({ length: ROWS }, (_, i) => arcSlab(R - 0.16, R + 0.16, A0 - 0.04, A1 + 0.04, rowY(i) - 0.025, rowY(i), 40)))
      root.add(new THREE.Mesh(shelves, b.reg(M.holoMat({ color: C.ice, fill: 0.14 }))))
      fm = instanced(new THREE.BoxGeometry(1, 1, 1), b.reg(M.holoMat({ color: C.ice, fill: 0.08, fresnel: 0.25, edge: 0.75 })), files.length)
      hs = []
      files.forEach((fi, i) => {
        const row = Math.floor(i / PER), k = i % PER, a = A0 + ((k + 0.5) / PER) * (A1 - A0)
        const kb = Math.max(1, (fi.sizeBytes ?? 4096) / 1024)
        const h = 0.14 + Math.min(1, Math.log10(kb) / 5) * 0.32
        hs.push(h)
        tmpM.compose(tmpP.set(Math.cos(a) * R, rowY(row) + h / 2, Math.sin(a) * R), tmpQ.setFromAxisAngle(yAxis, -a + Math.PI / 2), tmpS.set(0.035, h, 0.24))
        fm!.setMatrixAt(i, tmpM)
        const warn = unindexed(fi)
        fm!.setColorAt(i, new THREE.Color(warn ? C.amber : KC[fi.type]).multiplyScalar(warn ? 0.7 : 1))
      })
      fm.computeBoundingSphere()
      root.add(fm)
      rowNames = Array.from({ length: ROWS }, (_, r) => files[r * PER]?.folder ?? '').map((n, r, all) => (r > 0 && n === all[r - 1] ? '' : n))
      const scan = new THREE.Mesh(new THREE.PlaneGeometry(0.05, ROWS * 0.58 + 0.2), b.reg(M.holoMat({ color: C.white, fill: 1.2, edge: 0.6 })))
      scanArm = new THREE.Group()
      scanArm.add(scan)
      scan.position.set(R + 0.2, (ROWS * 0.58 + 0.2) / 2 + 0.05, 0)
      root.add(scanArm)
      scanGlow = billboard(M, C.white, 0.5, 1.2)
      b.reg(scanGlow.material as THREE.ShaderMaterial)
      scanArm.add(scanGlow)
      scanGlow.position.set(R + 0.2, ROWS * 0.58 + 0.3, 0)
      pending = snap.files.pending
      s.metric =
        snap.files.load !== 'ready' ? (snap.files.load === 'error' ? 'sin datos' : 'cargando…')
          : `${snap.files.total} recursos${pending ? ` · ${pending} por indexar` : ''}`
      picked = -1
    },
    update(t, _dt, c) {
      b.apply(s)
      indexing = c.indexing
      if (!scanArm || !scanGlow) return
      // El haz solo recorre las baldas de verdad mientras hay un indexado en marcha; si no, descansa al borde.
      const sweep = c.reduced ? 0.5 : indexing ? 0.5 + 0.5 * Math.sin(t * 1.6) : 0.5 + 0.5 * Math.sin(t * 0.25)
      scanArm.rotation.y = -(A0 + sweep * (A1 - A0))
      face(scanGlow, c.camera)
    },
    pick(rc): PickInfo | null {
      picked = pickInstanced(rc, fm)
      const fi = files[picked]
      if (!fi) return null
      return {
        key: 'res:' + fi.id,
        title: fi.title,
        sub: `${fi.folder ?? 'sin carpeta'} · ${fmtSize(fi.sizeBytes)}`,
        lines: [`${TYPE_LABELS[fi.type]} · ${INDEX_LABELS[fi.index]}`],
        ref: { kind: 'resource', id: fi.id }
      }
    },
    clearPick() {
      picked = -1
      clearInstancedPick(fm)
    },
    tags(): Tag[] {
      const out: Tag[] = []
      if (indexing && scanGlow) out.push({ p: scanGlow.getWorldPosition(new THREE.Vector3()).add(new THREE.Vector3(0, 0.15, 0)), t: 'indexando', k: 'hi' })
      rowNames.forEach((f, r) => {
        if (f) out.push({ p: W(b.body, Math.cos(A0) * (R + 0.25), rowY(r) + 0.1, Math.sin(A0) * (R + 0.25)), t: f, k: '' })
      })
      const i = files.findIndex(unindexed)
      if (i >= 0 && pending > 0) {
        const row = Math.floor(i / PER), a = A0 + (((i % PER) + 0.5) / PER) * (A1 - A0)
        out.push({ p: W(b.body, Math.cos(a) * R, rowY(row) + (hs[i] ?? 0.2) + 0.12, Math.sin(a) * R), t: `${pending} sin indexar`, k: 'warn' })
      }
      return out
    },
    dispose: () => b.dispose()
  }
  return s
}
