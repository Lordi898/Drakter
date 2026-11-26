import type { CreateAvatar, CreateAvatarLayer } from '../types';
import { createHoloAvatar } from '../holo-contorno/index';
import { createHoloLayer } from '../holo-contorno/layer';
import { holoHilo } from './variant';

/** Holo-Hilo con lienzo propio (modo Drakter): Holo-Contorno con su trama de filamentos. */
export const create: CreateAvatar = (canvas, options) => createHoloAvatar(canvas, { ...options, variant: holoHilo });

/** La misma implementación como capa de un renderer compartido (Stage de Jarvis). */
export const createLayer: CreateAvatarLayer = (renderer, options) => createHoloLayer(renderer, { ...options, variant: holoHilo });
