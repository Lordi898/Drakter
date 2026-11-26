import type { AvatarEntry } from '../registry'
import thumbnail from './thumbnail.webp?url'

/** Ficha y cargadores de Holo-Busto. No importa Three: el código del avatar se carga al usarlo. */
export const avatar: AvatarEntry = {
  meta: {
    id: 'holo-busto',
    name: 'Holo-Busto',
    description: 'Busto de caballero maduro esculpido en luz, con hebras de pelo y núcleo en el pecho.',
    thumbnail,
    voiceAliases: ['busto', 'holo-busto', 'holo busto']
  },
  load: () => import('./entry').then((module) => module.create),
  loadLayer: () => import('./entry').then((module) => module.createLayer),
  // Holograma: sin fondo propio flota sobre la interfaz (tema oscuro = luz aditiva, claro = tinta de cobalto).
  transparent: true
}
