import { useSyncExternalStore } from 'react'
import { usePreferences } from '@/stores/preferences'

const SYSTEM_REDUCED = '(prefers-reduced-motion: reduce)'

function subscribeSystemReduced(onChange: () => void): () => void {
  const query = window.matchMedia(SYSTEM_REDUCED)
  query.addEventListener('change', onChange)
  return () => query.removeEventListener('change', onChange)
}

const systemReduced = (): boolean => window.matchMedia(SYSTEM_REDUCED).matches

/** Movimiento reducido: el ajuste «Reducir movimiento» de la app o el del sistema. */
export function useReducedMotion(): boolean {
  const { reduceMotion } = usePreferences()
  return useSyncExternalStore(subscribeSystemReduced, systemReduced) || reduceMotion
}
