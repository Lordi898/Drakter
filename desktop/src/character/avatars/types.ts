import type { CharacterState } from '../types'

/** Avisos de contexto que entiende cualquier avatar 3D. */
export type AvatarEvent = 'userTyping' | 'focus' | 'blur'

export interface AvatarOptions {
  readonly reducedMotion?: boolean
  readonly pixelRatio?: number
  /**
   * Lienzo con alfa premultiplicado y sin fondo propio: el avatar flota sobre la interfaz.
   * Solo se pide a los avatares que lo declaran en `registry.ts`.
   */
  readonly transparent?: boolean
}

/**
 * API común de los avatares 3D (concurso de avatares, ronda 2, punto 5). Cada avatar es un módulo
 * con `createAvatar(canvas, opts)` que devuelve esto; el anfitrión (ThreeCharacter) no sabe cuál es.
 */
export interface Avatar3D {
  setState(state: CharacterState): void
  /** Nivel de voz 0..1. */
  setAudioLevel(level: number): void
  setViseme?(viseme: string | null): void
  /** Mirada en coordenadas normalizadas -1..1. Si nunca se llama, el avatar sigue al ratón. */
  lookAt(x: number, y: number): void
  notify(event: AvatarEvent): void
  setReducedMotion(on: boolean): void
  /** Tamaño CSS del lienzo en px. */
  resize(width: number, height: number): void
  /** Libera geometrías, materiales, listeners y el bucle. */
  dispose(): void
  /** Si existe, se resuelve con el primer fotograma listo y se rechaza si la carga falla. */
  readonly ready?: Promise<void>
}

/** Lanza (p. ej. sin WebGL2) si el avatar no puede arrancar: el anfitrión cae al SVG. */
export type CreateAvatar = (canvas: HTMLCanvasElement, options: AvatarOptions) => Avatar3D
