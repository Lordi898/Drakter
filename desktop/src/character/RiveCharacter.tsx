import { Rive, RuntimeLoader, type StateMachineInput } from '@rive-app/canvas'
import riveWasmUrl from '@rive-app/canvas/rive.wasm?url'
import { useCallback, useEffect, useRef } from 'react'
import { warnCharacter } from './log'
import { CHARACTER_STATES, type CharacterRendererProps } from './types'
import { useMouthLevel } from './useMouthLevel'

/** Contrato con el .riv (documentado en docs/usage/personaje.md). */
export const RIVE_STATE_MACHINE = 'Drakter'
export const RIVE_INPUT_STATE = 'state' // Number 0..8, orden de CHARACTER_STATES
export const RIVE_INPUT_MOUTH = 'mouthOpen' // Number 0..1

RuntimeLoader.setWasmUrl(riveWasmUrl)

interface RiveCharacterProps extends CharacterRendererProps {
  /** Bytes del .riv ya descargados. */
  readonly buffer: ArrayBuffer
  /** El .riv no cargó o no sirve: el padre vuelve al SVG. */
  readonly onFail: () => void
}

function findInput(inputs: StateMachineInput[], name: string): StateMachineInput | null {
  return inputs.find((input) => input.name === name) ?? null
}

/** Renderer Rive: la prop `state` y el nivel de audio se vuelcan a inputs de la state machine. */
export function RiveCharacter({ state, buffer, onFail }: RiveCharacterProps) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const stateInput = useRef<StateMachineInput | null>(null)
  const mouthInput = useRef<StateMachineInput | null>(null)
  const latest = useRef(state)
  latest.current = state

  useEffect(() => {
    const el = canvas.current
    if (!el) return
    let alive = true
    let rive: Rive | null = null
    try {
      rive = new Rive({
        canvas: el,
        buffer,
        stateMachines: RIVE_STATE_MACHINE,
        autoplay: true,
        onLoad: () => {
          if (!alive || !rive) return
          rive.resizeDrawingSurfaceToCanvas()
          const inputs = rive.stateMachineInputs(RIVE_STATE_MACHINE)
          if (!inputs) return onFail() // sin la state machine documentada no hay nada que animar
          stateInput.current = findInput(inputs, RIVE_INPUT_STATE)
          mouthInput.current = findInput(inputs, RIVE_INPUT_MOUTH)
          if (stateInput.current) stateInput.current.value = CHARACTER_STATES.indexOf(latest.current)
        },
        onLoadError: (event) => {
          if (alive) {
            warnCharacter('Rive no pudo cargar el .riv', event?.data)
            onFail()
          }
        }
      })
    } catch (reason) {
      warnCharacter('Rive falló al arrancar (¿wasm bloqueado por la CSP?)', reason)
      onFail()
    }
    return () => {
      alive = false
      stateInput.current = null
      mouthInput.current = null
      rive?.cleanup()
    }
  }, [buffer, onFail])

  useEffect(() => {
    if (stateInput.current) stateInput.current.value = CHARACTER_STATES.indexOf(state)
  }, [state])

  const applyMouth = useCallback((level: number | null) => {
    if (mouthInput.current) mouthInput.current.value = level ?? 0
  }, [])
  useMouthLevel(state, applyMouth)

  return <canvas ref={canvas} width={360} height={360} className="size-full" />
}
