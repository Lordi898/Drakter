import { useEffect, useRef } from 'react'
import { startCharacterReceiver, type CharacterSink } from './receiver'
import { createCharacter, type Rig } from './rig'
import type { CharacterRendererProps } from './types'

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
      // Reservado para voz: el rig articula la boca solo con su generador interno en 'speaking'.
      setMouth: () => {}
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

  return <div ref={host} className="size-full" />
}
