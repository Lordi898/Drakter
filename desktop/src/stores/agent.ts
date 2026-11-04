import type { CharacterState } from '@/character/types'

/**
 * Estado de Drakter visto por la interfaz. Sin backend no hay eventos, así que
 * es `offline` de forma honesta. El equipo de comunicación conectará aquí los
 * eventos reales; ningún componente debe simular otro estado.
 */
export function useDrakterState(): CharacterState {
  return 'offline'
}
