import { AdaptiveCharacter } from './AdaptiveCharacter'
import type { CharacterRenderer } from './types'

// Punto de enchufe del personaje: AdaptiveCharacter.
// Elige según la preferencia avatarId (avatars/registry.ts): un avatar 3D, con el SVG de respaldo, o el
// personaje clásico (.riv del usuario si existe, docs/usage/personaje.md; si no, el SVG).
export const characterRenderer: CharacterRenderer | null = AdaptiveCharacter
