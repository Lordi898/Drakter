/**
 * Adaptador de eventos de Drakter → mensajes de Roamies (CONTRACT §4.5, §11.4, §11.8, §12).
 * Recibe los sobres del WebSocket ya parseados (dato sin validar): comprueba la forma de lo que usa.
 */
import { checkOverlayDraw, type LayoutBounds } from './draw/validate'
import { logError } from '../log'

const SCOPE = 'floating:adapter'
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const PART = /^p\d{1,4}$/
const MAX_ERROR_CHARS = 200
const MAX_SAY_CHARS = 200
const MAX_DELTA_CHARS = 4000

export const PERMISSION_BUBBLE = 'Necesito tu permiso: mira el cuadro de diálogo'
export const OFFLINE_BUBBLE = 'Me he quedado sin conexión con mi núcleo.'

/** Tipos que main consume (§4.5). */
const PREFIXES = ['agent.', 'overlay.'] as const
const TYPES: ReadonlySet<string> = new Set([
  'chat.user_message',
  'confirmation.requested',
  'confirmation.resolved',
  'notification.created',
  'voice.playback',
  'voice.state',
  'ui.floating',
  'system.health_changed',
  'system.resync_required'
])

export function isFloatingEventType(type: string): boolean {
  return TYPES.has(type) || PREFIXES.some((prefix) => type.startsWith(prefix))
}

export interface EventEnvelopeLite {
  readonly type: string
  readonly payload: Record<string, unknown>
}

export type RoamieMessage = { readonly kind: string } & Readonly<Record<string, unknown>>

export type FloatVoiceMessage =
  | { readonly t: 'pb'; readonly id: number; readonly turn: string; readonly state: 'started' | 'sentence_done' | 'finished' | 'interrupted' }
  | { readonly t: 'lv'; readonly out: number; readonly in: number }
  | { readonly t: 'stop' }

export interface UiFloatingRequest {
  readonly action: 'on' | 'off' | 'toggle' | null
  readonly size: 'default' | 'small' | 'cursor' | null
  readonly pin: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'center' | 'release' | null
  readonly source: 'voice' | 'agent'
}

export interface AdapterHost {
  /** Modo activo y página lista (`ui_ready`). */
  isLive(): boolean
  isActive(): boolean
  host(msg: RoamieMessage): void
  voice(msg: FloatVoiceMessage): void
  layout(): LayoutBounds
  /** Si el puntero está en otro monitor, mueve la flotante allí (§4.2). */
  followPointer(): void
  followRect(x: number, y: number): void
  uiFloating(request: UiFloatingRequest): void
  /** Aprobación nativa (approvals.ts) con el modo activo. */
  approve(actionId: string): void
  copy(text: string): void
  /** Un `overlay.draw` descartado: avisar al backend para que la guía no se quede colgada. */
  drawDiscarded(guideId: string): void
}

type Obj = Record<string, unknown>
const str = (value: unknown): string | null => (typeof value === 'string' ? value : null)
const isObj = (value: unknown): value is Obj => typeof value === 'object' && value !== null && !Array.isArray(value)

/** Una línea, sin caracteres de control, recortada. */
function line(text: string, max: number): string {
  return text
    .replace(/[\p{Cc}\p{Cf}\p{Zl}\p{Zp}]+/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, max)
}

type Anim = { tool: string; variant: string; label: string; detail: string } | null

/** Chips de herramienta (§11.8). */
export function toolAnim(tool: string, source: string): Anim {
  if (source === 'hermes') return null
  if (tool === 'draw' || tool === 'guide_wait' || tool.startsWith('ui_') || tool.startsWith('voice_')) return null
  if (tool === 'look_screen') return { tool: 'look', variant: 'screen', label: 'mirando', detail: 'tu pantalla' }
  if (tool === 'read_window' || tool === 'list_windows') return { tool: 'read', variant: 'search', label: 'leyendo', detail: 'la ventana' }
  if (tool === 'act_in_app') return { tool: 'write', variant: 'edit', label: 'trabajando en', detail: 'la ventana' }
  if (tool === 'open_target') return { tool: 'run', variant: 'ok', label: 'abriendo', detail: '' }
  if (tool === 'jobs_start') return { tool: 'run', variant: 'progress', label: 'lanzando', detail: 'un trabajo' }
  if (tool.startsWith('delete_') || tool === 'forget_memory') {
    return { tool: 'write', variant: 'crumble', label: 'borrando', detail: '(con tu permiso)' }
  }
  if (/^(search|get|list)_/.test(tool) || tool === 'check_availability' || tool === 'read_resource') {
    return { tool: 'read', variant: 'search', label: 'consultando', detail: 'tus datos' }
  }
  if (/^(create|update|complete|archive|register|add|set|move)_/.test(tool) || tool === 'propose_memory') {
    return { tool: 'write', variant: 'edit', label: 'guardando', detail: 'en tu espacio' }
  }
  return null
}

const EMOTES: Readonly<Record<string, string>> = {
  happy: 'hype',
  excited: 'hype',
  sad: 'upset',
  regretful: 'upset',
  confident: 'motivate'
}

const PB_STATES = new Set(['started', 'sentence_done', 'finished', 'interrupted'])
const SIZES = new Set(['default', 'small', 'cursor'])
const PINS = new Set(['top-left', 'top-right', 'bottom-left', 'bottom-right', 'center', 'release'])
const ACTIONS = new Set(['on', 'off', 'toggle'])

function rectList(value: unknown): [number, number, number, number] | null {
  if (!Array.isArray(value) || value.length !== 4 || !value.every((n) => typeof n === 'number' && Number.isFinite(n))) return null
  return value as [number, number, number, number]
}

export class EventAdapter {
  /** Sesión de chat activa: la última vista en `agent.*`/`chat.*`. */
  sessionId: string | null = null
  /** Turno en curso (entre `turn_started` y `turn_finished`). */
  turnId: string | null = null
  /** Guía con dibujo en pantalla (el último `overlay.draw` aceptado). */
  guideId: string | null = null
  private readonly lastSpeech = new Map<string, number>()
  private listening = false
  private offlineSaid = false

  constructor(private readonly host: AdapterHost) {}

  /** La voz está escuchando: los niveles del micrófono van a la píldora. */
  get hearing(): boolean {
    return this.listening
  }

  /** Al activar el modo: olvida lo que dependía de la página anterior. */
  resetPage(): void {
    this.guideId = null
    this.listening = false
    this.offlineSaid = false
  }

  /** Main perdió el backend (WS caído o proceso caído). */
  offline(): void {
    if (!this.host.isLive() || this.offlineSaid) return
    this.offlineSaid = true
    this.host.host({ kind: 'say', text: OFFLINE_BUBBLE, mood: 'concerned' })
    if (this.turnId) this.host.host({ kind: 'agent', e: { type: 'error', message: OFFLINE_BUBBLE, speech: null } })
  }

  /** De vuelta: saluda otra vez (§12, offline). */
  online(): void {
    if (!this.offlineSaid) return
    this.offlineSaid = false
    if (this.host.isLive()) this.host.host({ kind: 'greet' })
  }

  onEvent(envelope: EventEnvelopeLite): void {
    const { type, payload } = envelope
    try {
      this.dispatch(type, payload)
    } catch (error) {
      logError(SCOPE, `Evento ${type} no procesado`, error instanceof Error ? error.message : String(error))
    }
  }

  private trackSession(p: Obj): void {
    const session = str(p['session_id'])
    if (session && UUID.test(session)) this.sessionId = session
  }

  private agent(e: Obj): void {
    if (this.host.isLive()) this.host.host({ kind: 'agent', e })
  }

  private dispatch(type: string, p: Obj): void {
    if (type.startsWith('agent.') || type.startsWith('chat.')) this.trackSession(p)
    switch (type) {
      case 'agent.turn_started': {
        this.turnId = str(p['turn_id'])
        if (this.host.isLive()) this.host.followPointer()
        this.agent({ type: 'start', agentish: false })
        return
      }
      case 'agent.message_delta': {
        const delta = str(p['delta'])
        if (delta) this.agent({ type: 'text', text: delta.slice(0, MAX_DELTA_CHARS) })
        return
      }
      case 'agent.tool_started': {
        const tool = str(p['tool'])
        const id = str(p['call_id'])
        if (tool && id) this.agent({ type: 'tool', id, anim: toolAnim(tool, str(p['source']) ?? 'drakter') })
        return
      }
      case 'agent.tool_completed': {
        const id = str(p['call_id'])
        if (id) this.agent({ type: 'tool_end', id, isError: p['error'] === true })
        return
      }
      case 'agent.expression_changed': {
        const action = EMOTES[str(p['expression']) ?? '']
        if (action) this.agent({ type: 'emote', action })
        return
      }
      case 'agent.error': {
        const message = line(str(p['message']) ?? 'Algo ha fallado.', MAX_ERROR_CHARS) || 'Algo ha fallado.'
        this.agent({ type: 'error', message, speech: null })
        return
      }
      case 'agent.status_changed': {
        const state = str(p['state'])
        if (state === 'listening' && !this.listening) {
          this.listening = true
          if (this.host.isLive()) this.host.followPointer()
          if (this.host.isLive()) this.host.host({ kind: 'voice', type: 'state', state: 'listening', mode: 'handsfree' })
        } else if (state !== 'listening' && this.listening) {
          this.listening = false
          if (this.host.isLive()) this.host.host({ kind: 'voice', type: 'state', state: 'idle' })
        }
        return
      }
      case 'agent.turn_finished': {
        const turn = str(p['turn_id'])
        const outcome = str(p['outcome'])
        if (outcome === 'interrupted' || outcome === 'cancelled') {
          this.host.voice({ t: 'stop' })
          if (this.guideId) this.agent({ type: 'ink_clear', stop: true })
          this.agent({ type: 'done', speech: null })
        } else {
          const speech = turn ? this.lastSpeech.get(turn) ?? null : null
          this.agent({ type: 'done', speech })
        }
        if (turn) this.lastSpeech.delete(turn)
        if (turn === this.turnId) this.turnId = null
        return
      }
      case 'chat.user_message': {
        const text = str(p['text'])
        if (p['input_source'] === 'voice' && text && this.host.isLive()) {
          this.host.host({ kind: 'voice', type: 'final', text: text.slice(0, MAX_DELTA_CHARS) })
        }
        return
      }
      case 'confirmation.requested': {
        const actionId = str(p['action_id'])
        if (!this.host.isActive() || !actionId || !UUID.test(actionId)) return
        this.host.approve(actionId)
        if (this.host.isLive()) this.host.host({ kind: 'say', text: PERMISSION_BUBBLE, mood: 'concerned' })
        return
      }
      case 'notification.created': {
        const title = line(str(p['title']) ?? '', MAX_SAY_CHARS)
        if (!title || !this.host.isLive()) return
        this.host.host({ kind: 'say', text: title, mood: 'determined' })
        if (p['kind'] === 'reminder') this.agent({ type: 'emote', action: 'remind' })
        return
      }
      case 'voice.playback': {
        const turn = str(p['turn_id'])
        const id = p['speech_id']
        const state = str(p['state'])
        if (!turn || !Number.isSafeInteger(id) || !state || !PB_STATES.has(state)) return
        this.lastSpeech.set(turn, id as number)
        if (this.host.isLive()) {
          this.host.voice({ t: 'pb', id: id as number, turn, state: state as 'started' | 'sentence_done' | 'finished' | 'interrupted' })
        }
        return
      }
      case 'ui.floating': {
        const action = str(p['action'])
        const size = str(p['size'])
        const pin = str(p['pin'])
        const source = str(p['source'])
        if (source !== 'voice' && source !== 'agent') return
        this.host.uiFloating({
          action: action && ACTIONS.has(action) ? (action as UiFloatingRequest['action']) : null,
          size: size && SIZES.has(size) ? (size as UiFloatingRequest['size']) : null,
          pin: pin && PINS.has(pin) ? (pin as UiFloatingRequest['pin']) : null,
          source
        })
        return
      }
      case 'overlay.draw':
        this.onDraw(p)
        return
      case 'overlay.ink_clear': {
        const e: Obj = { type: 'ink_clear' }
        if (p['screen'] === true) e['screen'] = true
        if (p['stop'] === true) e['stop'] = true
        if (p['all'] === true) e['all'] = true
        const parts = p['parts']
        if (Array.isArray(parts)) e['parts'] = parts.filter((x): x is string => typeof x === 'string' && PART.test(x)).slice(0, 100)
        if (p['stop'] === true || p['all'] === true || (str(p['guide_id']) !== null && p['guide_id'] === this.guideId)) {
          this.guideId = null
        }
        this.agent(e)
        return
      }
      case 'overlay.ink_stale':
        this.agent({ type: 'ink_stale' })
        return
      case 'overlay.hands': {
        if (!this.host.isLive()) return
        const step = p['step']
        if (isObj(step)) {
          const bounds = rectList(step['bounds'])
          if (bounds) this.host.host({ kind: 'hands', step: { bounds, hover: step['hover'] === true } })
        } else if (typeof p['on'] === 'boolean') {
          this.host.host({ kind: 'hands', on: p['on'] })
        }
        return
      }
      case 'overlay.trail': {
        const steps = p['steps']
        const head = str(p['head'])
        if (!Array.isArray(steps) || head === null) return
        const clean = steps.slice(0, 8).flatMap((s: unknown) => {
          if (!isObj(s) || typeof s['text'] !== 'string') return []
          const state = ['', 'now', 'ok', 'bad'].includes(String(s['state'])) ? s['state'] : ''
          return [{ text: line(s['text'], 120), state, ...(typeof s['why'] === 'string' ? { why: line(s['why'], 120) } : {}) }]
        })
        this.agent({ type: 'trail', steps: clean, head: line(head, 120), final: p['final'] === true })
        return
      }
      case 'overlay.clipboard': {
        const text = str(p['text'])
        if (text === null || !this.host.isActive()) return
        this.host.copy(text.slice(0, 20_000))
        if (this.host.isLive()) this.host.host({ kind: 'say', text: 'Copiado', mood: 'happy' })
        return
      }
      case 'system.health_changed': {
        const component = str(p['component'])
        if ((component === 'backend' || component === 'hermes') && p['status'] === 'down') this.offline()
        else if ((component === 'backend' || component === 'hermes') && p['status'] === 'ok') this.online()
        return
      }
      default:
        return
    }
  }

  private onDraw(p: Obj): void {
    if (!this.host.isActive()) return
    const result = checkOverlayDraw(p, this.host.layout())
    if (!result.ok) {
      logError(SCOPE, 'overlay.draw descartado', result.problems.join(' | '))
      if (result.guideId) this.host.drawDiscarded(result.guideId)
      return
    }
    if (!this.host.isLive()) {
      this.host.drawDiscarded(result.event.id)
      return
    }
    this.guideId = result.event.id
    const first = result.event.beats[0]
    const marks = isObj(first) && Array.isArray(first['marks']) ? first['marks'] : []
    for (const mark of marks) {
      const at = isObj(mark) && isObj(mark['at']) ? rectList(mark['at']['rect']) : null
      if (at) {
        this.host.followRect(at[0] + at[2] / 2, at[1] + at[3] / 2)
        break
      }
    }
    this.host.host({ kind: 'agent', e: result.event })
  }
}
