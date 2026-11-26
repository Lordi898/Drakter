/** Niveles de calidad del Stage (jarvis-arquitectura.md §2.6). */
import type { QualityProfile, QualityTier } from './types'

export const PROFILES: Readonly<Record<QualityTier, QualityProfile>> = {
  cine: { tier: 'cine', maxFps: 60, idleFps: 30, pixelBudget: 2_100_000, bloom: 'half', particles: 20_000, parallax: true },
  equilibrado: { tier: 'equilibrado', maxFps: 30, idleFps: 20, pixelBudget: 1_300_000, bloom: 'off', particles: 6_000, parallax: true },
  ahorro: { tier: 'ahorro', maxFps: 30, idleFps: 0, pixelBudget: 800_000, bloom: 'off', particles: 1_000, parallax: false }
}

/** De menos a más caro. */
export const TIERS: readonly QualityTier[] = ['ahorro', 'equilibrado', 'cine']

/**
 * Píxeles físicos por px CSS: `dpr · min(1, √(presupuesto / (w·h·dpr²)))`. Un 4K o un DPR 2 no
 * multiplican el coste: el lienzo nunca pasa de `budget` píxeles.
 */
export function renderScaleFor(budget: number, width: number, height: number, dpr: number): number {
  const area = Math.max(1, width * height * dpr * dpr)
  return dpr * Math.min(1, Math.sqrt(budget / area))
}
