import type { CreateAvatar, CreateAvatarLayer } from '../types';
import { createHoloAvatar } from './index';
import { createHoloLayer } from './layer';

/** Holo-Contorno con lienzo propio (modo Drakter). Acepta además `theme` y expone `setTheme`. */
export const create: CreateAvatar = (canvas, options) => createHoloAvatar(canvas, options);

/** La misma implementación como capa de un renderer compartido (Stage de Jarvis). */
export const createLayer: CreateAvatarLayer = (renderer, options) => createHoloLayer(renderer, options);
