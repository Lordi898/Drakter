import type { ServerEvent } from '@/services/protocol'
import { subscribeServerEvents } from '@/services/ws'
import type { CharacterState } from './types'

/** Destino de lo que el receptor traduce. El estado NO pasa por aquí: llega por la prop `state`. */
export interface CharacterSink {
  setState(state: CharacterState): void
  setExpression(expression: string): void
  /** Apertura de boca 0..1, reservada para la voz futura. */
  setMouth(level: number): void
}

/** Lista cerrada de expresiones aceptadas. Lo que no esté aquí se ignora. */
export const KNOWN_EXPRESSIONS = [
  'neutral',
  'happy',
  'curious',
  'concerned',
  'surprised',
  'focused'
] as const

export type CharacterExpression = (typeof KNOWN_EXPRESSIONS)[number]

export function isKnownExpression(value: string): value is CharacterExpression {
  return (KNOWN_EXPRESSIONS as readonly string[]).includes(value)
}

/**
 * Suscribe el sink a los eventos del servidor. La expresión es texto no confiable:
 * se valida contra KNOWN_EXPRESSIONS y lo desconocido se descarta sin reenviarlo.
 * Devuelve la función para cancelar la suscripción.
 */
export function startCharacterReceiver(sink: CharacterSink): () => void {
  return subscribeServerEvents((event: ServerEvent) => {
    if (event.type !== 'agent.expression_changed') return
    const expression = event.payload.expression
    if (isKnownExpression(expression)) sink.setExpression(expression)
  })
}
