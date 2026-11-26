import type { AvatarEntry } from '../registry'
import thumbnail from './thumbnail.webp?url'

/** Ficha y cargadores de Holo-Hilo (variante de Holo-Contorno). No importa Three: el código se carga al usarlo. */
export const avatar: AvatarEntry = {
  meta: {
    id: 'holo-hilo',
    name: 'Holo-Hilo',
    description: 'El holograma de Holo-Contorno tejido con miles de filamentos de luz que reaccionan a cada estado.',
    thumbnail,
    voiceAliases: ['hilo', 'hilos', 'holo-hilo', 'holo hilo']
  },
  load: () => import('./entry').then((module) => module.create),
  loadLayer: () => import('./entry').then((module) => module.createLayer),
  // Holograma: sin fondo propio flota sobre la interfaz (tema oscuro = luz aditiva, claro = tinta de cobalto).
  transparent: true
}
