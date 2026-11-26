import { useSyncExternalStore, type ComponentType } from 'react'
import { getPreferences, updatePreferences, type UiMode } from '@/stores/preferences'

export type { UiMode }

/**
 * Modo de la interfaz: Drakter (por defecto, siempre al arrancar) o Jarvis (shell aparte, carga diferida).
 * Todas las vías de activación (botón, atajo, bandeja, `ui.mode` de la voz o del agente) llaman a
 * `requestUiMode`. Va en el chunk principal: no importa nada de `src/jarvis/`.
 *
 * Ciclo: `requestUiMode` fija `target` y pone `phase` en `entering`/`leaving`; quien monta el shell
 * pedido llama a `settleUiMode('ready')` cuando ya se ve (entonces `mode = target`) o
 * `settleUiMode('failed')` si no pudo (se vuelve a `mode`). Mientras dura, se ignoran otras peticiones.
 */
export type UiModeSource = 'button' | 'shortcut' | 'tray' | 'voice' | 'agent' | 'startup'
export type UiModePhase = 'idle' | 'entering' | 'leaving'

export interface UiModeSnapshot {
  /** Modo montado: el que se ve cuando termina la transición. */
  readonly mode: UiMode
  /** Modo pedido; distinto de `mode` solo durante la transición. */
  readonly target: UiMode
  readonly phase: UiModePhase
  readonly source: UiModeSource | null
}

/** Separación mínima entre dos cambios: una orden repetida (voz y agente a la vez) no hace parpadear. */
const MIN_INTERVAL_MS = 1000

// El shell de Jarvis lo aporta W1 (src/jarvis/JarvisShell.tsx). Hasta entonces el glob queda vacío.
const jarvisModules = import.meta.glob<{ default: ComponentType }>('../jarvis/JarvisShell.tsx')
const jarvisLoader = Object.values(jarvisModules)[0]

let snapshot: UiModeSnapshot = { mode: 'drakter', target: 'drakter', phase: 'idle', source: null }
let lastChangeAt = Number.NEGATIVE_INFINITY
let jarvisPromise: Promise<{ default: ComponentType }> | null = null
const listeners = new Set<() => void>()

function set(next: UiModeSnapshot): void {
  snapshot = next
  listeners.forEach((listener) => listener())
}

/** Hay shell de Jarvis en esta build. */
export function jarvisAvailable(): boolean {
  return jarvisLoader !== undefined
}

/** Carga (una vez) el chunk de Jarvis. Si falla, el siguiente intento vuelve a pedirlo. */
export function loadJarvisShell(): Promise<{ default: ComponentType }> {
  if (!jarvisLoader) return Promise.reject(new Error('jarvis-unavailable'))
  jarvisPromise ??= jarvisLoader().catch((error: unknown) => {
    jarvisPromise = null
    throw error
  })
  return jarvisPromise
}

/** Precarga el chunk sin cambiar de modo (hover del botón, inicio de una orden). Idempotente. */
export function prefetchJarvis(): void {
  void loadJarvisShell().catch(() => undefined)
}

export function requestUiMode(mode: UiMode | 'toggle', source: UiModeSource): void {
  if (snapshot.phase !== 'idle') return
  const target: UiMode = mode === 'toggle' ? (snapshot.mode === 'jarvis' ? 'drakter' : 'jarvis') : mode
  if (target === snapshot.mode) return
  const now = performance.now()
  if (source !== 'startup' && now - lastChangeAt < MIN_INTERVAL_MS) return
  if (target === 'jarvis' && !jarvisAvailable()) {
    console.warn('El modo Jarvis no está en esta build.')
    return
  }
  lastChangeAt = now
  if (target === 'jarvis') prefetchJarvis()
  set({ mode: snapshot.mode, target, phase: target === 'jarvis' ? 'entering' : 'leaving', source })
}

export function settleUiMode(result: 'ready' | 'failed'): void {
  if (snapshot.phase === 'idle') return
  const mode = result === 'ready' ? snapshot.target : snapshot.mode
  set({ mode, target: mode, phase: 'idle', source: snapshot.source })
  if (result === 'ready' && getPreferences().jarvisStartup === 'last' && getPreferences().lastUiMode !== mode) {
    updatePreferences({ lastUiMode: mode })
  }
}

/** Tope de la secuencia de salida de una interfaz Jarvis: nunca retiene la vuelta a Drakter más. */
const LEAVE_MAX_MS = 1500
let leaveTransition: (() => Promise<void>) | null = null

/**
 * Secuencia de salida del shell que está a la vista (la registra `JarvisShell` por su interfaz).
 * `null` la quita. Solo puede haber una.
 */
export function setLeaveTransition(run: (() => Promise<void>) | null): void {
  leaveTransition = run
}

/** Ejecuta la secuencia de salida registrada (si la hay), con tope de tiempo. Nunca rechaza. */
export function runLeaveTransition(): Promise<void> {
  const run = leaveTransition
  if (!run) return Promise.resolve()
  return Promise.race([
    run().catch(() => undefined),
    new Promise<void>((resolve) => setTimeout(resolve, LEAVE_MAX_MS))
  ])
}

/** Vuelve a Drakter al instante, sin transición ni límite de frecuencia: el shell de Jarvis falló. */
export function resetUiMode(): void {
  if (snapshot.mode === 'drakter' && snapshot.phase === 'idle') return
  lastChangeAt = performance.now()
  set({ mode: 'drakter', target: 'drakter', phase: 'idle', source: snapshot.source })
}

export function getUiMode(): UiModeSnapshot {
  return snapshot
}

export function subscribeUiMode(listener: () => void): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export function useUiMode(): UiModeSnapshot {
  return useSyncExternalStore(subscribeUiMode, getUiMode)
}
