import { AdaptiveCharacter } from './AdaptiveCharacter'
import type { CharacterRenderer } from './types'

// Punto de enchufe del personaje. AdaptiveCharacter usa el .riv del usuario si existe
// (docs/usage/personaje.md) y, si no, el SVG provisional.
export const characterRenderer: CharacterRenderer | null = AdaptiveCharacter
