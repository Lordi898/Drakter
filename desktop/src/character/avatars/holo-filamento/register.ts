import type { AvatarEntry } from '../registry'
import thumbnail from './thumbnail.webp?url'

/** Ficha y cargadores de Holo-Filamento. No importa Three: el código del avatar se carga al usarlo. */
export const avatar: AvatarEntry = {
  meta: {
    id: 'holo-filamento',
    name: 'Holo-Filamento',
    description: 'Un busto holográfico tejido con hebras de luz azul sobre un cuerpo oscuro.',
    thumbnail,
    voiceAliases: ['filamento azul', 'holofilamento']
  },
  load: () => import('./entry').then((module) => module.create),
  loadLayer: () => import('./entry').then((module) => module.createLayer),
  // En tema claro, lo que flota fuera del busto pasa a tinta cobalto.
  transparent: true
}
