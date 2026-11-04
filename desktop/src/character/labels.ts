import type { CharacterState } from './types'

/** Única fuente de etiquetas de estado: las usan el indicador y el hueco del personaje. */
export const CHARACTER_STATE_LABELS: Record<CharacterState, string> = {
  idle: 'Disponible',
  listening: 'Escuchando',
  thinking: 'Pensando',
  speaking: 'Hablando',
  executing: 'Trabajando',
  success: 'Hecho',
  error: 'Con un error',
  interrupted: 'Interrumpido',
  offline: 'Desconectado'
}
