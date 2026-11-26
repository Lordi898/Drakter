import { useCallback, useEffect, useRef, useSyncExternalStore } from 'react'
import { usePreferences } from '@/stores/preferences'
import { subscribeUserTyping } from './activity'
import { loadActiveAvatar } from './avatars/registry'
import type { Avatar3D } from './avatars/types'
import { warnCharacter } from './log'
import type { CharacterRendererProps } from './types'
import { useMouthLevel } from './useMouthLevel'

/** Tope de densidad de píxeles: nitidez suficiente sin disparar el coste en GPU integrada. */
const MAX_PIXEL_RATIO = 1.5
/** Lo que tarda el fundido de entrada del lienzo; el padre retira el SVG al acabar. */
const FADE_MS = 650

const SYSTEM_REDUCED = '(prefers-reduced-motion: reduce)'
function subscribeSystemReduced(onChange: () => void): () => void {
  const query = window.matchMedia(SYSTEM_REDUCED)
  query.addEventListener('change', onChange)
  return () => query.removeEventListener('change', onChange)
}
const systemReduced = (): boolean => window.matchMedia(SYSTEM_REDUCED).matches

/** Movimiento reducido: el ajuste de la app o el del sistema. */
function useReducedMotion(): boolean {
  const { reduceMotion } = usePreferences()
  return useSyncExternalStore(subscribeSystemReduced, systemReduced) || reduceMotion
}

interface ThreeCharacterProps extends CharacterRendererProps {
  /** El avatar ya se ve (tras el fundido). */
  readonly onReady: () => void
  /** No hay WebGL2 o la carga falló: el padre vuelve al SVG. */
  readonly onFail: () => void
}

/**
 * Renderer 3D: un único lienzo WebGL con el avatar activo de `avatars/registry.ts`.
 * El bucle de dibujo lo lleva el avatar y se para solo con `document.hidden`.
 */
export function ThreeCharacter({ state, onReady, onFail }: ThreeCharacterProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const avatar = useRef<Avatar3D | null>(null)
  const latestState = useRef(state)
  const reduced = useReducedMotion()
  const latestReduced = useRef(reduced)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    let alive = true
    let instance: Avatar3D | null = null
    let fadeTimer: ReturnType<typeof setTimeout> | undefined
    const cleanups: Array<() => void> = []

    loadActiveAvatar()
      .then((create) => {
        if (!alive) return
        const created = create(canvas, {
          reducedMotion: latestReduced.current,
          pixelRatio: Math.min(window.devicePixelRatio || 1, MAX_PIXEL_RATIO)
        })
        instance = created
        avatar.current = created
        created.setState(latestState.current)

        const observer = new ResizeObserver((entries) => {
          const box = entries[0]?.contentRect
          if (box && box.width > 0 && box.height > 0) created.resize(box.width, box.height)
        })
        observer.observe(canvas)
        const onFocus = (): void => created.notify('focus')
        const onBlur = (): void => created.notify('blur')
        window.addEventListener('focus', onFocus)
        window.addEventListener('blur', onBlur)
        const stopTyping = subscribeUserTyping(() => created.notify('userTyping'))
        cleanups.push(() => {
          observer.disconnect()
          window.removeEventListener('focus', onFocus)
          window.removeEventListener('blur', onBlur)
          stopTyping()
        })
        return created.ready
      })
      .then(
        () => {
          if (alive) fadeTimer = setTimeout(() => alive && onReady(), FADE_MS)
        },
        (reason: unknown) => {
          if (!alive) return
          warnCharacter('el avatar 3D no pudo arrancar; se usa el SVG', reason)
          onFail()
        }
      )

    return () => {
      alive = false
      clearTimeout(fadeTimer)
      cleanups.forEach((cleanup) => cleanup())
      instance?.dispose()
      avatar.current = null
    }
  }, [onReady, onFail])

  useEffect(() => {
    latestState.current = state
    avatar.current?.setState(state)
  }, [state])

  useEffect(() => {
    latestReduced.current = reduced
    avatar.current?.setReducedMotion(reduced)
  }, [reduced])

  const applyMouth = useCallback((level: number | null) => {
    avatar.current?.setAudioLevel(level ?? 0)
  }, [])
  useMouthLevel(state, applyMouth)

  return <canvas ref={canvasRef} className="absolute inset-0 block size-full rounded-2xl" />
}
