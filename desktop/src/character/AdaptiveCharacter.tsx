import { useCallback, useEffect, useState } from 'react'
import { warnCharacter } from './log'
import { RiveCharacter } from './RiveCharacter'
import { SvgCharacter } from './SvgCharacter'
import type { CharacterRendererProps } from './types'

/** El proceso principal sirve aquí el .riv del usuario (404 si no existe). */
const RIV_URL = '/__character/drakter.riv'

type Source = { kind: 'checking' } | { kind: 'rive'; buffer: ArrayBuffer } | { kind: 'svg' }

/**
 * Usa el .riv del usuario si existe y carga; si no, o si falla, el SVG provisional sin errores.
 * Mientras se comprueba (unos ms, en local) ya se dibuja el SVG para no dejar el hueco vacío.
 */
export function AdaptiveCharacter(props: CharacterRendererProps) {
  const [source, setSource] = useState<Source>({ kind: 'checking' })

  useEffect(() => {
    let alive = true
    fetch(RIV_URL, { cache: 'no-store' })
      .then((response) => {
        if (response.ok) return response.arrayBuffer()
        // 404 = el usuario aún no tiene .riv: es lo normal y no se avisa.
        if (response.status !== 404) warnCharacter(`el .riv no se pudo leer (HTTP ${response.status}); se usa el SVG`)
        return null
      })
      .then((buffer) => {
        if (!alive) return
        if (buffer && buffer.byteLength === 0) warnCharacter('el .riv está vacío; se usa el SVG')
        setSource(buffer && buffer.byteLength > 0 ? { kind: 'rive', buffer } : { kind: 'svg' })
      })
      .catch((reason: unknown) => {
        warnCharacter('no se pudo pedir el .riv; se usa el SVG', reason)
        if (alive) setSource({ kind: 'svg' })
      })
    return () => {
      alive = false
    }
  }, [])

  const fallback = useCallback(() => {
    warnCharacter('el .riv no cargó o no tiene la state machine «Drakter»; se usa el SVG')
    setSource({ kind: 'svg' })
  }, [])

  if (source.kind === 'rive') return <RiveCharacter {...props} buffer={source.buffer} onFail={fallback} />
  return <SvgCharacter {...props} />
}
