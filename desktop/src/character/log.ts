/** Aviso del personaje: el proceso principal lo recoge de la consola y lo deja en el log (window.ts). */
export function warnCharacter(message: string, detail?: unknown): void {
  const text = detail === undefined ? message : `${message}: ${String(detail)}`
  console.warn(`[drakter:personaje] ${text}`)
}
