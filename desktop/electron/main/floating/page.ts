/**
 * IPC de la página flotante (CONTRACT §4.3 y §11.3): lista blanca de comandos y de mensajes
 * `sidecar_send`, validados por forma. La página es dato no confiable: no aprueba nada.
 */
import { FLOAT_INVOKE_CMDS, FLOAT_LIMITS, type FloatInvokeCmd } from '../../shared/floating'

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const PART = /^p\d{1,4}$/
const BAR_ID = /^bar:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const WAIT_RESULTS = new Set(['clicked', 'hovered', 'timeout', 'skipped'])
/** Mensajes que en v1 se aceptan y no hacen nada (§11.3). */
const IGNORED = new Set(['reply_said', 'auto_listen', 'feedback', 'list_card', 'list_toggle', 'quiz_done', 'card_image'])
const COMMANDS: ReadonlySet<string> = new Set(FLOAT_INVOKE_CMDS)

export class FloatIpcError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'FloatIpcError'
  }
}

export type OverlayClientEvent =
  | { type: 'draw_started'; guide_id: string; seg: number }
  | { type: 'draw_done'; guide_id: string }
  | { type: 'draw_wait_done'; guide_id: string; beat: number; result: string }
  | { type: 'ink_closed'; part: string }
  | { type: 'ink_cleared' }
  | { type: 'ink_pinned'; part: string; on: boolean }
  | { type: 'ink_action'; part: string }

export type SidecarMessage =
  | { kind: 'ui_ready' }
  | { kind: 'answer'; id: string; text: string | null }
  | { kind: 'menu_stop' }
  | { kind: 'listen_cancel' }
  | { kind: 'open_link'; url: string }
  | { kind: 'overlay'; event: OverlayClientEvent }
  | { kind: 'ignored'; type: string }

type Obj = Record<string, unknown>
const isObj = (value: unknown): value is Obj => typeof value === 'object' && value !== null && !Array.isArray(value)
function bad(why: string): never {
  throw new FloatIpcError(why)
}

function guide(value: unknown): string {
  return typeof value === 'string' && UUID.test(value) ? value.toLowerCase() : bad('id de guía no válido')
}

function part(value: unknown): string {
  return typeof value === 'string' && PART.test(value) ? value : bad('part no válida')
}

function nonNegativeInt(value: unknown, field: string): number {
  return Number.isSafeInteger(value) && (value as number) >= 0 ? (value as number) : bad(`${field} no válido`)
}

/** Valida `sidecar_send({msg})`. Lanza `FloatIpcError` con un `type` fuera de la lista blanca. */
export function parseSidecar(args: unknown): SidecarMessage {
  if (!isObj(args) || !isObj(args['msg'])) bad('sidecar_send sin msg')
  const msg = (args as { msg: Obj }).msg
  let size = 0
  try {
    size = Buffer.byteLength(JSON.stringify(msg), 'utf8')
  } catch {
    bad('msg no serializable')
  }
  if (size > FLOAT_LIMITS.sidecarBytes) bad('msg por encima de 64 KiB')
  const type = msg['type']
  if (typeof type !== 'string') return bad('msg sin type')
  switch (type) {
    case 'ui_ready':
      return { kind: 'ui_ready' }
    case 'answer': {
      const id = msg['id']
      const text = msg['text']
      if (typeof id !== 'string' || id.length > 64) bad('answer: id no válido')
      if (!(text === null || (typeof text === 'string' && text.length <= FLOAT_LIMITS.answerChars))) bad('answer: text no válido')
      return { kind: 'answer', id: id as string, text: text as string | null }
    }
    case 'menu':
      if (msg['id'] !== 'stop') bad('menu: solo stop')
      return { kind: 'menu_stop' }
    case 'listen_cancel':
      return { kind: 'listen_cancel' }
    case 'open_link': {
      const url = msg['url']
      if (typeof url !== 'string' || url.length > 2000) bad('open_link: url no válida')
      return { kind: 'open_link', url: url as string }
    }
    case 'draw_started':
      return { kind: 'overlay', event: { type, guide_id: guide(msg['id']), seg: nonNegativeInt(msg['seg'], 'seg') } }
    case 'draw_done':
      return { kind: 'overlay', event: { type, guide_id: guide(msg['id']) } }
    case 'draw_wait_done': {
      const result = msg['result']
      if (typeof result !== 'string' || !WAIT_RESULTS.has(result)) bad('draw_wait_done: result no válido')
      return {
        kind: 'overlay',
        event: { type, guide_id: guide(msg['id']), beat: nonNegativeInt(msg['beat'], 'beat'), result: result as string }
      }
    }
    case 'ink_closed':
      return { kind: 'overlay', event: { type, part: part(msg['part']) } }
    case 'ink_cleared':
      return { kind: 'overlay', event: { type } }
    case 'ink_pinned':
      if (typeof msg['on'] !== 'boolean') bad('ink_pinned: on no válido')
      return { kind: 'overlay', event: { type, part: part(msg['part']), on: msg['on'] as boolean } }
    case 'ink_action':
      return { kind: 'overlay', event: { type, part: part(msg['part']) } }
    default:
      if (IGNORED.has(type) || type.startsWith('agent_')) return { kind: 'ignored', type }
      return bad(`sidecar_send: type «${type.slice(0, 40)}» no permitido`)
  }
}

export function isBarId(id: string): boolean {
  return BAR_ID.test(id)
}

function onFlag(args: unknown, cmd: string): boolean {
  if (!isObj(args) || typeof args['on'] !== 'boolean') bad(`${cmd}: on no válido`)
  return (args as { on: boolean }).on
}

export type Rect4 = readonly [number, number, number, number]

/** `set_hit_rects`: múltiplo de 4, ≤ 1024 números finitos, recortados a la ventana; sin área se descartan. */
export function parseHitRects(args: unknown, width: number, height: number): Rect4[] {
  if (!isObj(args) || !Array.isArray(args['rects'])) bad('set_hit_rects: rects no válido')
  const raw = (args as { rects: unknown[] }).rects
  if (raw.length % 4 !== 0 || raw.length > FLOAT_LIMITS.hitRectNumbers) bad('set_hit_rects: longitud no válida')
  if (!raw.every((n) => typeof n === 'number' && Number.isFinite(n))) bad('set_hit_rects: números no finitos')
  const out: Rect4[] = []
  for (let i = 0; i < raw.length; i += 4) {
    const [x, y, w, h] = raw.slice(i, i + 4) as [number, number, number, number]
    const x1 = Math.max(0, Math.floor(x))
    const y1 = Math.max(0, Math.floor(y))
    const x2 = Math.min(width, Math.ceil(x + w))
    const y2 = Math.min(height, Math.ceil(y + h))
    if (x2 > x1 && y2 > y1) out.push([x1, y1, x2 - x1, y2 - y1])
  }
  return out
}

export interface PageHost {
  windowSize(): { width: number; height: number }
  sidecar(message: SidecarMessage): void
  setHitRects(rects: Rect4[]): void
  setTyping(on: boolean): void
  escWatch(on: boolean): void
  inkWait(on: boolean): void
}

/** `float:invoke`: lista blanca de §4.3. Cualquier otro comando lanza `FloatIpcError`. */
export function handleFloatInvoke(host: PageHost, cmd: unknown, args: unknown): unknown {
  if (typeof cmd !== 'string' || !COMMANDS.has(cmd)) return bad(`float:invoke: comando «${String(cmd).slice(0, 40)}» no permitido`)
  switch (cmd as FloatInvokeCmd) {
    case 'sidecar_send':
      host.sidecar(parseSidecar(args))
      return null
    case 'set_hot':
      // Con ROAMIE_LINUX la página no lo llama: la región de entrada va por set_hit_rects.
      if (!isObj(args) || typeof args['hot'] !== 'boolean') bad('set_hot: hot no válido')
      return null
    case 'set_hit_rects': {
      const { width, height } = host.windowSize()
      host.setHitRects(parseHitRects(args, width, height))
      return null
    }
    case 'set_typing':
      host.setTyping(onFlag(args, cmd))
      return null
    case 'esc_watch':
      host.escWatch(onFlag(args, cmd))
      return null
    case 'ink_wait':
      host.inkWait(onFlag(args, cmd))
      return null
    case 'buddy':
      return false
  }
}
