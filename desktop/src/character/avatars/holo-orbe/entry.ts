import type { CreateAvatar, CreateAvatarLayer } from '../types'
import { createAvatar } from './index'
import { createHoloOrbeLayer } from './layer'

/** Holo-Orbe con lienzo propio (modo Drakter, vista previa de Ajustes). Todo procedural: sin assets. */
export const create: CreateAvatar = (canvas, options) => createAvatar(canvas, options)

/** La misma implementación como capa de un renderer compartido (Stage de Jarvis). */
export const createLayer: CreateAvatarLayer = (renderer, options) => createHoloOrbeLayer(renderer, options)
