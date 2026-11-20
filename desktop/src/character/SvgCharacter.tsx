import { useCallback, useEffect, useRef } from 'react'
import { startCharacterReceiver, type CharacterSink } from './receiver'
import { createCharacter, type Rig } from './rig'
import type { CharacterRendererProps } from './types'
import { useMouthLevel } from './useMouthLevel'

/**
 * Renderer SVG del personaje (sustituto del .riv). El estado llega por prop;
 * las expresiones llegan por el receptor de eventos.
 */
export function SvgCharacter({ state }: CharacterRendererProps) {
  const host = useRef<HTMLDivElement>(null)
  const rig = useRef<Rig | null>(null)
  const initial = useRef(state)

  useEffect(() => {
    const el = host.current
    if (!el) return
    const created = createCharacter(el, { state: initial.current })
    rig.current = created
    const sink: CharacterSink = {
      setState: (next) => {
        created.setState(next)
      },
      // El rig solo se mueve por estados: no tiene parametros de expresion propios.
      // Las expresiones validadas se aceptan y se ignoran hasta que el .riv las exponga.
      setExpression: () => {},
      // Nivel real del audio; sin él (o sin audio) el rig usa su generador interno.
      setMouth: (level) => {
        created.setMouthLevel(level)
      }
    }
    const stop = startCharacterReceiver(sink)
    return () => {
      stop()
      created.destroy()
      rig.current = null
    }
  }, [])

  useEffect(() => {
    rig.current?.setState(state)
  }, [state])

  const applyMouth = useCallback((level: number | null) => {
    rig.current?.setMouthLevel(level)
  }, [])
  useMouthLevel(state, applyMouth)

  return <div ref={host} className="size-full" />
}
