import type { CreateAvatar, CreateAvatarLayer } from './types'

export interface AvatarEntry {
  /** Carga diferida: Three.js y la malla no pesan en el arranque ni se descargan si el avatar no se usa. */
  readonly load: () => Promise<CreateAvatar>
  /** El avatar sabe dibujarse sin fondo propio (`AvatarOptions.transparent`) y flota sobre la interfaz. */
  readonly transparent: boolean
  /**
   * Variante de capa para un lienzo compartido (modo Jarvis). Si falta, Jarvis usa `load` en un
   * segundo lienzo. Mismo Three.js (versión fija) que el anfitrión.
   */
  readonly loadLayer?: () => Promise<CreateAvatarLayer>
}

/**
 * Avatares 3D disponibles. Cómo añadir uno: `README.md` de esta carpeta (su `entry.ts` exporta
 * `create: CreateAvatar` y, para el Stage de Jarvis, `createLayer: CreateAvatarLayer`).
 */
const AVATARS = {
  // Provisional. Soporta `transparent`, pero su diseño cuenta con su halo de fondo.
  ascuario: {
    load: () => import('./ascuario/entry').then((module) => module.create),
    loadLayer: () => import('./ascuario/entry').then((module) => module.createLayer),
    transparent: false
  },
  // El Relojero v2: figura opaca de latón y laca. Con `transparent` no pinta su fondo; en tema claro baja la ganancia de los destellos.
  relojero: {
    load: () => import('./relojero/entry').then((module) => module.create),
    loadLayer: () => import('./relojero/entry').then((module) => module.createLayer),
    transparent: true
  },
  // Filamento v2 (dorado): luz aditiva pura. En tema claro pone una tarjeta oscura propia con esquinas redondeadas.
  filamento: {
    load: () => import('./filamento/entry').then((module) => module.create),
    loadLayer: () => import('./filamento/entry').then((module) => module.createLayer),
    transparent: true
  },
  // Holo-Filamento (azul): busto sólido oscuro más hebras de luz. En tema claro, lo que flota fuera del busto pasa a tinta cobalto.
  'holo-filamento': {
    load: () => import('./holo-filamento/entry').then((module) => module.create),
    loadLayer: () => import('./holo-filamento/entry').then((module) => module.createLayer),
    transparent: true
  }
} satisfies Record<string, AvatarEntry>

export type AvatarId = keyof typeof AVATARS

/**
 * Avatar activo. Cambiar de avatar es cambiar esta línea (p. ej. `'ascuario'`).
 * `null` = sin avatar 3D: el personaje de siempre (.riv si existe, si no el SVG) y Three.js no se descarga.
 */
export const ACTIVE_AVATAR: AvatarId | null = null

export const activeAvatar: AvatarEntry | null = ACTIVE_AVATAR === null ? null : AVATARS[ACTIVE_AVATAR]
