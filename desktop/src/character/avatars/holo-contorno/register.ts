import type { AvatarEntry } from '../registry'
import thumbnail from './thumbnail.webp?url'

/** Ficha y cargadores de Holo-Contorno (avatar por defecto). No importa Three: el código se carga al usarlo. */
export const avatar: AvatarEntry = {
  meta: {
    id: 'holo-contorno',
    name: 'Holo-Contorno',
    description: 'Caballero maduro como holograma de curvas de nivel, con cintas de luz en los rasgos.',
    thumbnail,
    voiceAliases: ['contorno', 'holograma', 'holo-contorno', 'holo contorno']
  },
  load: () => import('./entry').then((module) => module.create),
  loadLayer: () => import('./entry').then((module) => module.createLayer),
  // Holograma: sin fondo propio flota sobre la interfaz (tema oscuro = luz aditiva, claro = tinta de cobalto).
  transparent: true
}
