import { AdaptiveCharacter } from './AdaptiveCharacter'
import type { CharacterRenderer } from './types'

// Punto de enchufe del personaje. AdaptiveCharacter usa el .riv del usuario si existe
// (docs/usage/personaje.md); si no, el avatar 3D activo (avatars/registry.ts; ninguno por defecto) y, si no hay o falla, el SVG.
export const characterRenderer: CharacterRenderer | null = AdaptiveCharacter
