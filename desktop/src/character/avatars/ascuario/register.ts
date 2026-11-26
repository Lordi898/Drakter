import type { AvatarEntry } from '../registry'
import thumbnail from './thumbnail.webp?url'

/** Ficha y cargadores de Ascuario. No importa Three: el código del avatar se carga al usarlo. */
export const avatar: AvatarEntry = {
  meta: {
    id: 'ascuario',
    name: 'Ascuario',
    description: 'Dragón de escamas negras y vetas de fuego, con monóculo.',
    thumbnail,
    voiceAliases: ['dragón', 'dragon', 'ascuario']
  },
  load: () => import('./entry').then((module) => module.create),
  loadLayer: () => import('./entry').then((module) => module.createLayer),
  // Soporta `transparent`, pero su diseño cuenta con su halo de fondo.
  transparent: false
}
