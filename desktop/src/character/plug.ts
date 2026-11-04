import { SvgCharacter } from './SvgCharacter'
import type { CharacterRenderer } from './types'

// Punto de enchufe del personaje: cambiar esta línea es lo único necesario para enchufarlo.
// Para sustituir el SVG por el .riv real, ver ./rive.md.
export const characterRenderer: CharacterRenderer | null = SvgCharacter
