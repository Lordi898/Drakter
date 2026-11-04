import type { ComponentType } from 'react'

/** Estados funcionales del personaje (CLAUDE.md §2). Tipo local de la UI, no un contrato de red. */
export const CHARACTER_STATES = [
  'idle',
  'listening',
  'thinking',
  'speaking',
  'executing',
  'success',
  'error',
  'interrupted',
  'offline'
] as const

export type CharacterState = (typeof CHARACTER_STATES)[number]
export type CharacterSize = 'compact' | 'expanded'

export interface CharacterRendererProps {
  readonly state: CharacterState
  readonly size: CharacterSize
}

export type CharacterRenderer = ComponentType<CharacterRendererProps>
