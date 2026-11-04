/**
 * Paleta corta de asignaturas. Tonos medios (luminancia 0,16-0,27) para que el
 * indicador de color mantenga >= 3:1 contra el fondo claro y el oscuro.
 * El texto nunca se pinta con ellos: siempre usa los tokens de primer plano.
 */
export interface PaletteColor {
  readonly hex: string
  readonly name: string
}

export const SUBJECT_PALETTE: readonly PaletteColor[] = [
  { hex: '#3f86d0', name: 'Azul' },
  { hex: '#2a9d7f', name: 'Verde' },
  { hex: '#c9780f', name: 'Ámbar' },
  { hex: '#d1566b', name: 'Rojo' },
  { hex: '#8b6fd6', name: 'Violeta' },
  { hex: '#1f9bb0', name: 'Turquesa' },
  { hex: '#b8683a', name: 'Ocre' },
  { hex: '#7488a0', name: 'Pizarra' }
]

export const FALLBACK_COLOR = '#7488a0'

export function colorOf(color: string | null): string {
  return color ?? FALLBACK_COLOR
}

export function colorName(color: string | null): string {
  return SUBJECT_PALETTE.find((c) => c.hex.toLowerCase() === color?.toLowerCase())?.name ?? 'Sin color'
}
