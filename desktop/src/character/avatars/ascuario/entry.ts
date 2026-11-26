import type { CreateAvatar } from '../types'
import geometryUrl from './ascuario-geo.json?url'
import { createAvatar } from './index'

/** Ascuario con su malla horneada servida como asset de Vite (sin ella esculpiría al arrancar). */
export const create: CreateAvatar = (canvas, options) => createAvatar(canvas, { ...options, geometryUrl })
