import type { CreateAvatar, CreateAvatarLayer } from '../types'
import geometryUrl from './ascuario-geo.json?url'
import { createAvatar } from './index'
import { createAscuarioLayer } from './layer'

/** Ascuario con su malla horneada servida como asset de Vite (sin ella esculpiría al arrancar). */
export const create: CreateAvatar = (canvas, options) => createAvatar(canvas, { ...options, geometryUrl })

/** La misma implementación como capa de un renderer compartido (Stage de Jarvis). */
export const createLayer: CreateAvatarLayer = (renderer, options) => createAscuarioLayer(renderer, { ...options, geometryUrl })
