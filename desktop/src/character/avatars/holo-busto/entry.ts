import type { CreateAvatar, CreateAvatarLayer } from '../types'
import geometryUrl from './holo-busto-geo.json?url'
import { createAvatar } from './index'
import { createHoloBustoLayer } from './layer'

/** Holo-busto con su malla horneada servida como asset de Vite (esculpirla en el navegador tarda 15-25 s). */
export const create: CreateAvatar = (canvas, options) => createAvatar(canvas, { ...options, geometryUrl })

/** La misma implementación como capa de un renderer compartido (Stage de Jarvis). */
export const createLayer: CreateAvatarLayer = (renderer, options) => createHoloBustoLayer(renderer, { ...options, geometryUrl })
