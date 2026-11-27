/**
 * Modo flotante (docs/floating/CONTRACT.md §4): estado, canales IPC y tipos que comparten
 * main, los dos preload y el renderer. Sin dependencias de Electron.
 */

export type CompanionStatus = 'ok' | 'missing' | 'outdated' | 'denied' | 'unsupported_session'

export interface FloatingState {
  readonly active: boolean
  /** `companion === 'ok'`. */
  readonly available: boolean
  readonly companion: CompanionStatus
  readonly busy: 'activating' | 'deactivating' | null
  /** Texto en español para la UI cuando `!available` o al fallar. */
  readonly reason: string | null
}

export type FloatingAction = 'on' | 'off' | 'toggle'
export type FloatingSource = 'ui' | 'shortcut' | 'tray' | 'voice' | 'agent'

export const FLOATING_ACTIONS: readonly FloatingAction[] = ['on', 'off', 'toggle']

/** Página flotante ↔ main (`window.drakterFloat`, §4.3). */
export const FLOAT_CHANNELS = {
  invoke: 'float:invoke',
  host: 'float:host',
  ptr: 'float:ptr',
  click: 'float:click',
  safe: 'float:safe',
  moved: 'float:moved',
  voice: 'float:voice'
} as const

export const FLOAT_INVOKE_CMDS = ['sidecar_send', 'set_hot', 'set_hit_rects', 'set_typing', 'esc_watch', 'ink_wait', 'buddy'] as const
export type FloatInvokeCmd = (typeof FLOAT_INVOKE_CMDS)[number]

export type FloatPushChannel = 'host' | 'ptr' | 'click' | 'safe' | 'moved' | 'voice'
export const FLOAT_PUSH_CHANNELS: readonly FloatPushChannel[] = ['host', 'ptr', 'click', 'safe', 'moved', 'voice']

export const FLOAT_CONFIG = {
  unit: 400,
  only: ['sidekick'],
  autosound: true,
  linux: 'wayland'
} as const

export interface DrakterFloat {
  readonly config: {
    readonly unit: 400
    readonly only: readonly ['sidekick']
    readonly autosound: true
    readonly linux: 'wayland'
  }
  invoke(cmd: FloatInvokeCmd, args: unknown): Promise<unknown>
  on(ch: FloatPushChannel, cb: (...a: unknown[]) => void): void
}

/** Límites que hace cumplir main. */
export const FLOAT_LIMITS = {
  /** JSON de `sidecar_send`. */
  sidecarBytes: 64 * 1024,
  /** Números de `set_hit_rects` (256 rects). */
  hitRectNumbers: 1024,
  hitRectsPerSecond: 10,
  levelsPerSecond: 40,
  answerChars: 4000
} as const

/** Título de la ventana flotante: con el `pid`, es la regla de casado de la extensión. */
export const FLOATING_WINDOW_TITLE = 'drakter-floating'
export const FLOATING_URL = 'app://floating/index.html?look=jarvis'

/** CSP de la página flotante (§11.6), en cabecera de `app://floating`. */
export const FLOATING_HEADER_CSP = [
  "default-src 'none'",
  "script-src 'self'",
  "style-src 'self' 'unsafe-inline'",
  "font-src 'self'",
  "img-src 'self' data:",
  "connect-src 'none'",
  "media-src 'none'",
  "base-uri 'none'",
  "form-action 'none'",
  "object-src 'none'",
  "frame-ancestors 'none'"
].join('; ')
