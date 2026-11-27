// Drakter: declaraciones de tipos para `draw.mjs` (copia literal de Roamies 8f0adaa, AGPL-3.0). Solo lo que usa main.
import type { ZodType } from 'zod'

export interface DrawTarget {
  text?: string
  every?: boolean
  within?: { x: number; y: number; w: number; h: number }
  id?: number
  x?: number
  y?: number
  w?: number
  h?: number
}

export interface DrawMark {
  kind: string
  at?: DrawTarget
  to?: DrawTarget
  tie?: DrawTarget
  points?: [number, number][]
  [key: string]: unknown
}

export interface DrawBeat {
  say: string
  marks: DrawMark[]
  wait?: 'click' | 'hover'
}

export interface DrawEdit {
  do: 'recolor' | 'move' | 'erase' | 'clear'
  part?: string
  tone?: string
  dx?: number
  dy?: number
}

export interface DrawArgsOut {
  target?: string
  beats?: DrawBeat[]
  edit?: DrawEdit[]
  deep?: boolean
  keep?: boolean
}

export const LIMITS: { readonly beats: number; readonly marks: number; readonly points: number; readonly cardsShown: number } & Readonly<
  Record<string, number>
>
export const TONES: readonly string[]
export const SCREEN: readonly string[]
export const ACTIONS: readonly string[]
export const CARDS: readonly string[]
export const KINDS: readonly string[]
export const DrawArgs: ZodType<DrawArgsOut>
export function tidyDraw(args: unknown): unknown
export function checkDraw(args: DrawArgsOut): string[]
