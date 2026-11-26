import type { CreateAvatar, CreateAvatarLayer } from '../types'
import { createAvatar } from './index'
import { createRelojeroLayer } from './layer'

export const create: CreateAvatar = (canvas, options) => createAvatar(canvas, options)

/** La misma implementación como capa de un renderer compartido (Stage de Jarvis). */
export const createLayer: CreateAvatarLayer = (renderer, options) => createRelojeroLayer(renderer, options)
