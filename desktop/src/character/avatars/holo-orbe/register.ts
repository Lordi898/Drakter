import type { AvatarEntry } from '../registry'
import thumbnail from './thumbnail.webp?url'

/** Ficha y cargadores de Holo-Orbe. No importa Three: el código del avatar se carga al usarlo. */
export const avatar: AvatarEntry = {
  meta: {
    id: 'holo-orbe',
    name: 'Holo-Orbe',
    description: 'Busto holográfico de filamentos que nace de un orbe y vuelve a él al pensar.',
    thumbnail,
    voiceAliases: ['orbe', 'holo-orbe', 'holo orbe']
  },
  load: () => import('./entry').then((module) => module.create),
  loadLayer: () => import('./entry').then((module) => module.createLayer),
  transparent: true
}
