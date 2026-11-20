import { useEffect } from 'react'
import { subscribeOutputLevel } from '@/voice/outputLevel'
import type { CharacterState } from './types'

/** Movimiento reducido: el ajuste de la app (atributo del documento) o el del sistema. */
export function motionReduced(): boolean {
  return (
    document.documentElement.dataset['reduceMotion'] === 'true' ||
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

/**
 * Entrega el nivel real del audio (0..1, ~30 fps) mientras el personaje habla; fuera de
 * `speaking` o con movimiento reducido no se suscribe a nada y manda `null` (boca por defecto).
 * `apply` debe ser estable (p. ej. un método de un ref).
 */
export function useMouthLevel(state: CharacterState, apply: (level: number | null) => void): void {
  useEffect(() => {
    if (state !== 'speaking' || motionReduced()) {
      apply(null)
      return
    }
    apply(0)
    const stop = subscribeOutputLevel(apply)
    return () => {
      stop()
      apply(null)
    }
  }, [state, apply])
}
