import { useSyncExternalStore } from 'react'
import * as api from '@/services/api'
import type { ConfirmationDecision, PendingConfirmation } from '@/services/protocol'
import { getExtendedBridge } from '@/services/session'
import { subscribeLinkStatus, subscribeServerEvents } from '@/services/ws'

/**
 * Confirmaciones pendientes de acciones destructivas o masivas.
 *
 * `decide` es el ÚNICO camino de aprobación: exige un gesto real del usuario
 * (`isTrusted`), comprueba antes de cualquier red y evita el doble envío. Caducar
 * solo quita la confirmación de la lista; jamás la aprueba. No existe aprobar en
 * bloque, recordar decisiones ni auto-aprobar, y no debe añadirse.
 */
export type TrustedGesture = { readonly isTrusted: boolean }

const MAX_TIMEOUT_MS = 2_147_483_647 // límite de setTimeout

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

function expiresAt(item: PendingConfirmation): number {
  return Date.parse(item.expires_at)
}

function isExpired(item: PendingConfirmation): boolean {
  return Date.now() >= expiresAt(item)
}

function clearTimer(id: string): void {
  const timer = timers.get(id)
  if (timer !== undefined) clearTimeout(timer)
  timers.delete(id)
}

function remove(id: string): void {
  clearTimer(id)
  if (refreshing) {
    addedDuringRefresh.delete(id)
    removedDuringRefresh.add(id)
  }
  if (!items.some((item) => item.id === id)) return
  items = items.filter((item) => item.id !== id)
  emit()
}

function scheduleExpiry(item: PendingConfirmation): void {
  clearTimer(item.id)
  const remaining = expiresAt(item) - Date.now()
  const timer = setTimeout(
    () => {
      timers.delete(item.id)
      if (isExpired(item)) remove(item.id) // solo retira; nunca aprueba
      else scheduleExpiry(item)
    },
    Math.min(Math.max(remaining, 0), MAX_TIMEOUT_MS)
  )
  timers.set(item.id, timer)
}

function add(item: PendingConfirmation): void {
  if (isExpired(item)) return
  if (refreshing) {
    addedDuringRefresh.set(item.id, item)
    removedDuringRefresh.delete(item.id)
  }
  if (items.some((existing) => existing.id === item.id)) return
  items = [...items, item]
  scheduleExpiry(item)
  emit()
}

function replaceAll(next: readonly PendingConfirmation[]): void {
  const keep = next.filter((item) => !isExpired(item))
  const keepIds = new Set(keep.map((item) => item.id))
  for (const old of items) if (!keepIds.has(old.id)) clearTimer(old.id)
  items = keep
  keep.forEach(scheduleExpiry)
  emit()
}

async function refresh(): Promise<void> {
  if (refreshing) return
  refreshing = true
  addedDuringRefresh = new Map()
  removedDuringRefresh = new Set()
  try {
    const fetched = await api.listPendingConfirmations()
    const merged = new Map<string, PendingConfirmation>()
    for (const item of fetched) if (!removedDuringRefresh.has(item.id)) merged.set(item.id, item)
    for (const [id, item] of addedDuringRefresh) merged.set(id, item)
    replaceAll([...merged.values()])
  } catch {
    console.warn('No se pudieron leer las confirmaciones pendientes.')
  } finally {
    refreshing = false
  }
}

// Suscripciones: una sola vez, al cargar el módulo.
subscribeServerEvents((event) => {
  if (event.type === 'confirmation.requested') add(event.payload.confirmation)
  else if (event.type === 'confirmation.resolved') remove(event.payload.id)
})
subscribeLinkStatus((status) => {
  if (status === 'open') void refresh()
})

export async function decide(id: string, decision: ConfirmationDecision, proof: TrustedGesture): Promise<void> {
  // Antes de cualquier red: un clic sintético o programático nunca aprueba.
  if (typeof proof !== 'object' || proof === null || proof.isTrusted !== true) {
    throw new Error('Solo puedes decidir una confirmación con un gesto directo en la interfaz.')
  }
  if (decision !== 'approved' && decision !== 'rejected') {
    throw new Error('La decisión no es válida.')
  }
  const item = items.find((candidate) => candidate.id === id)
  if (!item) throw new Error('Esta confirmación ya no está disponible.')
  if (isExpired(item)) {
    remove(id)
    throw new Error('Esta confirmación ha caducado y no se ha ejecutado nada.')
  }
  if (inFlight.has(id)) return
  inFlight.add(id)
  try {
    const bridge = getExtendedBridge()
    if (bridge && typeof bridge.decideConfirmation === 'function') {
      try {
        await bridge.decideConfirmation(id, decision)
      } catch {
        throw new Error('No se pudo registrar tu decisión. Inténtalo de nuevo.')
      }
    } else {
      await api.decideConfirmation(id, decision)
    }
    remove(id)
  } catch (error) {
    if (error instanceof api.ApiError && (error.status === 404 || error.status === 409)) remove(id)
    throw error instanceof Error ? error : new Error('No se pudo registrar tu decisión.')
  } finally {
    inFlight.delete(id)
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
