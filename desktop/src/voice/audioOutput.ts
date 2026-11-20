/** Salida de audio elegida: la voz y el tono de prueba van al dispositivo del usuario, no al predeterminado. */

/** `AudioContext.setSinkId` (Chromium 110+) aún no está en la librería DOM de TypeScript. */
interface SinkTarget {
  setSinkId(sinkId: string): Promise<void>
}

/** `''` si el dispositivo elegido ya no existe (se vuelve al predeterminado; si reaparece, se recupera). */
async function resolveSink(deviceId: string): Promise<string> {
  if (deviceId === '') return ''
  const devices = await navigator.mediaDevices.enumerateDevices()
  return devices.some((d) => d.kind === 'audiooutput' && d.deviceId === deviceId) ? deviceId : ''
}

async function setSink(target: SinkTarget, deviceId: string): Promise<void> {
  await target.setSinkId(await resolveSink(deviceId))
}

/** Aplica la salida al `<audio>`; un fallo deja la salida anterior y no interrumpe la voz. */
export async function applySink(audio: HTMLMediaElement, deviceId: string): Promise<void> {
  try {
    await setSink(audio, deviceId)
  } catch {
    // setSinkId puede rechazar un dispositivo que se está yendo; el siguiente devicechange reintenta.
  }
}

/** Tono corto local (WebAudio, sin red) por la salida indicada. */
export async function playTestTone(deviceId: string): Promise<void> {
  const ctx = new AudioContext() as AudioContext & SinkTarget
  try {
    await setSink(ctx, deviceId)
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    const t = ctx.currentTime
    osc.frequency.value = 660
    gain.gain.setValueAtTime(0, t)
    gain.gain.linearRampToValueAtTime(0.2, t + 0.03)
    gain.gain.linearRampToValueAtTime(0, t + 0.6)
    osc.connect(gain).connect(ctx.destination)
    osc.start(t)
    osc.stop(t + 0.65)
    await new Promise<void>((resolve) => {
      osc.onended = () => resolve()
    })
  } finally {
    void ctx.close()
  }
}
