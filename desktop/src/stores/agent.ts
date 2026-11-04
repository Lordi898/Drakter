import { useSyncExternalStore } from 'react'
import type { CharacterState } from '@/character/types'
import { getAgentStatus } from '@/services/api'
import type { AgentState } from '@/services/protocol'
import { getLinkStatus, startBackendLink, subscribeLinkStatus, subscribeResync, subscribeServerEvents } from '@/services/ws'

/**
 * Estado de Drakter visto por la interfaz. `offline` si el enlace no está
 * abierto; si no, el último `agent.status_changed` recibido (`idle` por defecto).
 * Nada simulado.
 */
let reported: AgentState = 'idle'
/** Se incrementa con cada cambio; una siembra obsoleta no pisa un evento más reciente. */
let version = 0
const listeners = new Set<() => void>()
let wired = false

function emit(): void {
  listeners.forEach((listener) => listener())
}

export function getDrakterState(): CharacterState {
  return getLinkStatus() === 'open' ? reported : 'offline'
}

/** Al abrir el enlace se lee el estado real del agente; si falla, se conserva lo último sabido sin inventar nada. */
async function seed(): Promise<void> {
  const mine = version
  try {
    const info = await getAgentStatus()
    if (mine !== version) return
    reported = info.state
    emit()
  } catch {
    console.warn('No se pudo leer el estado del agente.')
  }
}

function wire(): void {
  if (wired) return
  wired = true
  subscribeServerEvents((event) => {
    if (event.type !== 'agent.status_changed') return
    version += 1
    reported = event.payload.state
    emit()
  })
  // Al cambiar el enlace se avisa a la interfaz; no se fuerza `idle` (un turno puede seguir activo).
  subscribeLinkStatus(() => {
    version += 1
    emit()
  })
  subscribeResync(() => void seed())
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
