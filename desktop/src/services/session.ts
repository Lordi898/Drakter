import type { DrakterBridge } from '../../electron/shared/bridge'
import type { ConfirmationDecision } from '@/services/protocol'
import { WS_PATH } from '@/services/protocol'

/**
 * Sesión con el backend local. El token vive SOLO en la memoria de este módulo:
 * nunca en stores, almacenamiento, URL, logs ni notificaciones.
 */
export interface BackendSession {
  readonly baseUrl: string
  readonly wsUrl: string
  readonly token: string
}

/** Parte del puente que aún no declara `bridge.ts`; se detecta en tiempo de ejecución. */
export type ExtendedBridge = DrakterBridge &
  Partial<{
    getBackendSession(): Promise<{ port: number; token: string } | null>
    decideConfirmation(id: string, decision: ConfirmationDecision): Promise<void>
  }>

const HOST = '127.0.0.1'
const TOKEN_PATTERN = /^[A-Za-z0-9._~+-]{1,1024}$/

let cached: BackendSession | null = null
let inFlight: Promise<BackendSession | null> | null = null
let generation = 0

/** En un navegador normal el puente no existe aunque el tipo diga lo contrario. */
export function getExtendedBridge(): ExtendedBridge | null {
  if (typeof window === 'undefined' || typeof window.drakter === 'undefined') return null
  return window.drakter as ExtendedBridge
}

function isValidPort(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value >= 1024 && value <= 65535
}

function buildSession(raw: unknown): BackendSession | null {
  if (typeof raw !== 'object' || raw === null) return null
  const { port, token } = raw as { port?: unknown; token?: unknown }
  if (!isValidPort(port) || typeof token !== 'string' || !TOKEN_PATTERN.test(token)) return null
  return {
    baseUrl: `http://${HOST}:${port}`,
    wsUrl: `ws://${HOST}:${port}${WS_PATH}`,
    token
  }
}

/** Devuelve la sesión en caché o la pide al puente. `null` si no hay backend o el puente no existe. */
export function loadBackendSession(): Promise<BackendSession | null> {
  if (cached) return Promise.resolve(cached)
  if (inFlight) return inFlight

  const bridge = getExtendedBridge()
  if (!bridge || typeof bridge.getBackendSession !== 'function') return Promise.resolve(null)

  const myGeneration = generation
  const request = bridge
    .getBackendSession()
    .then((raw) => {
      const session = buildSession(raw)
      // Si se limpió mientras se pedía, el resultado puede estar obsoleto: no se guarda.
      if (session && myGeneration === generation) cached = session
      return session
    })
    .catch(() => null)
    .finally(() => {
      if (inFlight === request) inFlight = null
    })
  inFlight = request
  return request
}

export function clearBackendSession(): void {
  generation += 1
  cached = null
  inFlight = null
}
