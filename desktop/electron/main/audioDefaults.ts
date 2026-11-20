import { execFile } from 'node:child_process'
import type { DefaultAudioDevices } from '../shared/bridge'

/** `node.description` del nodo predeterminado según PipeWire (coincide con la etiqueta de Chromium). */
function describe(target: string): Promise<string | null> {
  return new Promise((resolve) => {
    execFile('wpctl', ['inspect', target], { timeout: 2000 }, (error, stdout) => {
      const match = error ? null : /node\.description = "([^"]+)"/.exec(stdout)
      resolve(match?.[1] ?? null)
    })
  })
}

/** Linux/PipeWire; sin `wpctl` devuelve nulos y la interfaz no avisa. */
export async function defaultAudioDevices(): Promise<DefaultAudioDevices> {
  const [input, output] = await Promise.all([describe('@DEFAULT_AUDIO_SOURCE@'), describe('@DEFAULT_AUDIO_SINK@')])
  return { input, output }
}
