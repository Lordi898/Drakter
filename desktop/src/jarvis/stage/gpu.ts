/** Detección de GPU, una vez al montar (jarvis-arquitectura.md §2.6). */
import type { QualityTier } from './types'

export interface GpuInfo {
  /** Texto de `RENDERER` (con ANGLE ya trae el modelo). */
  readonly renderer: string
  /** SwiftShader, llvmpipe…: Ahorro y sin partículas. */
  readonly software: boolean
  /** Nivel de partida para `auto`. */
  readonly tier: QualityTier
}

const SOFTWARE = /swiftshader|llvmpipe|softpipe|software|basic render/i
const INTEGRATED = /intel|iris|uhd|hd graphics|mali|adreno|powervr|videocore/i

export function classifyGpu(renderer: string, cores: number): GpuInfo {
  if (SOFTWARE.test(renderer)) return { renderer, software: true, tier: 'ahorro' }
  if (INTEGRATED.test(renderer)) return { renderer, software: false, tier: 'equilibrado' }
  // Dedicada; con 4 núcleos o menos la CPU no da para Cine.
  return { renderer, software: false, tier: cores <= 4 ? 'equilibrado' : 'cine' }
}

/**
 * Prueba en un lienzo desechable: los atributos del contexto real (antialias) dependen del nivel.
 * `null` = sin WebGL2.
 */
export function detectGpu(): GpuInfo | null {
  const probe = document.createElement('canvas')
  const gl = probe.getContext('webgl2', { failIfMajorPerformanceCaveat: false })
  if (!gl) return null
  const ext = gl.getExtension('WEBGL_debug_renderer_info')
  const renderer = String(gl.getParameter(ext ? ext.UNMASKED_RENDERER_WEBGL : gl.RENDERER) ?? '')
  gl.getExtension('WEBGL_lose_context')?.loseContext()
  return classifyGpu(renderer, navigator.hardwareConcurrency || 4)
}
