/**
 * Anclajes 3D → DOM (jarvis-arquitectura.md §2.4): una capa sin GL, la última en dibujarse, que
 * escribe `--jv-x`/`--jv-y` (px CSS) y `data-anchor-visible` en los nodos enlazados. Sin React por
 * fotograma y solo cuando el valor cambia.
 */
import type { Stage, StageLayer } from './types'

export interface AnchorLayer extends StageLayer {
  /** Enlaza un nodo a un anclaje (`StageLayer.anchors()`); devuelve la función para soltarlo. */
  bind(element: HTMLElement, anchorId: string): () => void
}

interface Binding {
  readonly element: HTMLElement
  readonly id: string
  x: number
  y: number
  visible: boolean | null
}

export function createAnchorLayer(stage: Pick<Stage, 'anchor'>): AnchorLayer {
  const bindings = new Set<Binding>()
  return {
    id: 'anchors',
    order: Number.MAX_SAFE_INTEGER,
    bind(element, id) {
      const b: Binding = { element, id, x: Number.NaN, y: Number.NaN, visible: null }
      bindings.add(b)
      return () => bindings.delete(b)
    },
    init() {},
    update() {},
    render() {
      for (const b of bindings) {
        const a = stage.anchor(b.id)
        const visible = a?.visible ?? false
        if (a && (Math.abs(a.x - b.x) >= 0.25 || Math.abs(a.y - b.y) >= 0.25)) {
          b.x = a.x
          b.y = a.y
          b.element.style.setProperty('--jv-x', `${a.x.toFixed(1)}px`)
          b.element.style.setProperty('--jv-y', `${a.y.toFixed(1)}px`)
        }
        if (visible !== b.visible) {
          b.visible = visible
          b.element.dataset.anchorVisible = String(visible)
        }
      }
    },
    dispose() {
      bindings.clear()
    }
  }
}
