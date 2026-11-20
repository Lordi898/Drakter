import { useEffect, useState } from 'react'

export interface MicDevices {
  readonly inputs: readonly { readonly id: string; readonly label: string }[]
  /** La entrada (`''` = predeterminada) y la salida predeterminada son de dispositivos distintos. */
  readonly split: (id: string) => boolean
}

const EMPTY: MicDevices = { inputs: [], split: () => false }

async function read(): Promise<MicDevices> {
  const [devices, defaults] = await Promise.all([
    navigator.mediaDevices.enumerateDevices(),
    window.api.voice.defaultDevices().catch(() => ({ input: null, output: null }))
  ])
  const real = (kind: MediaDeviceKind) =>
    devices.filter((d) => d.kind === kind && d.deviceId !== 'default' && d.deviceId !== 'communications')
  const inputs = real('audioinput').map((d, i) => ({ id: d.deviceId, label: d.label || `Micrófono ${i + 1}` }))
  // Chromium solo da «Default» como etiqueta del predeterminado: el nombre real lo da PipeWire.
  const outGroup = real('audiooutput').find((d) => d.label === defaults.output)?.groupId
  const inGroup = (id: string): string | undefined =>
    real('audioinput').find((d) => (id === '' ? d.label === defaults.input : d.deviceId === id))?.groupId
  return {
    inputs,
    split: (id) => {
      const group = inGroup(id)
      return outGroup !== undefined && group !== undefined && group !== outGroup
    }
  }
}

/** Entradas de audio disponibles, al día con `devicechange`. */
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
