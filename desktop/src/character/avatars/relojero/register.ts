import type { AvatarEntry } from '../registry'
import thumbnail from './thumbnail.webp?url'

/** Ficha y cargadores de El Relojero. No importa Three: el código del avatar se carga al usarlo. */
export const avatar: AvatarEntry = {
  meta: {
    id: 'relojero',
    name: 'El Relojero',
    description: 'Autómata de relojería de latón y laca, con un mecanismo a la vista.',
    thumbnail,
    voiceAliases: ['relojero', 'reloj']
  },
  load: () => import('./entry').then((module) => module.create),
  loadLayer: () => import('./entry').then((module) => module.createLayer),
  // Opaco: sin fondo propio flota igual. En tema claro solo baja la ganancia de sus destellos.
  transparent: true
}
