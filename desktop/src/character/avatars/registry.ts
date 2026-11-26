import type { CreateAvatar } from './types'

export interface AvatarEntry {
  /** Carga diferida: Three.js y la malla no pesan en el arranque ni se descargan si el avatar no se usa. */
  readonly load: () => Promise<CreateAvatar>
  /** El avatar sabe dibujarse sin fondo propio (`AvatarOptions.transparent`) y flota sobre la interfaz. */
  readonly transparent: boolean
}

/**
 * Avatares 3D disponibles. Para añadir otro: su carpeta con un `entry.ts` que exporte
 * `create: CreateAvatar`, y una entrada aquí.
 */
const AVATARS = {
  // Provisional. Soporta `transparent`, pero su diseño cuenta con su halo de fondo.
  ascuario: { load: () => import('./ascuario/entry').then((module) => module.create), transparent: false }
} satisfies Record<string, AvatarEntry>

export type AvatarId = keyof typeof AVATARS

/**
 * Avatar activo. Cambiar de avatar es cambiar esta línea (p. ej. `'ascuario'`).
 * `null` = sin avatar 3D: el personaje de siempre (.riv si existe, si no el SVG) y Three.js no se descarga.
 */
export const ACTIVE_AVATAR: AvatarId | null = null

export const activeAvatar: AvatarEntry | null = ACTIVE_AVATAR === null ? null : AVATARS[ACTIVE_AVATAR]
