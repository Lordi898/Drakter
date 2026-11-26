import type { JarvisLayoutChoice } from '@/stores/preferences'

/**
 * Catálogo visible de las interfaces Jarvis (Ajustes, selector rápido, Ctrl+K). Va fuera de `jarvis/`
 * porque lo usa Drakter sin cargar el chunk de Jarvis; la carga de cada una está en
 * `jarvis/layouts/registry.ts`.
 */
export interface JarvisLayoutInfo {
  readonly id: JarvisLayoutChoice
  readonly name: string
  readonly description: string
}

export const JARVIS_LAYOUTS: readonly JarvisLayoutInfo[] = [
  { id: 'nucleo', name: 'Núcleo', description: 'Un astrolabio de luz: el avatar en el centro y cada sección como un anillo a su alrededor.' },
  { id: 'holomesa', name: 'Holomesa', description: 'Una mesa de operaciones: cada sección es una maqueta de luz que se puede rodear.' },
  { id: 'visor', name: 'Visor', description: 'Un visor curvo a tu alrededor: giras la vista para pasar de una sección a otra.' }
] satisfies readonly JarvisLayoutInfo[]

export function jarvisLayoutInfo(id: JarvisLayoutChoice): JarvisLayoutInfo {
  return JARVIS_LAYOUTS.find((layout) => layout.id === id) ?? JARVIS_LAYOUTS[0]!
}
