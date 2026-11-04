/** Selección nativa de carpeta: método del puente aún por añadir; acceso defensivo. */
type PickBridge = { pickDirectory?: () => Promise<string | null> }

function pick(): (() => Promise<string | null>) | null {
  const fn = ((window as { drakter?: unknown }).drakter as PickBridge | undefined)?.pickDirectory
  return typeof fn === 'function' ? fn : null
}

export const canPickDirectory = (): boolean => pick() !== null

export async function pickDirectory(): Promise<string | null> {
  const fn = pick()
  return fn ? fn() : null
}
