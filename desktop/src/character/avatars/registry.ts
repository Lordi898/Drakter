import { useSyncExternalStore } from 'react'
import { getPreferences, subscribePreferences } from '@/stores/preferences'
import { avatar as ascuario } from './ascuario/register'
import { avatar as filamento } from './filamento/register'
import { avatar as holoFilamento } from './holo-filamento/register'
import { avatar as relojero } from './relojero/register'
import { avatar as holoBusto } from './holo-busto/register'
import { avatar as holoContorno } from './holo-contorno/register'
import { avatar as holoHilo } from './holo-hilo/register'
import type { AvatarMeta, CreateAvatar, CreateAvatarLayer } from './types'

export interface AvatarEntry {
  /** Ficha para elegirlo (nombre, miniatura, alias de voz). */
  readonly meta: AvatarMeta
  /** Carga diferida: Three.js y la malla no pesan en el arranque ni se descargan si el avatar no se usa. */
  readonly load: () => Promise<CreateAvatar>
  /** Variante de capa para el Stage de Jarvis (lienzo compartido). Si falta, Jarvis usa `load` en un segundo lienzo. */
  readonly loadLayer?: () => Promise<CreateAvatarLayer>
  /** Sabe dibujarse sin fondo propio (`AvatarOptions.transparent`) y flota sobre la interfaz. */
  readonly transparent: boolean
}

/**
 * Avatares portados, en el orden en que se muestran. Para añadir uno: `README.md` de esta carpeta
 * (su `register.ts` exporta `avatar: AvatarEntry`) y una línea aquí y otra en los imports.
 */
const AVATARS: readonly AvatarEntry[] = [holoContorno, holoHilo, holoBusto, holoFilamento, ascuario, relojero, filamento]

/** Valor de la preferencia `avatarId` para «sin avatar 3D» (personaje clásico: .riv o SVG). */
export const NO_AVATAR = 'none'
/** Avatar por defecto (decisión del usuario). */
export const DEFAULT_AVATAR_ID = 'holo-contorno'

const BY_ID: ReadonlyMap<string, AvatarEntry> = new Map(AVATARS.map((entry) => [entry.meta.id, entry]))

/** Avatares que se pueden elegir (sin «ninguno»). */
export function listAvatars(): readonly AvatarEntry[] {
  return AVATARS
}

/** Ids elegibles, para validar órdenes de voz o de la herramienta (incluye `NO_AVATAR`). */
export function avatarIds(): readonly string[] {
  return [NO_AVATAR, ...BY_ID.keys()]
}

/** El avatar de ese id, o `null` para «ninguno», un id desconocido o uno aún no portado. Nunca lanza. */
export function resolveAvatar(id: string): AvatarEntry | null {
  return BY_ID.get(id) ?? null
}

/** Busca por alias de voz o por nombre (minúsculas, sin acentos). `null` si no hay coincidencia. */
export function findAvatarByAlias(text: string): AvatarEntry | null {
  const norm = (value: string): string => value.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase().trim()
  const wanted = norm(text)
  return (
    AVATARS.find(
      (entry) =>
        norm(entry.meta.name) === wanted ||
        entry.meta.id === wanted ||
        entry.meta.voiceAliases.some((alias) => norm(alias) === wanted)
    ) ?? null
  )
}

/** Avatar activo según la preferencia `avatarId`. */
export function getActiveAvatar(): AvatarEntry | null {
  return resolveAvatar(getPreferences().avatarId)
}

/** Avatar activo, reactivo: cambia al elegir otro en Ajustes, en Jarvis o por voz. */
export function useActiveAvatar(): AvatarEntry | null {
  return useSyncExternalStore(subscribePreferences, getActiveAvatar)
}
