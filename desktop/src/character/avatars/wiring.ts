import { useCallback, useEffect } from 'react'
import { subscribeUserTyping } from '../activity'
import type { CharacterState } from '../types'
import { useMouthLevel } from '../useMouthLevel'
import type { Avatar3D } from './types'

/** Lo que los cables del personaje necesitan de un avatar (`Avatar3D` o `AvatarLayer`). */
export type AvatarControls = Pick<Avatar3D, 'setState' | 'setAudioLevel' | 'notify'>

/**
 * Los mismos cables que `ThreeCharacter`, para cualquier anfitrión (p. ej. el Stage de Jarvis):
 * estado → `setState`, nivel real de voz → `setAudioLevel`, foco y blur de la ventana y escritura en
 * el chat → `notify`. El movimiento reducido lo lleva cada anfitrión (el Stage lo pasa en su fotograma).
 * `controls` debe ser estable (o `null` mientras no exista).
 */
export function useAvatarWiring(controls: AvatarControls | null, state: CharacterState): void {
  useEffect(() => {
    controls?.setState(state)
  }, [controls, state])

  useEffect(() => {
    if (!controls) return
    const onFocus = (): void => controls.notify('focus')
    const onBlur = (): void => controls.notify('blur')
    window.addEventListener('focus', onFocus)
    window.addEventListener('blur', onBlur)
    const stopTyping = subscribeUserTyping(() => controls.notify('userTyping'))
    return () => {
      window.removeEventListener('focus', onFocus)
      window.removeEventListener('blur', onBlur)
      stopTyping()
    }
  }, [controls])

  const applyMouth = useCallback((level: number | null) => controls?.setAudioLevel(level ?? 0), [controls])
  useMouthLevel(state, applyMouth)
}
