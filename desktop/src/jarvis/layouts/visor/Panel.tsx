/**
 * Panel del Visor: con Stage, un nodo DOM colocado en el cilindro por la capa `visor-world` (CSS3D)
 * sobre su fondo curvo en WebGL; React pinta dentro con un portal. Sin Stage («HUD sin lienzo»),
 * el mismo contenido en una tarjeta normal dentro de la rejilla DOM.
 */
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import type { PanelSpec, VisorWorld } from './stage/world'

export const WorldContext = createContext<VisorWorld | null>(null)

interface PanelProps extends PanelSpec {
  readonly title: string
  /** Código corto del panel (cabecera, fijación de objetivo). */
  readonly code: string
  readonly className?: string
  readonly children?: ReactNode
}

export function Panel({ title, code, className, children, ...spec }: PanelProps) {
  const world = useContext(WorldContext)
  const [el] = useState(() => {
    const node = document.createElement('section')
    node.dataset.lock = title
    node.dataset.code = code
    return node
  })
  const key = `${spec.sector}|${spec.dA ?? 0}|${spec.R ?? 0}|${spec.y ?? 0}|${spec.w}|${spec.h}|${spec.side ? 1 : 0}|${spec.alpha ?? 1}|${spec.avatar ? 1 : 0}`
  useEffect(() => {
    if (!world) return
    if (className) el.classList.add(...className.split(/\s+/).filter(Boolean))
    return world.addPanel(el, spec)
    // `key` resume `spec`: el panel solo se recoloca si cambia su sitio.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [world, el, key, className])

  const body = (
    <>
      <header className="jv-visor-pnl-h">
        <span className="pt">{title}</span>
        <span className="pc">{code}</span>
      </header>
      <div className="jv-visor-pnl-b">{children}</div>
    </>
  )
  if (!world) {
    return (
      <section className={`jv-visor-card ${className ?? ''}`} data-lock={title} data-code={code}>
        {body}
      </section>
    )
  }
  return createPortal(body, el)
}
