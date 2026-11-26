/**
 * Contrato del Stage del modo Jarvis: un ÚNICO lienzo WebGL2 a pantalla completa bajo el HUD en DOM.
 * Todas las capas (fondo, retícula, partículas, grafo, avatar, osciloscopio…) comparten renderer y bucle.
 * React no corre por fotograma: los paneles pasan datos a sus capas cuando cambian los stores.
 * Diseño: jarvis-arquitectura.md §2.4-§2.7 y §4.3.
 */
import type { WebGLRenderer } from 'three'

export type QualityTier = 'cine' | 'equilibrado' | 'ahorro'

export interface QualityProfile {
  readonly tier: QualityTier
  readonly maxFps: 30 | 60
  /** fps en reposo; 0 = solo se dibuja a demanda (`Stage.requestFrame`). */
  readonly idleFps: number
  /** Máximo de píxeles físicos del lienzo; la escala de render se deriva de él. */
  readonly pixelBudget: number
  readonly bloom: 'half' | 'off'
  /** Partículas instanciadas como máximo. */
  readonly particles: number
  readonly parallax: boolean
}

/** Lo que cada capa recibe en cada fotograma. Solo lectura: lo escribe el Stage. */
export interface StageFrame {
  readonly renderer: WebGLRenderer
  readonly quality: QualityProfile
  readonly reducedMotion: boolean
  /** Tamaño CSS del lienzo en px. */
  readonly width: number
  readonly height: number
  /** Píxeles físicos por px CSS tras aplicar `pixelBudget` (incluye el devicePixelRatio). */
  readonly renderScale: number
  /** Puntero normalizado -1..1 (y hacia arriba); `active` = dentro de la ventana. */
  readonly pointer: { readonly x: number; readonly y: number; readonly active: boolean }
  /** Segundos desde el montaje y desde el fotograma anterior. */
  readonly time: number
  readonly dt: number
}

/** Punto de la escena proyectado a px CSS (origen arriba a la izquierda), para anclar paneles DOM. */
export interface StageAnchor {
  readonly x: number
  readonly y: number
  readonly visible: boolean
}

export interface StageLayer {
  readonly id: string
  /** Orden de dibujo ascendente. */
  readonly order: number
  /** Crea recursos; puede compilar shaders (el Stage espera a todas antes de `ready`). */
  init(frame: StageFrame): void | Promise<void>
  update(frame: StageFrame): void
  /** El Stage deja `autoClear = false`; la capa restaura cualquier estado global que cambie. */
  render(frame: StageFrame): void
  resize?(frame: StageFrame): void
  setQuality?(quality: QualityProfile): void
  anchors?(): Readonly<Record<string, StageAnchor>>
  /** Libera geometrías, materiales y texturas; nunca el renderer. */
  dispose(): void
}

export interface StageStats {
  readonly fps: number
  /** Percentil 90 del tiempo de fotograma (ms) en la última ventana del regulador. */
  readonly p90ms: number
  readonly tier: QualityTier
  readonly renderScale: number
  readonly calls: number
  readonly tris: number
}

export interface Stage {
  /** Capas iniciadas y shaders compilados: el primer fotograma ya no da tirones. */
  readonly ready: Promise<void>
  add(layer: StageLayer): void
  remove(id: string): void
  /** `auto` = según la GPU y el regulador; un nivel fijo solo baja ante tirones sostenidos. */
  setQuality(tier: QualityTier | 'auto'): void
  setReducedMotion(on: boolean): void
  /** Pide un fotograma (modo a demanda o tras un cambio de datos). */
  requestFrame(): void
  anchor(id: string): StageAnchor | null
  stats(): StageStats
  /** Para el bucle y libera todas las capas y el renderer. */
  dispose(): void
}

export interface StageOptions {
  readonly quality: QualityTier | 'auto'
  readonly reducedMotion: boolean
}

/** Lanza si no hay WebGL2: Jarvis sigue en «HUD sin lienzo» (solo DOM). */
export type CreateStage = (canvas: HTMLCanvasElement, options: StageOptions) => Stage
