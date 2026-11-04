import { useSyncExternalStore } from 'react'
import type { PendingConfirmation } from '@/services/protocol'
import { getExtendedBridge, type ReviewOutcome } from '@/services/session'
import { subscribeServerEvents } from '@/services/ws'

/**
 * Confirmaciones pendientes. El renderer NO aprueba ni rechaza: solo pide al
 * proceso principal que muestre el diálogo nativo (`reviewConfirmation`), que es
 * quien decide y llama al backend. No hay ruta REST alternativa, ni aprobar en
 * bloque, ni recordar decisiones; no debe añadirse ninguna.
 */
export type TrustedGesture = { readonly isTrusted: boolean }
export type { ReviewOutcome }

const MAX_TIMEOUT_MS = 2_147_483_647 // límite de setTimeout
const OUTCOMES: readonly string[] = ['approved', 'rejected', 'dismissed', 'expired', 'unavailable']

let items: readonly PendingConfirmation[] = []
const timers = new Map<string, ReturnType<typeof setTimeout>>()
const inFlight = new Set<string>()
const listeners = new Set<() => void>()

function emit(): void {
  listeners.forEach((listener) => listener())
}

function isExpired(item: PendingConfirmation): boolean {
  return Date.now() >= Date.parse(item.expires_at)
}

function remove(actionId: string): void {
  const timer = timers.get(actionId)
  if (timer !== undefined) clearTimeout(timer)
  timers.delete(actionId)
  if (!items.some((item) => item.action_id === actionId)) return
  items = items.filter((item) => item.action_id !== actionId)
  emit()
}

function scheduleExpiry(item: PendingConfirmation): void {
  const remaining = Date.parse(item.expires_at) - Date.now()
  timers.set(
    item.action_id,
    setTimeout(
      () => {
        timers.delete(item.action_id)
        if (isExpired(item)) remove(item.action_id) // solo retira; nunca aprueba
        else scheduleExpiry(item)
      },
      Math.min(Math.max(remaining, 0), MAX_TIMEOUT_MS)
    )
  )
}

function add(item: PendingConfirmation): void {
  if (isExpired(item) || items.some((existing) => existing.action_id === item.action_id)) return
  items = [...items, item]
  scheduleExpiry(item)
  emit()
}

// Una sola vez, al cargar el módulo. Tras reconectar llegan de nuevo por `after_seq`.
subscribeServerEvents((event) => {
  if (event.type === 'agent.confirmation_required') add(event.payload)
})

export async function reviewConfirmation(actionId: string, proof: TrustedGesture): Promise<ReviewOutcome> {
  // Antes de cualquier otra cosa: un clic sintético o programático no abre nada.
  if (typeof proof !== 'object' || proof === null || proof.isTrusted !== true) {
    throw new Error('Solo puedes revisar una confirmación con un gesto directo en la interfaz.')
  }
  const item = items.find((candidate) => candidate.action_id === actionId)
  if (!item) return 'unavailable'
  if (isExpired(item)) {
    remove(actionId)
    return 'expired'
  }
  if (inFlight.has(actionId)) return 'dismissed'

  const bridge = getExtendedBridge()
  if (!bridge || typeof bridge.reviewConfirmation !== 'function') return 'unavailable'

  inFlight.add(actionId)
  try {
    const result = await bridge.reviewConfirmation(actionId)
    const outcome: ReviewOutcome =
      typeof result === 'object' && result !== null && OUTCOMES.includes(result.outcome)
        ? result.outcome
        : 'unavailable'
    if (outcome === 'approved' || outcome === 'rejected' || outcome === 'expired') remove(actionId)
    return outcome
  } catch {
    return 'unavailable'
  } finally {
    inFlight.delete(actionId)
  }
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export function useConfirmations(): readonly PendingConfirmation[] {
  return useSyncExternalStore(subscribe, () => items)
}
