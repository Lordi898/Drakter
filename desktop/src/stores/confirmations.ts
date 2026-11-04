import { useSyncExternalStore } from 'react'
import type { ApprovalOutcome } from '../../electron/shared/bridge'
import { listPendingConfirmations, subscribeConfirmationRequired } from '@/services/api'
import type { PendingConfirmation } from '@/services/protocol'
import { subscribeResync, subscribeServerEvents } from '@/services/ws'

/**
 * Confirmaciones pendientes. El renderer NO aprueba ni rechaza: pide a main que
 * muestre el diálogo nativo (`window.api.requestApproval`), que es quien decide.
 * No hay ruta alternativa, ni aprobar en bloque, ni recordar decisiones; no debe añadirse ninguna.
 */
export type TrustedGesture = { readonly isTrusted: boolean }
export type ReviewOutcome = ApprovalOutcome

const MAX_TIMEOUT_MS = 2_147_483_647 // límite de setTimeout
const OUTCOMES: readonly string[] = ['approved', 'rejected', 'expired', 'conflict', 'failed']

let items: readonly PendingConfirmation[] = []
const timers = new Map<string, ReturnType<typeof setTimeout>>()
const inFlight = new Set<string>()
const listeners = new Set<() => void>()

// Durante una relectura se anotan los cambios por evento para no pisarlos.
let refreshing = false
let addedDuringRefresh = new Map<string, PendingConfirmation>()
let removedDuringRefresh = new Set<string>()

function emit(): void {
  listeners.forEach((listener) => listener())
}

function isExpired(item: PendingConfirmation): boolean {
  return Date.now() >= Date.parse(item.expires_at)
}

function clearTimer(actionId: string): void {
  const timer = timers.get(actionId)
  if (timer !== undefined) clearTimeout(timer)
  timers.delete(actionId)
}

function remove(actionId: string): void {
  clearTimer(actionId)
  if (refreshing) {
    addedDuringRefresh.delete(actionId)
    removedDuringRefresh.add(actionId)
  }
  if (!items.some((item) => item.action_id === actionId)) return
  items = items.filter((item) => item.action_id !== actionId)
  emit()
}

function scheduleExpiry(item: PendingConfirmation): void {
  clearTimer(item.action_id)
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
  if (isExpired(item)) return
  if (refreshing) {
    addedDuringRefresh.set(item.action_id, item)
    removedDuringRefresh.delete(item.action_id)
  }
  if (items.some((existing) => existing.action_id === item.action_id)) return
  items = [...items, item]
  scheduleExpiry(item)
  emit()
}

async function refresh(): Promise<void> {
  if (refreshing) return
  refreshing = true
  addedDuringRefresh = new Map()
  removedDuringRefresh = new Set()
  try {
    const fetched = await listPendingConfirmations()
    const merged = new Map<string, PendingConfirmation>()
    for (const item of fetched) if (!removedDuringRefresh.has(item.action_id)) merged.set(item.action_id, item)
    for (const [id, item] of addedDuringRefresh) merged.set(id, item)
    const keep = [...merged.values()].filter((item) => !isExpired(item))
    const keepIds = new Set(keep.map((item) => item.action_id))
    for (const old of items) if (!keepIds.has(old.action_id)) clearTimer(old.action_id)
    items = keep
    keep.forEach(scheduleExpiry)
    emit()
  } catch {
    console.warn('No se pudieron leer las confirmaciones pendientes.')
  } finally {
    refreshing = false
  }
}

// Una sola vez, al cargar el módulo.
subscribeServerEvents((event) => {
  if (event.type === 'confirmation.requested') add(event.payload)
  else if (event.type === 'confirmation.resolved') remove(event.payload.action_id)
})
subscribeConfirmationRequired((ticket) => {
  add({
    action_id: ticket.id,
    summary: ticket.summary,
    affected_count: ticket.affected_count,
    expires_at: ticket.expires_at
  })
})
subscribeResync(() => void refresh())

export async function reviewConfirmation(actionId: string, proof: TrustedGesture): Promise<ReviewOutcome> {
  // Antes de cualquier otra cosa: un clic sintético o programático no abre nada.
  if (typeof proof !== 'object' || proof === null || proof.isTrusted !== true) {
    throw new Error('Solo puedes revisar una confirmación con un gesto directo en la interfaz.')
  }
  const item = items.find((candidate) => candidate.action_id === actionId)
  if (!item) return 'failed'
  if (isExpired(item)) {
    remove(actionId)
    return 'expired'
  }
  if (inFlight.has(actionId)) return 'failed'
  if (typeof window === 'undefined' || typeof window.api === 'undefined') return 'failed'

  inFlight.add(actionId)
  try {
    const outcome: unknown = await window.api.requestApproval(actionId)
    const result: ReviewOutcome = OUTCOMES.includes(outcome as string) ? (outcome as ReviewOutcome) : 'failed'
    if (result !== 'failed') remove(actionId)
    return result
  } catch {
    return 'failed'
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
