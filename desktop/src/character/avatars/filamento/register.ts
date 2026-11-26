import type { AvatarEntry } from '../registry'
import thumbnail from './thumbnail.webp?url'

/** Ficha y cargadores de Filamento (dorado). No importa Three: el código del avatar se carga al usarlo. */
export const avatar: AvatarEntry = {
  meta: {
    id: 'filamento',
    name: 'Filamento (dorado)',
    description: 'Un busto tejido con hebras de luz ámbar que se deshacen y se vuelven a tejer.',
    thumbnail,
    voiceAliases: ['filamento dorado']
  },
  load: () => import('./entry').then((module) => module.create),
  loadLayer: () => import('./entry').then((module) => module.createLayer),
  // Luz aditiva pura: en tema claro pone su propia tarjeta oscura con esquinas redondeadas.
  transparent: true
}
