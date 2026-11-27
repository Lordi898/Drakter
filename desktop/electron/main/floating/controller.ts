/**
 * `FloatingController` (CONTRACT §4.2): único dueño del estado del modo flotante. Une el cliente
 * D-Bus de la extensión, la ventana flotante, el IPC de la página y los eventos del backend.
 */
import { randomUUID } from 'node:crypto'
import { BrowserWindow, clipboard, Notification, shell, type IpcMainInvokeEvent } from 'electron'
import {
  FLOAT_CHANNELS,
  FLOAT_LIMITS,
  FLOATING_URL,
  type CompanionStatus,
  type FloatingAction,
  type FloatingSource,
  type FloatingState
} from '../../shared/floating'
import { FLOATING_CHANNELS } from '../../shared/bridge'
import { callNamedOperation } from '../apiProxy'
import { APPROVAL_TITLE, requestApproval } from '../approvals'
import type { BackendHost } from '../host-types'
import { describeError, logError } from '../log'
import { activateVoice } from '../tray'
import { focusMainWindow, getMainWindow } from '../window'
import { EventAdapter, type EventEnvelopeLite, type FloatVoiceMessage, type RoamieMessage, type UiFloatingRequest } from './adapter'
import { cancelTurn, postOverlayEvent, postPresence, readFloatingSettings, sendChatMessage, type PresenceBody } from './backend'
import { CompanionClient, type CompanionMonitor, type Rect, type SubscribeOptions } from './companion'
import { installFakeCompanion } from './dev/fakeCompanion'
import { checkUrl } from './draw/safety.mjs'
import type { LayoutBounds } from './draw/validate'
import { handleFloatInvoke, isBarId, type PageHost, type Rect4, type SidecarMessage } from './page'
import { createFloatingWindow } from './window'

const SCOPE = 'floating'
const FLOATING_WAIT_MS = 3000
const UI_READY_WAIT_MS = 5000
const RELEASE_WAIT_MS = 1000
const SAFE_EVERY_MS = 2000
const PRESENCE_EVERY_MS = 30_000
const HIT_RECTS_GAP_MS = 1000 / FLOAT_LIMITS.hitRectsPerSecond
const ASK_PLACEHOLDER = 'Pregúntame lo que quieras…'
const BASE_SUBSCRIPTION: SubscribeOptions = { windows: true, gestures: true }

function notify(title: string, body: string): void {
  try {
    if (Notification.isSupported()) new Notification({ title, body }).show()
  } catch (error) {
    logError(SCOPE, 'Notificación fallida', describeError(error))
  }
}

function contains(rect: Rect, x: number, y: number): boolean {
  return x >= rect.x && y >= rect.y && x < rect.x + rect.w && y < rect.y + rect.h
}

function deadline<T>(promise: Promise<T>, ms: number, what: string): Promise<T> {
  let timer: NodeJS.Timeout | undefined
  return Promise.race([
    promise,
    new Promise<never>((_resolve, reject) => {
      timer = setTimeout(() => reject(new Error(`${what}: sin respuesta en ${ms} ms`)), ms)
    })
  ]).finally(() => clearTimeout(timer))
}

export class FloatingController {
  readonly companion = new CompanionClient()
  private readonly adapter: EventAdapter
  private active = false
  private busy: FloatingState['busy'] = null
  private reason: string | null = null
  private queue: Promise<unknown> = Promise.resolve()

  private win: BrowserWindow | null = null
  private frame: Rect | null = null
  private monitors: CompanionMonitor[] = []
  private monitor: CompanionMonitor | null = null
  private wasVisible = false
  private uiReady = false
  private uiReadyPending = false
  private greeted = false
  private inkWaiting = false
  private barId: string | null = null
  private floatingWaiter: ((present: boolean) => void) | null = null
  private readyWaiter: (() => void) | null = null

  private safeTimer: NodeJS.Timeout | null = null
  private presenceTimer: NodeJS.Timeout | null = null
  private rectsTimer: NodeJS.Timeout | null = null
  private pendingRects: Rect4[] | null = null
  private lastRectsAt = 0
  private clientRegionLogged = false
  private levelStamps: number[] = []
  private stateListeners = new Set<(state: FloatingState) => void>()

  constructor(private readonly backend: BackendHost) {
    this.adapter = new EventAdapter({
      isLive: () => this.live,
      isActive: () => this.active,
      host: (msg) => this.toPage(msg),
      voice: (msg) => this.toVoice(msg),
      layout: () => this.layout(),
      followPointer: () => void this.followPointer(),
      followRect: (x, y) => void this.followAt(x, y),
      uiFloating: (request) => this.onUiFloating(request),
      approve: (actionId) => this.approve(actionId),
      copy: (text) => clipboard.writeText(text),
      drawDiscarded: (guideId) => void postOverlayEvent(this.backend, { type: 'draw_done', guide_id: guideId })
    })
    installFakeCompanion(this.companion, { focusFloating: (on) => this.fakeFocus(on) })
    this.companion.setBaseSubscription(BASE_SUBSCRIPTION)
    this.companion.on('status', (status) => this.onCompanionStatus(status))
    this.companion.on('shortcut', (name, phase) => this.onShortcut(name, phase))
    this.companion.on('gesture', (name, phase) => {
      if (name === 'talk' && phase === 'hold') void activateVoice(this.backend, 'hotkey')
    })
    this.companion.on('pointer', (x, y, _mods, tUs) => this.onPointer(x, y, tUs))
    this.companion.on('button', (button, pressed, x, y, tUs) => this.onButton(button, pressed, x, y, tUs))
    this.companion.on('floating', (present, window) => {
      if (present && window.frame && window.frame.w > 0 && window.frame.h > 0) this.frame = window.frame
      this.floatingWaiter?.(present)
      if (present) setTimeout(() => void this.refreshFrame(), 150)
    })
    this.companion.on('windows', (reason) => {
      if (reason === 'monitors') void this.refreshMonitors()
    })
  }

  private get live(): boolean {
    return this.active && this.uiReady && this.win !== null && !this.win.isDestroyed()
  }

  // ------------------------------------------------------------------ estado

  getState(): FloatingState {
    const companion: CompanionStatus = this.companion.status
    const available = companion === 'ok'
    return {
      active: this.active,
      available,
      companion,
      busy: this.busy,
      reason: this.reason ?? (available ? null : this.companion.reason)
    }
  }

  onState(listener: (state: FloatingState) => void): () => void {
    this.stateListeners.add(listener)
    return () => {
      this.stateListeners.delete(listener)
    }
  }

  private publish(): void {
    const state = this.getState()
    getMainWindow()?.webContents.send(FLOATING_CHANNELS.state, state)
    for (const listener of [...this.stateListeners]) listener(state)
    void this.postPresence()
  }

  private presenceBody(): PresenceBody {
    const m = this.monitor
    return {
      active: this.active,
      ready: this.live,
      companion: this.companion.status,
      bridge_version: 1,
      monitor: m
        ? { index: m.index, geometry: { ...m.geometry }, workarea: { ...m.workarea }, scale: m.scale, primary: m.primary }
        : null
    }
  }

  private postPresence(): Promise<void> {
    return postPresence(this.backend, this.presenceBody())
  }

  start(): void {
    this.companion.start()
    this.presenceTimer = setInterval(() => void this.postPresence(), PRESENCE_EVERY_MS)
    this.backend.onConnection((connection) => {
      if (connection.state === 'ready') {
        this.adapter.online()
        void this.postPresence()
      } else {
        this.adapter.offline()
      }
    })
    // La ventana principal recarga: vuelve a saber si hay demanda de niveles.
    const main = getMainWindow()
    main?.webContents.on('did-finish-load', () => this.sendLevelsDemand())
  }

  dispose(): void {
    if (this.presenceTimer) clearInterval(this.presenceTimer)
    this.presenceTimer = null
    if (this.active) void this.teardownWindow().finally(() => this.companion.stop())
    else this.companion.stop()
  }

  // ------------------------------------------------------------------ activar / desactivar

  set(action: FloatingAction, source: FloatingSource): Promise<FloatingState> {
    const run = this.queue.then(async () => {
      const on = action === 'toggle' ? !this.active : action === 'on'
      if (on && !this.active) await this.activate(source)
      else if (!on && this.active) await this.deactivate()
      return this.getState()
    })
    this.queue = run.catch(() => undefined)
    return run
  }

  private onCompanionStatus(status: CompanionStatus): void {
    if (status !== 'ok' && this.active) {
      notify('Modo flotante desactivado', 'Se ha perdido la conexión con la extensión de GNOME.')
      void this.set('off', 'ui')
    }
    this.publish()
  }

  private async activate(source: FloatingSource): Promise<void> {
    this.reason = null
    if (this.companion.status !== 'ok') {
      this.publish()
      if (source !== 'agent' && source !== 'voice') focusMainWindow()
      notify('Modo flotante no disponible', this.companion.reason ?? 'Falta la extensión de GNOME.')
      return
    }
    this.busy = 'activating'
    this.publish()
    try {
      const [monitors, pointer] = await Promise.all([this.companion.getMonitors(), this.companion.getPointer()])
      const monitor = monitors.find((m) => contains(m.geometry, pointer.x, pointer.y)) ?? monitors.find((m) => m.primary) ?? monitors[0]
      if (!monitor) throw new Error('la extensión no ha dado ningún monitor')
      this.monitors = monitors
      this.monitor = monitor
      this.uiReady = false
      this.adapter.resetPage()

      const win = createFloatingWindow(monitor.geometry)
      this.win = win
      this.watchWindow(win)
      const seen = new Promise<boolean>((resolve) => {
        this.floatingWaiter = (present) => {
          if (present) resolve(true)
        }
      })
      const found = await this.companion.setFloatingWindow({
        title: 'drakter-floating',
        pid: process.pid,
        monitor: monitor.index,
        cover: true
      })
      win.showInactive()
      if (!found) await deadline(seen, FLOATING_WAIT_MS, 'FloatingWindowChanged')
      this.floatingWaiter = null
      await this.companion.subscribe(this.activeSubscription())
      // La página puede haber mandado ya `ui_ready` (carga rápida): entonces no se espera.
      if (!this.uiReady) {
        await deadline(
          new Promise<void>((resolve) => {
            this.readyWaiter = resolve
          }),
          UI_READY_WAIT_MS,
          'ui_ready'
        )
      }
      this.readyWaiter = null

      const main = getMainWindow()
      this.wasVisible = main !== null && !main.isDestroyed() && main.isVisible()
      if (this.wasVisible) main?.hide()
      this.active = true
      this.busy = null
      this.startSafeTimer()
      this.sendLevelsDemand()
      this.publish()
    } catch (error) {
      logError(SCOPE, 'No se pudo activar el modo flotante', describeError(error))
      this.floatingWaiter = null
      this.readyWaiter = null
      await this.teardownWindow()
      this.busy = null
      this.reason = 'No se ha podido mostrar a Drakter en modo flotante. Inténtalo de nuevo.'
      this.publish()
      notify('Modo flotante', this.reason)
    }
  }

  /**
   * Diálogo nativo de confirmación con la principal oculta (D-13). Sin padre ni foco, GNOME no lo trae al
   * frente (solo avisa con «"Confirmar acción" está preparado»): la extensión lo activa en cuanto aparece.
   */
  private approve(actionId: string): void {
    let open = true
    void requestApproval(this.backend, actionId).finally(() => {
      open = false
      // El avatar vuelve a donde estaba (bridge.js, `drakter_dodge`).
      if (this.live) this.toPage({ kind: 'drakter_dodge', rect: null })
    })
    void this.raiseApproval(() => open)
  }

  private async raiseApproval(isOpen: () => boolean): Promise<void> {
    for (let i = 0; i < 30 && isOpen(); i++) {
      await new Promise((resolve) => setTimeout(resolve, 100))
      try {
        const dialog = (await this.companion.listWindows()).find(
          (w) => !w.floating && w.pid === process.pid && w.title === APPROVAL_TITLE && w.id !== null
        )
        if (dialog?.id) {
          await this.companion.activateWindow(dialog.id)
          // Mientras esté abierto, JARVIS se aparta de su rect (px de la página) para no tapar el texto.
          const o = this.frame
          if (isOpen() && this.live && dialog.frame && o) {
            const f = dialog.frame
            this.toPage({ kind: 'drakter_dodge', rect: [f.x - o.x, f.y - o.y, f.w, f.h] })
          }
          return
        }
      } catch (error) {
        logError(SCOPE, 'No se pudo traer al frente la confirmación', describeError(error))
        return
      }
    }
  }

  private async deactivate(): Promise<void> {
    this.busy = 'deactivating'
    this.publish()
    if (this.barId && this.live) this.toPage({ kind: 'cancel_ask', id: this.barId })
    await this.teardownWindow()
    if (this.wasVisible) focusMainWindow()
    this.wasVisible = false
    this.active = false
    this.busy = null
    this.sendLevelsDemand()
    this.publish()
  }

  /**
   * Suelta todo lo de la extensión y destruye la ventana (orden de CONTRACT §4.2). No lanza.
   * `SetFloatingWindow({})` va después de que la ventana desaparezca: con el prototipo del
   * spike 02, liberar una ventana aún mapeada y cerrarla después tumba gnome-shell (notes/D2.md).
   */
  private async teardownWindow(): Promise<void> {
    this.stopSafeTimer()
    if (this.rectsTimer) clearTimeout(this.rectsTimer)
    this.rectsTimer = null
    this.pendingRects = null
    this.inkWaiting = false
    this.barId = null
    this.uiReady = false
    this.uiReadyPending = false
    const win = this.win
    this.win = null
    this.frame = null
    const ignore = (what: string) => (error: unknown) => logError(SCOPE, `${what} al desactivar`, describeError(error))
    const connected = this.companion.status === 'ok'
    if (connected) {
      await Promise.all([
        this.companion.setEscapeGrab(false).catch(ignore('SetEscapeGrab')),
        this.companion.setInputRegion('none', []).catch(ignore('SetInputRegion')),
        this.companion.subscribe(BASE_SUBSCRIPTION).catch(ignore('Subscribe'))
      ])
    }
    if (win && !win.isDestroyed()) {
      const gone = new Promise<void>((resolve) => {
        const off = this.companion.on('floating', (present) => {
          if (present) return
          off()
          resolve()
        })
        setTimeout(() => {
          off()
          resolve()
        }, RELEASE_WAIT_MS)
      })
      win.destroy()
      if (connected) await gone
    }
    if (connected) await this.companion.setFloatingWindow({}).catch(ignore('SetFloatingWindow'))
  }

  private watchWindow(win: BrowserWindow): void {
    const lost = (why: string): void => {
      if (this.win !== win) return
      logError(SCOPE, `Ventana flotante perdida: ${why}`)
      notify('Modo flotante desactivado', 'La ventana flotante se ha cerrado de forma inesperada.')
      void this.set('off', 'ui')
    }
    win.on('closed', () => lost('cerrada'))
    win.webContents.on('render-process-gone', (_event, details) => lost(details.reason))
    win.webContents.on('did-fail-load', (_event, code, description, _url, isMainFrame) => {
      if (isMainFrame && code !== -3) lost(`carga fallida (${description})`)
    })
  }

  private activeSubscription(): SubscribeOptions {
    return { pointer: true, pointer_min_ms: 8, gestures: true, windows: true, buttons: this.inkWaiting }
  }

  // ------------------------------------------------------------------ hacia la página

  private toPage(msg: RoamieMessage): void {
    this.send(FLOAT_CHANNELS.host, msg)
  }

  private toVoice(msg: FloatVoiceMessage): void {
    if (this.live) this.send(FLOAT_CHANNELS.voice, msg)
  }

  private send(channel: string, ...args: unknown[]): void {
    const win = this.win
    if (!win || win.isDestroyed() || !this.uiReady) return
    win.webContents.send(channel, ...args)
  }

  private layout(): LayoutBounds {
    if (this.monitors.length === 0) return this.monitor?.geometry ?? { x: 0, y: 0, w: 0, h: 0 }
    const x = Math.min(...this.monitors.map((m) => m.geometry.x))
    const y = Math.min(...this.monitors.map((m) => m.geometry.y))
    const x2 = Math.max(...this.monitors.map((m) => m.geometry.x + m.geometry.w))
    const y2 = Math.max(...this.monitors.map((m) => m.geometry.y + m.geometry.h))
    return { x, y, w: x2 - x, h: y2 - y }
  }

  private origin(): { x: number; y: number } {
    return this.frame ?? this.monitor?.geometry ?? { x: 0, y: 0 }
  }

  private sendSafe(): void {
    const m = this.monitor
    if (!m) return
    const o = this.origin()
    const g = m.geometry
    const wa = m.workarea
    // Márgenes de la barra y el dock respecto a la propia ventana (su frame real).
    const height = this.frame?.h ?? g.h
    const width = this.frame?.w ?? g.w
    this.send(FLOAT_CHANNELS.safe, {
      top: Math.max(0, wa.y - o.y),
      left: Math.max(0, wa.x - o.x),
      bottom: Math.max(0, o.y + height - (wa.y + wa.h)),
      right: Math.max(0, o.x + width - (wa.x + wa.w)),
      ox: o.x,
      oy: o.y,
      notch: null
    })
  }

  private startSafeTimer(): void {
    this.stopSafeTimer()
    this.safeTimer = setInterval(() => void this.refreshFrame().then(() => this.sendSafe()), SAFE_EVERY_MS)
  }

  /**
   * Frame real de la flotante (px lógicos globales): es el origen de `ptr`, `click` y `__roamieSafe`.
   * Con `cover` es la geometría del monitor; si Mutter la coloca en otro sitio, manda lo que dice la extensión.
   */
  private async refreshFrame(): Promise<void> {
    if (!this.win || this.companion.status !== 'ok') return
    try {
      const mine = (await this.companion.listWindows()).find((w) => w.floating && w.pid === process.pid)
      const frame = mine?.frame
      if (!frame || frame.w <= 0 || frame.h <= 0) return
      const old = this.frame
      this.frame = frame
      if (!old || old.x !== frame.x || old.y !== frame.y || old.w !== frame.w || old.h !== frame.h) this.sendSafe()
    } catch (error) {
      logError(SCOPE, 'ListWindows fallido', describeError(error))
    }
  }

  private stopSafeTimer(): void {
    if (this.safeTimer) clearInterval(this.safeTimer)
    this.safeTimer = null
  }

  private async refreshMonitors(): Promise<void> {
    if (!this.active) return
    try {
      this.monitors = await this.companion.getMonitors()
      const same = this.monitors.find((m) => m.index === this.monitor?.index)
      if (same) this.monitor = same
      this.sendSafe()
    } catch (error) {
      logError(SCOPE, 'GetMonitors fallido', describeError(error))
    }
  }

  private async followPointer(): Promise<void> {
    if (!this.live) return
    try {
      const pointer = await this.companion.getPointer()
      await this.followAt(pointer.x, pointer.y)
    } catch (error) {
      logError(SCOPE, 'GetPointer fallido', describeError(error))
    }
  }

  /** Mueve la flotante al monitor del punto si es otro (como `move_sidekick_to` de Roamies). */
  private async followAt(x: number, y: number): Promise<void> {
    if (!this.live || !this.monitor || contains(this.monitor.geometry, x, y)) return
    const target = this.monitors.find((m) => contains(m.geometry, x, y))
    if (!target) return
    this.monitor = target
    try {
      await this.companion.setFloatingWindow({ title: 'drakter-floating', pid: process.pid, monitor: target.index, cover: true })
    } catch (error) {
      logError(SCOPE, 'Cambio de monitor fallido', describeError(error))
      return
    }
    this.frame = target.geometry
    this.sendSafe()
    this.send(FLOAT_CHANNELS.moved)
    void this.postPresence()
  }

  // ------------------------------------------------------------------ señales de la extensión

  private onShortcut(name: string, phase: string): void {
    if (phase !== 'press') return
    if (name === 'toggle-floating') void this.set('toggle', 'shortcut')
    else if (name === 'push-to-talk') void activateVoice(this.backend, 'hotkey')
    else if (name === 'escape') this.toPage({ kind: 'esc' })
    else if (name === 'ask') void this.openAsk()
  }

  private async openAsk(): Promise<void> {
    if (!this.active) await this.set('on', 'shortcut')
    if (!this.live) return
    await this.followPointer()
    const id = `bar:${randomUUID()}`
    this.barId = id
    this.toPage({ kind: 'ask', id, placeholder: ASK_PLACEHOLDER, bar: true })
  }

  private onPointer(x: number, y: number, tUs: number): void {
    if (!this.live) return
    const o = this.origin()
    this.send(FLOAT_CHANNELS.ptr, x - o.x, y - o.y, tUs / 1000)
  }

  private onButton(button: number, pressed: boolean, x: number, y: number, tUs: number): void {
    if (!this.live || !this.inkWaiting || button !== 1 || !pressed) return
    const o = this.origin()
    this.send(FLOAT_CHANNELS.click, x - o.x, y - o.y, tUs / 1000)
  }

  private fakeFocus(on: boolean): boolean {
    const win = this.win
    if (!win || win.isDestroyed()) return false
    if (on) win.focus()
    else win.blur()
    return true
  }

  // ------------------------------------------------------------------ eventos del backend

  onEvent(envelope: EventEnvelopeLite): void {
    this.adapter.onEvent(envelope)
  }

  private onUiFloating(request: UiFloatingRequest): void {
    if (request.action) void this.set(request.action, request.source)
    if (request.size) this.toPage({ kind: 'size', size: request.size })
    if (request.pin) {
      this.toPage(request.pin === 'release' ? { kind: 'avatar_pin', release: true } : { kind: 'avatar_pin', corner: request.pin })
    }
  }

  // ------------------------------------------------------------------ IPC

  /** `float:invoke` desde la página flotante. */
  handleInvoke(event: IpcMainInvokeEvent, cmd: unknown, args: unknown): unknown {
    const win = this.win
    const frame = event.senderFrame
    const trusted =
      win !== null &&
      !win.isDestroyed() &&
      event.sender.id === win.webContents.id &&
      frame !== null &&
      frame.frameTreeNodeId === win.webContents.mainFrame.frameTreeNodeId &&
      frame.url.split('?')[0] === FLOATING_URL.split('?')[0]
    if (!trusted) throw new Error('Remitente no autorizado')
    try {
      return handleFloatInvoke(this.pageHost, cmd, args)
    } catch (error) {
      logError(SCOPE, 'float:invoke rechazado', error instanceof Error ? error.message : String(error))
      throw error
    }
  }

  private readonly pageHost: PageHost = {
    windowSize: () => {
      const win = this.win
      if (!win || win.isDestroyed()) return { width: 0, height: 0 }
      const [width = 0, height = 0] = win.getContentSize()
      return { width, height }
    },
    sidecar: (message) => this.onSidecar(message),
    setHitRects: (rects) => this.queueHitRects(rects),
    setTyping: (on) => {
      void this.companion.setFloatingFocus(on).catch((error: unknown) => logError(SCOPE, 'SetFloatingFocus fallido', describeError(error)))
    },
    escWatch: (on) => {
      void this.companion.setEscapeGrab(on).catch((error: unknown) => logError(SCOPE, 'SetEscapeGrab fallido', describeError(error)))
    },
    inkWait: (on) => {
      if (this.inkWaiting === on) return
      this.inkWaiting = on
      if (this.active) {
        void this.companion.subscribe(this.activeSubscription()).catch((error: unknown) => logError(SCOPE, 'Subscribe fallido', describeError(error)))
      }
    }
  }

  private queueHitRects(rects: Rect4[]): void {
    this.pendingRects = rects
    if (this.rectsTimer) return
    const wait = Math.max(0, this.lastRectsAt + HIT_RECTS_GAP_MS - Date.now())
    this.rectsTimer = setTimeout(() => {
      this.rectsTimer = null
      const next = this.pendingRects
      this.pendingRects = null
      if (next === null || !this.active && !this.busy) return
      this.lastRectsAt = Date.now()
      const mode = next.length === 0 ? 'none' : 'rects'
      this.companion
        .setInputRegion(mode, next)
        .then((applied) => {
          if (applied === 'client' && !this.clientRegionLogged) {
            this.clientRegionLogged = true
            logError(SCOPE, 'La ventana flotante va por XWayland: la región de entrada no se aplica (configuración errónea)')
          }
        })
        .catch((error: unknown) => logError(SCOPE, 'SetInputRegion fallido', describeError(error)))
    }, wait)
  }

  private onSidecar(message: SidecarMessage): void {
    switch (message.kind) {
      case 'ui_ready':
        void this.onUiReady()
        return
      case 'answer':
        void this.onAnswer(message.id, message.text)
        return
      case 'menu_stop':
        if (this.adapter.turnId) void cancelTurn(this.backend, this.adapter.turnId)
        this.toVoice({ t: 'stop' })
        if (this.adapter.guideId) {
          this.adapter.guideId = null
          void postOverlayEvent(this.backend, { type: 'ink_cleared' })
        }
        return
      case 'listen_cancel':
        void callNamedOperation(this.backend, 'voice.mode', { mode: 'standby' })
        return
      case 'open_link':
        this.openLink(message.url)
        return
      case 'overlay':
        if (message.event.type === 'ink_cleared') this.adapter.guideId = null
        void postOverlayEvent(this.backend, message.event)
        return
      case 'ignored':
        return
    }
  }

  private async onUiReady(): Promise<void> {
    const win = this.win
    if (!win || win.isDestroyed()) return
    // La página repite `ui_ready` cada 150 ms hasta oír algo: una sola respuesta.
    if (this.uiReady || this.uiReadyPending) return
    this.uiReadyPending = true
    const [settings] = await Promise.all([readFloatingSettings(this.backend), this.refreshFrame()])
    this.uiReadyPending = false
    if (this.win !== win) return
    this.uiReady = true
    this.toPage({ kind: 'sound', on: settings.sound })
    this.toPage({ kind: 'volume', v: 1 })
    this.toPage({ kind: 'notch', on: false })
    this.toPage({ kind: 'size', size: settings.size })
    this.toPage({ kind: 'look', look: 'jarvis' })
    this.sendSafe()
    if (!this.greeted) {
      this.greeted = true
      this.toPage({ kind: 'greet' })
    }
    this.toPage({ kind: 'summon', show: true })
    this.readyWaiter?.()
    if (this.active) this.publish()
  }

  private async onAnswer(id: string, text: string | null): Promise<void> {
    // Solo la barra de pregunta abierta por main. Nunca confirma nada.
    if (!isBarId(id) || id !== this.barId) return
    this.barId = null
    const clean = text?.trim() ?? ''
    if (clean === '') return
    const result = await sendChatMessage(this.backend, this.adapter.sessionId, clean)
    if (result.ok) {
      this.adapter.sessionId = result.sessionId
      return
    }
    const bubble = result.code === 'busy' ? 'Ahora estoy ocupado; pregúntamelo en cuanto termine.' : 'No he podido enviar tu pregunta.'
    this.toPage({ kind: 'say', text: bubble, mood: 'concerned' })
  }

  private openLink(url: string): void {
    let parsed: URL
    try {
      parsed = new URL(url)
    } catch {
      return
    }
    const mail = parsed.protocol === 'mailto:' && !/[\r\n]/.test(url)
    if (!mail && checkUrl(url).level !== 'safe') return
    void shell.openExternal(parsed.href).catch((error: unknown) => logError(SCOPE, 'No se pudo abrir el enlace', describeError(error)))
  }

  /** `floating:levels` de la ventana principal: ≤ 40 por segundo y en 0..1. */
  onLevels(payload: unknown): void {
    if (!this.live) return
    const now = Date.now()
    this.levelStamps = this.levelStamps.filter((t) => now - t < 1000)
    if (this.levelStamps.length >= FLOAT_LIMITS.levelsPerSecond) return
    if (typeof payload !== 'object' || payload === null) return
    const { out, in: input } = payload as { out?: unknown; in?: unknown }
    const ok = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v) && v >= 0 && v <= 1
    if (!ok(out) || !ok(input)) return
    this.levelStamps.push(now)
    this.toVoice({ t: 'lv', out, in: input })
    if (this.adapter.hearing) this.toPage({ kind: 'voice', type: 'level', v: input })
  }

  private sendLevelsDemand(): void {
    getMainWindow()?.webContents.send(FLOATING_CHANNELS.levelsDemand, this.active)
  }
}
