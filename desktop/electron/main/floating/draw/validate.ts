/**
 * Segunda validación de `overlay.draw` en main (CONTRACT §9.5), antes de entregarlo a la página.
 * El backend ya validó (tidy + esquema + checkDraw + reglas de Drakter); aquí se repite con el
 * `draw.mjs` literal de Roamies y se comprueban los campos que el backend resolvió.
 */
import { checkDraw, DrawArgs, LIMITS } from './draw.mjs'

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const PART = /^p\d{1,4}$/
const FORBIDDEN_KINDS: ReadonlySet<string> = new Set(['type', 'copy', 'open', 'handoff'])
/** Campos que pone el backend y que el esquema del modelo no conoce. */
const BEAT_RESOLVED = ['n', 'caption', 'voiced', 'read'] as const
const MARK_RESOLVED = ['part', 'live', 'missing', 'credit'] as const
const TARGET_KEYS = ['at', 'to', 'tie'] as const
const MARGIN = 1000
const MAX_BUSY = 300

/** Disposición de monitores en px lógicos globales (unión de las geometrías). */
export interface LayoutBounds {
  readonly x: number
  readonly y: number
  readonly w: number
  readonly h: number
}

export type RectList = [number, number, number, number]

/** Lo que recibe `ink.js` como `e` de `{kind:'agent', e}`. `speech_id` lo quita `bridge.js`. */
export interface RoamieDrawEvent {
  readonly type: 'draw'
  readonly id: string
  readonly seg: number
  readonly last: boolean
  readonly beats: readonly Record<string, unknown>[]
  readonly edits: readonly Record<string, unknown>[]
  readonly win: RectList | null
  readonly busy: readonly RectList[]
  readonly fade?: number
  readonly deep?: boolean
  readonly speech_id?: number
}

export type DrawCheck =
  | { readonly ok: true; readonly event: RoamieDrawEvent; readonly turnId: string }
  | { readonly ok: false; readonly guideId: string | null; readonly problems: readonly string[] }

type Obj = Record<string, unknown>

function isObj(value: unknown): value is Obj {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value)
const int = (value: unknown): value is number => Number.isSafeInteger(value)

function inLayout(x: number, y: number, layout: LayoutBounds): boolean {
  return (
    x >= layout.x - MARGIN && y >= layout.y - MARGIN && x <= layout.x + layout.w + MARGIN && y <= layout.y + layout.h + MARGIN
  )
}

function asRect(value: unknown, layout: LayoutBounds): RectList | null {
  if (!Array.isArray(value) || value.length !== 4 || !value.every(finite)) return null
  const [x, y, w, h] = value as RectList
  if (w < 0 || h < 0 || !inLayout(x, y, layout) || !inLayout(x + w, y + h, layout)) return null
  return [x, y, w, h]
}

/** El objetivo tal como lo escribió el modelo: `src` si viene; si no, el rect resuelto como x/y/w/h. */
function modelTarget(target: Obj, where: string, layout: LayoutBounds, problems: string[]): Obj {
  const { rect, src, ...rest } = target
  if (rect !== undefined && asRect(rect, layout) === null) problems.push(`${where}: rect no válido o fuera de la pantalla`)
  if (src !== undefined) {
    if (!isObj(src)) {
      problems.push(`${where}: src no válido`)
      return rest
    }
    return { ...rest, ...src }
  }
  if (Object.keys(rest).length === 0 && Array.isArray(rect) && rect.length === 4) {
    const [x, y, w, h] = rect as number[]
    return { x, y, w, h }
  }
  return rest
}

function modelMark(mark: unknown, where: string, layout: LayoutBounds, problems: string[]): unknown {
  if (!isObj(mark)) return mark
  const kind = mark['kind']
  if (typeof kind === 'string' && FORBIDDEN_KINDS.has(kind)) problems.push(`${where}: la marca «${kind}» está prohibida`)
  if (mark['src'] !== undefined) problems.push(`${where}: src no admitido (no hay fotos en v1)`)
  if (mark['icon'] !== undefined) problems.push(`${where}: icon no admitido (no hay favicons en v1)`)
  const part = mark['part']
  if (part !== undefined && (typeof part !== 'string' || !PART.test(part))) problems.push(`${where}: part no válida`)
  const points = mark['points']
  if (points !== undefined) {
    const valid =
      Array.isArray(points) &&
      points.length <= LIMITS.points &&
      points.every((p) => Array.isArray(p) && p.length === 2 && finite(p[0]) && finite(p[1]) && inLayout(p[0], p[1], layout))
    if (!valid) problems.push(`${where}: points no válidos o fuera de la pantalla`)
  }
  const out: Obj = { ...mark }
  for (const key of MARK_RESOLVED) delete out[key]
  delete out['src']
  delete out['icon']
  for (const key of TARGET_KEYS) {
    const target = out[key]
    if (isObj(target)) out[key] = modelTarget(target, `${where} ${key}`, layout, problems)
  }
  return out
}

/** Valida un `overlay.draw` (payload sin validar) y devuelve el evento listo para la página. */
export function checkOverlayDraw(payload: unknown, layout: LayoutBounds): DrawCheck {
  const problems: string[] = []
  const fail = (guideId: string | null, why: string): DrawCheck => ({ ok: false, guideId, problems: [why] })
  if (!isObj(payload)) return fail(null, 'payload no es un objeto')
  const guideId = typeof payload['guide_id'] === 'string' && UUID.test(payload['guide_id']) ? payload['guide_id'].toLowerCase() : null
  if (guideId === null) return fail(null, 'guide_id no válido')

  const { turn_id: turnId, call_id: callId, seg, last, beats, edits, win, busy, fade, deep, speech_id: speechId } = payload
  if (typeof turnId !== 'string' || turnId === '' || typeof callId !== 'string') return fail(guideId, 'turn_id o call_id no válidos')
  if (!int(seg) || seg < 0 || seg >= LIMITS.beats || typeof last !== 'boolean') return fail(guideId, 'seg o last no válidos')
  if (!Array.isArray(beats) || beats.length !== 1) return fail(guideId, 'beats debe traer un solo beat')
  if (!Array.isArray(edits) || edits.length > 20) return fail(guideId, 'edits no válido')
  if (!(fade === undefined || fade === null || (finite(fade) && fade >= 0))) return fail(guideId, 'fade no válido')
  if (!(deep === undefined || deep === null || typeof deep === 'boolean')) return fail(guideId, 'deep no válido')
  if (!(speechId === undefined || speechId === null || (int(speechId) && speechId >= 0))) return fail(guideId, 'speech_id no válido')

  let winRect: RectList | null = null
  if (win !== undefined && win !== null) {
    winRect = asRect(win, layout)
    if (winRect === null) return fail(guideId, 'win no válido')
  }
  if (!Array.isArray(busy) || busy.length > MAX_BUSY) return fail(guideId, 'busy no válido')
  const busyRects: RectList[] = []
  for (const rect of busy) {
    const parsed = asRect(rect, layout)
    if (parsed === null) return fail(guideId, 'busy contiene un rect no válido')
    busyRects.push(parsed)
  }

  const modelBeats: unknown[] = []
  beats.forEach((beat: unknown, i) => {
    const where = `beat ${i + 1}`
    if (!isObj(beat)) {
      problems.push(`${where}: no es un objeto`)
      return
    }
    const { say, marks, wait, n, caption, voiced, read } = beat
    if (typeof say !== 'string' || !Array.isArray(marks)) problems.push(`${where}: say o marks no válidos`)
    if (!(wait === undefined || wait === null || wait === 'click' || wait === 'hover')) problems.push(`${where}: wait no válido`)
    if (!int(n) || typeof caption !== 'string' || typeof voiced !== 'boolean') problems.push(`${where}: n, caption o voiced no válidos`)
    if (!(read === undefined || read === null || finite(read))) problems.push(`${where}: read no válido`)
    const rest: Obj = { ...beat }
    for (const key of BEAT_RESOLVED) delete rest[key]
    if (rest['wait'] === null) delete rest['wait']
    rest['marks'] = Array.isArray(marks) ? marks.map((m, j) => modelMark(m, `${where} mark ${j + 1}`, layout, problems)) : marks
    modelBeats.push(rest)
  })
  if (problems.length > 0) return { ok: false, guideId, problems }

  const parsed = DrawArgs.safeParse({ beats: modelBeats, edit: edits })
  if (!parsed.success) {
    const issues = parsed.error.issues.slice(0, 8).map((issue) => `${issue.path.join('.')}: ${issue.message}`)
    return { ok: false, guideId, problems: issues }
  }
  const lines = checkDraw(parsed.data)
  if (lines.length > 0) return { ok: false, guideId, problems: lines }

  const event: RoamieDrawEvent = {
    type: 'draw',
    id: guideId,
    seg,
    last,
    beats: beats as Record<string, unknown>[],
    edits: edits as Record<string, unknown>[],
    win: winRect,
    busy: busyRects,
    ...(finite(fade) ? { fade } : {}),
    ...(deep === true ? { deep: true } : {}),
    ...(int(speechId) ? { speech_id: speechId } : {})
  }
  return { ok: true, event, turnId }
}
