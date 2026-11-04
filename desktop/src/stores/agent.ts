import { useSyncExternalStore } from 'react'
import type { CharacterState } from '@/character/types'
import type { AgentStatus } from '@/services/protocol'
import { getLinkStatus, startBackendLink, subscribeLinkStatus, subscribeServerEvents } from '@/services/ws'

/**
 * Estado de Drakter visto por la interfaz. `offline` si el enlace no está
 * abierto; si no, el último `agent.status_changed` recibido (`idle` por defecto).
 * Nada simulado.
 */
let reported: AgentStatus = 'idle'
const listeners = new Set<() => void>()
let wired = false

function emit(): void {
  listeners.forEach((listener) => listener())
}

export function getDrakterState(): CharacterState {
  return getLinkStatus() === 'open' ? reported : 'offline'
}

function wire(): void {
  if (wired) return
  wired = true
  subscribeServerEvents((event) => {
    if (event.type !== 'agent.status_changed') return
    reported = event.payload.status
    emit()
  })
  // Al cambiar el enlace (perdido o recién abierto) se parte de un estado neutro.
  subscribeLinkStatus(() => {
    reported = 'idle'
    emit()
  })
}

wire()

export function subscribeDrakterState(listener: () => void): () => void {
  listeners.add(listener)
  startBackendLink()
  return () => {
    listeners.delete(listener)
  }
}

export function useDrakterState(): CharacterState {
  return useSyncExternalStore(subscribeDrakterState, getDrakterState)
}
