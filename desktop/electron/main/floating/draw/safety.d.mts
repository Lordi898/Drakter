// Drakter: declaraciones de tipos para `safety.mjs` (copia literal de Roamies 8f0adaa, AGPL-3.0). Solo lo que usa main.
export const SAFE: 'safe'
export const ASK: 'ask'
export const BLOCK: 'block'
export interface Verdict {
  readonly level: 'safe' | 'ask' | 'block'
  readonly reason: string
}
export function checkUrl(url: unknown): Verdict
