import { useEffect, useState } from 'react'

export interface MicDevices {
  readonly inputs: readonly { readonly id: string; readonly label: string }[]
  readonly outputs: readonly { readonly id: string; readonly label: string }[]
  /** La entrada y la salida (`''` = predeterminada del sistema) son de dispositivos distintos. */
  readonly split: (inputId: string, outputId: string) => boolean
}

const EMPTY: MicDevices = { inputs: [], outputs: [], split: () => false }

async function read(): Promise<MicDevices> {
  const [devices, defaults] = await Promise.all([
    navigator.mediaDevices.enumerateDevices(),
    window.api.voice.defaultDevices().catch(() => ({ input: null, output: null }))
  ])
  const real = (kind: MediaDeviceKind) =>
    devices.filter((d) => d.kind === kind && d.deviceId !== 'default' && d.deviceId !== 'communications')
  const inputs = real('audioinput').map((d, i) => ({ id: d.deviceId, label: d.label || `Micrófono ${i + 1}` }))
  const outputs = real('audiooutput').map((d, i) => ({ id: d.deviceId, label: d.label || `Salida ${i + 1}` }))
  // Chromium solo da «Default» como etiqueta del predeterminado: el nombre real lo da PipeWire.
  const group = (kind: MediaDeviceKind, id: string, defaultLabel: string | null): string | undefined =>
    real(kind).find((d) => (id === '' ? d.label === defaultLabel : d.deviceId === id))?.groupId
  return {
    inputs,
    outputs,
    split: (inputId, outputId) => {
      const inGroup = group('audioinput', inputId, defaults.input)
      const outGroup = group('audiooutput', outputId, defaults.output)
      return inGroup !== undefined && outGroup !== undefined && inGroup !== outGroup
    }
  }
}

/** Entradas y salidas de audio disponibles, al día con `devicechange`. */
export function useMicDevices(): MicDevices {
  const [state, setState] = useState<MicDevices>(EMPTY)
  useEffect(() => {
    let cancelled = false
    const refresh = (): void => {
      read()
        .then((next) => {
          if (!cancelled) setState(next)
        })
        .catch(() => undefined)
    }
    refresh()
    navigator.mediaDevices.addEventListener('devicechange', refresh)
    return () => {
      cancelled = true
      navigator.mediaDevices.removeEventListener('devicechange', refresh)
    }
  }, [])
  return state
}
