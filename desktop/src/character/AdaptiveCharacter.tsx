import { useCallback, useEffect, useState } from 'react'
import { useActiveAvatar, type AvatarEntry } from './avatars/registry'
import { warnCharacter } from './log'
import { RiveCharacter } from './RiveCharacter'
import { SvgCharacter } from './SvgCharacter'
import { ThreeCharacter } from './ThreeCharacter'
import type { CharacterRendererProps } from './types'

/** El proceso principal sirve aquí el .riv del usuario (204/404 si no existe). */
const RIV_URL = '/__character/drakter.riv'

/**
 * El avatar elegido (preferencia `avatarId`). Con un avatar 3D se usa ese y, sin WebGL2 o si falla,
 * el SVG. Con «ninguno» (o uno aún no portado), el personaje clásico: el .riv del usuario si existe y,
 * si no, el SVG. Cambiar de avatar monta uno nuevo y libera el anterior.
 */
export function AdaptiveCharacter(props: CharacterRendererProps) {
  const avatar = useActiveAvatar()
  return avatar ? <Avatar3DCharacter key={avatar.meta.id} {...props} avatar={avatar} /> : <ClassicCharacter {...props} />
}

/** Avatar 3D con el SVG debajo hasta que se ve (nunca deja el hueco vacío) y como respaldo si falla. */
function Avatar3DCharacter({ avatar, ...props }: CharacterRendererProps & { readonly avatar: AvatarEntry }) {
  const [failed, setFailed] = useState(false)
  const [shown, setShown] = useState(false)
  const onFail = useCallback(() => setFailed(true), [])
  const onReady = useCallback(() => setShown(true), [])
  // Hijos en posiciones fijas: el SVG no se vuelve a montar mientras carga el 3D.
  return (
    <div className="relative size-full">
      {failed || !shown ? (
        <div className="absolute inset-0">
          <SvgCharacter {...props} />
        </div>
      ) : null}
      {failed ? null : <ThreeCharacter {...props} avatar={avatar} onReady={onReady} onFail={onFail} />}
    </div>
  )
}

type ClassicSource = { kind: 'checking' } | { kind: 'rive'; buffer: ArrayBuffer } | { kind: 'svg' }

/** Personaje clásico: el .riv del usuario si existe y carga; si no, el SVG (dibujado ya mientras se comprueba). */
function ClassicCharacter(props: CharacterRendererProps) {
  const [source, setSource] = useState<ClassicSource>({ kind: 'checking' })

  useEffect(() => {
    let alive = true
    fetch(RIV_URL, { cache: 'no-store' })
      .then((response) => {
        // 204 (o 404) = el usuario no tiene .riv: es lo normal y no se avisa.
        if (response.status === 204) return null
        // En desarrollo el servidor de Vite responde a cualquier ruta con index.html.
        if (response.headers.get('Content-Type')?.startsWith('text/html')) return null
        if (response.ok) return response.arrayBuffer()
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

  const riveFailed = useCallback(() => {
    warnCharacter('el .riv no cargó o no tiene la state machine «Drakter»; se usa el SVG')
    setSource({ kind: 'svg' })
  }, [])

  if (source.kind === 'rive') return <RiveCharacter {...props} buffer={source.buffer} onFail={riveFailed} />
  return <SvgCharacter {...props} />
}
