/**
 * Cliente D-Bus persistente de la extensión `drakter-companion@drakter` (CONTRACT §3, §4.2).
 * Una conexión propia al bus de sesión: `Hello(token)`, señales unicast y reconexión cuando
 * el nombre `org.drakter.Companion` aparece o desaparece (`NameOwnerChanged`).
 */
import { readFile } from 'node:fs/promises'
import { join } from 'node:path'
import * as dbus from 'dbus-next'
import type { CompanionStatus } from '../../shared/floating'
import { describeError, logError } from '../log'

const SCOPE = 'floating:companion'
const NAME = 'org.drakter.Companion'
const PATH = '/org/drakter/Companion'
const IFACE = 'org.drakter.Companion1'
const ERROR_PREFIX = `${IFACE}.Error.`
const BUS = 'org.freedesktop.DBus'
const BUS_PATH = '/org/freedesktop/DBus'
const REQUIRED_VERSION = 2
const CALL_TIMEOUT_MS = 3000
const RECONNECT_MS = 5000

export interface Rect {
  readonly x: number
  readonly y: number
  readonly w: number
  readonly h: number
}

export interface CompanionWindow {
  readonly id: string | null
  readonly frame: Rect | null
  readonly monitor: number | null
  readonly pid: number | null
  readonly title: string | null
  /** Es la ventana flotante (regla de `SetFloatingWindow`). */
  readonly floating: boolean
}

export interface CompanionMonitor {
  readonly index: number
  readonly geometry: Rect
  readonly workarea: Rect
  readonly scale: number
  readonly primary: boolean
  readonly current: boolean
}

export interface SubscribeOptions {
  readonly pointer?: boolean
  readonly pointer_min_ms?: number
  readonly buttons?: boolean
  readonly gestures?: boolean
  readonly windows?: boolean
}

export interface FloatingMatch {
  readonly title: string
  readonly pid: number
  readonly monitor?: number
  readonly cover?: boolean
}

export type InputMode = 'all' | 'none' | 'rects'

export interface CompanionEvents {
  status: (status: CompanionStatus, reason: string | null) => void
  pointer: (x: number, y: number, mods: number, tUs: number) => void
  button: (button: number, pressed: boolean, x: number, y: number, tUs: number) => void
  gesture: (name: string, phase: string, tUs: number) => void
  shortcut: (name: string, phase: string, tUs: number) => void
  focus: (window: CompanionWindow) => void
  windows: (reason: string) => void
  floating: (present: boolean, window: CompanionWindow) => void
}

/** Métodos nuevos de la v2 que el prototipo del spike 02 no tiene (los simula `dev/fakeCompanion.ts`). */
export interface CompanionV2Shim {
  setFloatingFocus?(on: boolean): Promise<boolean>
}

export class CompanionError extends Error {
  constructor(
    readonly code: 'AccessDenied' | 'InvalidArgs' | 'NotFound' | 'RateLimited' | 'Failed' | 'Unavailable' | 'Timeout',
    message: string
  ) {
    super(message)
    this.name = 'CompanionError'
  }
}

const REASONS: Record<CompanionStatus, string | null> = {
  ok: null,
  missing: 'Falta la extensión de GNOME «Drakter Companion». Instálala y cierra la sesión una vez para activarla.',
  outdated: 'La extensión de GNOME «Drakter Companion» está desactualizada. Actualízala y cierra la sesión una vez.',
  denied: 'La extensión de GNOME «Drakter Companion» ha rechazado la conexión de Drakter.',
  unsupported_session: 'El modo flotante necesita una sesión de GNOME en Wayland.'
}

type Listener<K extends keyof CompanionEvents> = CompanionEvents[K]

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/** Quita los `Variant` de dbus-next (anidados). */
function plain(value: unknown): unknown {
  if (value instanceof dbus.Variant) return plain(value.value)
  if (typeof value === 'bigint') return value
  if (Array.isArray(value)) return value.map(plain)
  if (isRecord(value) && !Buffer.isBuffer(value)) {
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, plain(v)]))
  }
  return value
}

function num(value: unknown): number {
  if (typeof value === 'bigint') return Number(value)
  return typeof value === 'number' ? value : Number.NaN
}

function rect(value: unknown): Rect | null {
  if (!Array.isArray(value) || value.length !== 4) return null
  const [x, y, w, h] = value.map(num) as [number, number, number, number]
  return [x, y, w, h].every(Number.isFinite) ? { x, y, w, h } : null
}

export function parseWindow(raw: unknown): CompanionWindow {
  const d = isRecord(raw) ? raw : {}
  const id = d['id']
  return {
    id: typeof id === 'bigint' || typeof id === 'number' ? String(id) : null,
    frame: rect(d['frame']),
    monitor: Number.isFinite(num(d['monitor'])) ? num(d['monitor']) : null,
    pid: Number.isFinite(num(d['pid'])) ? num(d['pid']) : null,
    title: typeof d['title'] === 'string' ? d['title'] : null,
    floating: d['floating'] === true
  }
}

function parseMonitor(raw: unknown): CompanionMonitor | null {
  if (!isRecord(raw)) return null
  const geometry = rect(raw['geometry'])
  const workarea = rect(raw['workarea'])
  const index = num(raw['index'])
  if (!geometry || !workarea || !Number.isInteger(index)) return null
  const scale = num(raw['scale'])
  return {
    index,
    geometry,
    workarea,
    scale: Number.isFinite(scale) ? scale : 1,
    primary: raw['primary'] === true,
    current: raw['current'] === true
  }
}

function errorCode(error: unknown): CompanionError['code'] {
  if (error instanceof dbus.DBusError && typeof error.type === 'string') {
    if (error.type.startsWith(ERROR_PREFIX)) {
      const code = error.type.slice(ERROR_PREFIX.length)
      if (code === 'AccessDenied' || code === 'InvalidArgs' || code === 'NotFound' || code === 'RateLimited') return code
    }
    if (error.type === 'org.freedesktop.DBus.Error.InvalidArgs') return 'InvalidArgs'
    if (error.type === 'org.freedesktop.DBus.Error.UnknownMethod') return 'Failed'
  }
  return 'Failed'
}

function variants(options: Readonly<Record<string, unknown>>): Record<string, dbus.Variant> {
  const out: Record<string, dbus.Variant> = {}
  for (const [key, value] of Object.entries(options)) {
    if (value === undefined) continue
    if (typeof value === 'boolean') out[key] = new dbus.Variant('b', value)
    else if (typeof value === 'string') out[key] = new dbus.Variant('s', value)
    else if (typeof value === 'number' && key === 'pointer_min_ms') out[key] = new dbus.Variant('u', Math.max(0, Math.round(value)))
    else if (typeof value === 'number') out[key] = new dbus.Variant('i', Math.round(value))
  }
  return out
}

export class CompanionClient {
  private bus: dbus.MessageBus | null = null
  private owner: string | null = null
  private generation = 0
  private reconnectTimer: NodeJS.Timeout | null = null
  private stopped = false
  private readonly listeners: { [K in keyof CompanionEvents]: Set<Listener<K>> } = {
    status: new Set(),
    pointer: new Set(),
    button: new Set(),
    gesture: new Set(),
    shortcut: new Set(),
    focus: new Set(),
    windows: new Set(),
    floating: new Set()
  }
  private current: CompanionStatus = 'missing'
  private currentReason: string | null = REASONS.missing
  private baseSubscription: SubscribeOptions = { windows: true, gestures: true }

  /** Versión mínima aceptada: 2 (la de este contrato); el doble de desarrollo la baja a 1. */
  minVersion = REQUIRED_VERSION
  shim: CompanionV2Shim | null = null
  version = 0

  get status(): CompanionStatus {
    return this.current
  }

  get reason(): string | null {
    return this.currentReason
  }

  on<K extends keyof CompanionEvents>(event: K, listener: Listener<K>): () => void {
    this.listeners[event].add(listener)
    return () => {
      this.listeners[event].delete(listener)
    }
  }

  /** Para el doble de desarrollo: inyecta una señal como si viniera de la extensión. */
  emit<K extends keyof CompanionEvents>(event: K, ...args: Parameters<CompanionEvents[K]>): void {
    for (const listener of [...this.listeners[event]]) {
      try {
        ;(listener as (...a: Parameters<CompanionEvents[K]>) => void)(...args)
      } catch (error) {
        logError(SCOPE, `Oyente de ${event} fallido`, describeError(error))
      }
    }
  }

  /** Suscripción que se restablece en cada `Hello` (desde el arranque: ventanas y atajos). */
  setBaseSubscription(options: SubscribeOptions): void {
    this.baseSubscription = options
  }

  start(): void {
    this.stopped = false
    if (process.platform !== 'linux' || !process.env['DBUS_SESSION_BUS_ADDRESS'] || !process.env['WAYLAND_DISPLAY']) {
      this.setStatus('unsupported_session')
      return
    }
    const session = process.env['XDG_SESSION_TYPE']
    if (session && session !== 'wayland') {
      this.setStatus('unsupported_session')
      return
    }
    this.connect()
  }

  stop(): void {
    this.stopped = true
    this.cancelReconnect()
    this.dropBus()
  }

  private setStatus(status: CompanionStatus, detail?: string): void {
    const reason = REASONS[status] ?? null
    if (status === this.current && reason === this.currentReason) return
    this.current = status
    this.currentReason = reason
    if (detail) logError(SCOPE, `Extensión: ${status}`, detail)
    this.emit('status', status, reason)
  }

  private cancelReconnect(): void {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.reconnectTimer = null
  }

  private scheduleReconnect(): void {
    if (this.stopped || this.reconnectTimer) return
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this.connect()
    }, RECONNECT_MS)
  }

  private dropBus(): void {
    this.generation++
    this.owner = null
    const bus = this.bus
    this.bus = null
    if (bus) {
      try {
        bus.disconnect()
      } catch {
        // ya cerrado
      }
    }
  }

  private connect(): void {
    if (this.stopped) return
    this.dropBus()
    const generation = this.generation
    let bus: dbus.MessageBus
    try {
      bus = dbus.sessionBus()
    } catch (error) {
      this.setStatus('unsupported_session', describeError(error))
      return
    }
    this.bus = bus
    bus.on('error', (error: unknown) => {
      if (generation !== this.generation) return
      logError(SCOPE, 'Bus de sesión perdido', describeError(error))
      this.dropBus()
      this.setStatus('missing')
      this.scheduleReconnect()
    })
    bus.on('message', (msg: dbus.Message) => {
      if (generation === this.generation) this.onMessage(msg)
    })
    void this.watchName(bus, generation)
  }

  private async busCall(bus: dbus.MessageBus, member: string, signature: string, body: unknown[]): Promise<unknown[]> {
    const reply = await bus.call(
      new dbus.Message({ destination: BUS, path: BUS_PATH, interface: BUS, member, signature, body })
    )
    return reply?.body ?? []
  }

  private async watchName(bus: dbus.MessageBus, generation: number): Promise<void> {
    try {
      await this.busCall(bus, 'AddMatch', 's', [
        `type='signal',sender='${BUS}',interface='${BUS}',member='NameOwnerChanged',arg0='${NAME}'`
      ])
      await this.busCall(bus, 'AddMatch', 's', [`type='signal',interface='${IFACE}',path='${PATH}'`])
      let owner = ''
      try {
        const [value] = await this.busCall(bus, 'GetNameOwner', 's', [NAME])
        owner = typeof value === 'string' ? value : ''
      } catch {
        owner = ''
      }
      if (generation !== this.generation) return
      await this.onOwner(owner, generation)
    } catch (error) {
      if (generation !== this.generation) return
      logError(SCOPE, 'No se pudo vigilar el nombre de la extensión', describeError(error))
      this.setStatus('missing')
      this.scheduleReconnect()
    }
  }

  private async onOwner(owner: string, generation: number): Promise<void> {
    this.owner = owner || null
    if (!owner) {
      this.setStatus('missing')
      return
    }
    try {
      const [versionVariant] = await this.rawCall('org.freedesktop.DBus.Properties', 'Get', 'ss', [IFACE, 'Version'])
      const version = num(plain(versionVariant))
      if (generation !== this.generation) return
      this.version = Number.isFinite(version) ? version : 0
      if (this.version < this.minVersion) {
        this.setStatus('outdated', `versión ${this.version}`)
        return
      }
      const token = await this.readToken()
      if (token === null) {
        this.setStatus('denied', 'sin token en $XDG_RUNTIME_DIR/drakter-companion/token')
        return
      }
      await this.call('Hello', 's', [token])
      if (generation !== this.generation) return
      await this.subscribe(this.baseSubscription)
      this.setStatus('ok')
    } catch (error) {
      if (generation !== this.generation) return
      const code = error instanceof CompanionError ? error.code : errorCode(error)
      this.setStatus(code === 'AccessDenied' ? 'denied' : 'missing', describeError(error))
    }
  }

  private async readToken(): Promise<string | null> {
    const runtime = process.env['XDG_RUNTIME_DIR']
    if (!runtime) return null
    try {
      const token = (await readFile(join(runtime, 'drakter-companion', 'token'), 'utf8')).trim()
      return token === '' ? null : token
    } catch {
      return null
    }
  }

  private onMessage(msg: dbus.Message): void {
    if (msg.type !== dbus.MessageType.SIGNAL) return
    if (msg.interface === BUS && msg.member === 'NameOwnerChanged' && msg.body[0] === NAME) {
      const owner = typeof msg.body[2] === 'string' ? msg.body[2] : ''
      void this.onOwner(owner, this.generation)
      return
    }
    if (msg.interface !== IFACE || msg.path !== PATH || this.owner === null || msg.sender !== this.owner) return
    if (this.current !== 'ok') return
    const b = msg.body.map(plain)
    switch (msg.member) {
      case 'PointerMoved':
        this.emit('pointer', num(b[0]), num(b[1]), num(b[2]), num(b[3]))
        break
      case 'Button':
        this.emit('button', num(b[0]), b[1] === true, num(b[2]), num(b[3]), num(b[4]))
        break
      case 'Gesture':
        this.emit('gesture', String(b[0]), String(b[1]), num(b[2]))
        break
      case 'Shortcut':
        this.emit('shortcut', String(b[0]), String(b[1]), num(b[2]))
        break
      case 'FocusChanged':
        this.emit('focus', parseWindow(b[0]))
        break
      case 'WindowsChanged':
        this.emit('windows', String(b[0]))
        break
      case 'FloatingWindowChanged':
        this.emit('floating', b[0] === true, parseWindow(b[1]))
        break
      default:
        break
    }
  }

  private async rawCall(iface: string, member: string, signature: string, body: unknown[]): Promise<unknown[]> {
    const bus = this.bus
    if (!bus || !this.owner) throw new CompanionError('Unavailable', 'La extensión no está conectada')
    let timer: NodeJS.Timeout | undefined
    const timeout = new Promise<never>((_resolve, reject) => {
      timer = setTimeout(() => reject(new CompanionError('Timeout', `${member}: sin respuesta`)), CALL_TIMEOUT_MS)
    })
    try {
      const message = new dbus.Message({ destination: NAME, path: PATH, interface: iface, member, signature, body })
      const reply = await Promise.race([bus.call(message), timeout])
      return reply?.body ?? []
    } catch (error) {
      if (error instanceof CompanionError) throw error
      throw new CompanionError(errorCode(error), `${member}: ${describeError(error)}`)
    } finally {
      clearTimeout(timer)
    }
  }

  private call(member: string, signature: string, body: unknown[]): Promise<unknown[]> {
    return this.rawCall(IFACE, member, signature, body)
  }

  async getPointer(): Promise<{ x: number; y: number; mods: number; tUs: number }> {
    const b = (await this.call('GetPointer', '', [])).map(plain)
    return { x: num(b[0]), y: num(b[1]), mods: num(b[2]), tUs: num(b[3]) }
  }

  async getMonitors(): Promise<CompanionMonitor[]> {
    const [list] = (await this.call('GetMonitors', '', [])).map(plain)
    return Array.isArray(list) ? list.map(parseMonitor).filter((m): m is CompanionMonitor => m !== null) : []
  }

  /** Ventanas visibles de arriba abajo (aquí solo para leer el frame real de la flotante). */
  async listWindows(): Promise<CompanionWindow[]> {
    const [list] = (await this.call('ListWindows', '', [])).map(plain)
    return Array.isArray(list) ? list.map(parseWindow) : []
  }

  async subscribe(options: SubscribeOptions): Promise<void> {
    await this.call('Subscribe', 'a{sv}', [variants(options as Record<string, unknown>)])
  }

  /** `{}` libera la ventana. */
  async setFloatingWindow(match: FloatingMatch | Record<string, never>): Promise<boolean> {
    const [found] = await this.call('SetFloatingWindow', 'a{sv}', [variants(match as Record<string, unknown>)])
    return found === true
  }

  async setInputRegion(mode: InputMode, rects: readonly (readonly [number, number, number, number])[]): Promise<string> {
    const [applied] = await this.call('SetInputRegion', 'sa(iiii)', [mode, rects.map((r) => [...r])])
    return typeof applied === 'string' ? applied : ''
  }

  async setEscapeGrab(enabled: boolean): Promise<void> {
    await this.call('SetEscapeGrab', 'b', [enabled])
  }

  /** Activa una ventana cliente por su `id` (`false` si no existe o es la flotante). */
  async activateWindow(id: string): Promise<boolean> {
    const [ok] = await this.call('ActivateWindow', 't', [BigInt(id)])
    return ok === true
  }

  /** Solo el dueño: con `true` la flotante no se pinta (opacidad 0) y deja pasar todos los clics. */
  async setFloatingHidden(hidden: boolean): Promise<boolean> {
    const [ok] = await this.call('SetFloatingHidden', 'b', [hidden])
    return ok === true
  }

  async setFloatingFocus(on: boolean): Promise<boolean> {
    if (this.shim?.setFloatingFocus) return this.shim.setFloatingFocus(on)
    const [ok] = await this.call('SetFloatingFocus', 'b', [on])
    return ok === true
  }
}
