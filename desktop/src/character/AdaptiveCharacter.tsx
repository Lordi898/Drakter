import { useCallback, useEffect, useState } from 'react'
import { activeAvatar } from './avatars/registry'
import { warnCharacter } from './log'
import { RiveCharacter } from './RiveCharacter'
import { SvgCharacter } from './SvgCharacter'
import { ThreeCharacter } from './ThreeCharacter'
import type { CharacterRendererProps } from './types'

/** El proceso principal sirve aquí el .riv del usuario (204/404 si no existe). */
const RIV_URL = '/__character/drakter.riv'

type Source = { kind: 'checking' } | { kind: 'rive'; buffer: ArrayBuffer } | { kind: 'three' } | { kind: 'svg' }

/** Sin .riv: el avatar 3D activo o, si no hay ninguno (`ACTIVE_AVATAR = null`), el SVG. */
const NO_RIV: Source = activeAvatar ? { kind: 'three' } : { kind: 'svg' }
const NO_RIV_LABEL = activeAvatar ? 'el avatar 3D' : 'el SVG'

/**
 * Orden: el .riv del usuario si existe (alternativa explícita); si no, el avatar 3D activo, si lo hay;
 * y, sin avatar 3D, sin WebGL2 o si algo falla, el SVG provisional. El SVG se dibuja desde el primer
 * momento y se retira cuando el avatar 3D ya se ve, para no dejar nunca el hueco vacío.
 */
export function AdaptiveCharacter(props: CharacterRendererProps) {
  const [source, setSource] = useState<Source>({ kind: 'checking' })
  const [threeReady, setThreeReady] = useState(false)

  useEffect(() => {
    let alive = true
    fetch(RIV_URL, { cache: 'no-store' })
      .then((response) => {
        // 204 (o 404) = el usuario no tiene .riv: es lo normal y no se avisa.
        if (response.status === 204) return null
        // En desarrollo el servidor de Vite responde a cualquier ruta con index.html.
        if (response.headers.get('Content-Type')?.startsWith('text/html')) return null
        if (response.ok) return response.arrayBuffer()
        if (response.status !== 404) warnCharacter(`el .riv no se pudo leer (HTTP ${response.status}); se usa ${NO_RIV_LABEL}`)
        return null
      })
      .then((buffer) => {
        if (!alive) return
        if (buffer && buffer.byteLength === 0) warnCharacter(`el .riv está vacío; se usa ${NO_RIV_LABEL}`)
        setSource(buffer && buffer.byteLength > 0 ? { kind: 'rive', buffer } : NO_RIV)
      })
      .catch((reason: unknown) => {
        warnCharacter(`no se pudo pedir el .riv; se usa ${NO_RIV_LABEL}`, reason)
        if (alive) setSource(NO_RIV)
      })
    return () => {
      alive = false
    }
  }, [])

  const riveFailed = useCallback(() => {
    warnCharacter(`el .riv no cargó o no tiene la state machine «Drakter»; se usa ${NO_RIV_LABEL}`)
    setSource(NO_RIV)
  }, [])
  const threeFailed = useCallback(() => setSource({ kind: 'svg' }), [])
  const threeShown = useCallback(() => setThreeReady(true), [])

  if (source.kind === 'rive') return <RiveCharacter {...props} buffer={source.buffer} onFail={riveFailed} />
  const three = source.kind === 'three' ? activeAvatar : null
  const svgVisible = !three || !threeReady
  // Hijos en posiciones fijas: el SVG no se vuelve a montar al pasar de «checking» a «three».
  return (
    <div className="relative size-full">
      {svgVisible ? (
        <div className="absolute inset-0">
          <SvgCharacter {...props} />
        </div>
      ) : null}
      {three ? <ThreeCharacter {...props} avatar={three} onReady={threeShown} onFail={threeFailed} /> : null}
    </div>
  )
}
