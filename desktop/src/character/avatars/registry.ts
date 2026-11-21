import type { CreateAvatar } from './types'

/**
 * Avatares 3D disponibles. Cada uno se carga aparte (import dinámico): Three.js y la malla
 * no pesan en el arranque ni se descargan si el avatar no se usa.
 * Para añadir otro finalista: su carpeta con un `entry.ts` que exporte `create: CreateAvatar`.
 */
const AVATARS = {
  ascuario: () => import('./ascuario/entry').then((module) => module.create)
} satisfies Record<string, () => Promise<CreateAvatar>>

export type AvatarId = keyof typeof AVATARS

/** Avatar activo. Cambiar de avatar es cambiar esta línea. */
export const ACTIVE_AVATAR: AvatarId = 'ascuario'

export function loadActiveAvatar(): Promise<CreateAvatar> {
  return AVATARS[ACTIVE_AVATAR]()
}
