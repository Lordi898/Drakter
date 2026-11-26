// Visemas aproximados del castellano y la forma de boca de cada uno.

export type Viseme = 'A' | 'E' | 'I' | 'O' | 'U' | 'M' | 'F' | 'C' | '_';
/** Forma de la boca de láminas por visema: apertura, anchura, redondez, sonrisa. */
export const MOUTH: Record<Viseme, [number, number, number, number]> = {
  A: [1, 0.92, 0, 0.05], E: [0.55, 1.05, 0, 0.15], I: [0.34, 1.1, 0, 0.3], O: [0.8, 0.6, 0.75, 0],
  U: [0.45, 0.42, 1, -0.05], M: [0, 0.85, 0, 0], F: [0.14, 0.95, 0, 0.05], C: [0.3, 0.88, 0.1, 0.05], _: [0, 0.9, 0, 0],
};
