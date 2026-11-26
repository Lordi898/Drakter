import { JARVIS_LAYOUTS } from '@/app/jarvisLayouts'
import { listAvatars, NO_AVATAR } from '@/character/avatars/registry'
import { requestAppearance } from '@/stores/appearance'
import { jarvisAvailable, requestUiMode } from '@/stores/uiMode'

/** Acción de la paleta Ctrl+K (no es un resultado de búsqueda): abrir Jarvis o cambiar la apariencia. */
export interface PaletteAction {
  readonly id: string
  readonly label: string
  readonly kind: 'mode' | 'layout' | 'avatar'
  readonly hint?: string
  readonly run: () => void
}

const MAX_ACTIONS = 6

const fold = (text: string): string =>
  text.trim().toLowerCase().normalize('NFD').replace(/\p{M}/gu, '').replace(/\s+/g, ' ')

/** Lo escrito es el principio de alguna de estas palabras, o las contiene. */
function hits(q: string, words: readonly string[]): boolean {
  return words.some((word) => {
    const w = fold(word)
    return w.startsWith(q) || q.includes(w)
  })
}

/** Lo escrito es el principio del sustantivo («ava», «interf»): se listan todas las opciones de ese tipo. */
const startsNoun = (q: string, noun: string): boolean => noun.startsWith(q)

/**
 * Acciones que encajan con lo escrito (3 letras o más): «modo jarvis», «interfaz visor», «avatar orbe»,
 * «dragón»… Usan las mismas puertas que el resto de vías (`requestUiMode`, `requestAppearance`).
 */
export function paletteActions(query: string): readonly PaletteAction[] {
  const q = fold(query)
  if (q.length < 3 || !jarvisAvailable()) return []
  const out: PaletteAction[] = []

  if (hits(q, ['modo jarvis', 'jarvis'])) {
    out.push({ id: 'mode:jarvis', label: 'Abrir modo Jarvis', kind: 'mode', hint: 'Ctrl+Shift+J', run: () => requestUiMode('jarvis', 'button') })
  }
  for (const layout of JARVIS_LAYOUTS) {
    if (startsNoun(q, 'interfaz') || hits(q, [`interfaz ${layout.name}`, layout.name, layout.id])) {
      out.push({
        id: `layout:${layout.id}`,
        label: `Interfaz Jarvis: ${layout.name}`,
        kind: 'layout',
        run: () => requestAppearance({ layout: layout.id }, 'button')
      })
    }
  }
  for (const entry of listAvatars()) {
    const { id, name, voiceAliases } = entry.meta
    if (startsNoun(q, 'avatar') || hits(q, [`avatar ${name}`, name, ...voiceAliases])) {
      out.push({ id: `avatar:${id}`, label: `Avatar: ${name}`, kind: 'avatar', run: () => requestAppearance({ avatar: id }, 'button') })
    }
  }
  if (hits(q, ['avatar ninguno', 'sin avatar', 'personaje clasico'])) {
    out.push({
      id: `avatar:${NO_AVATAR}`,
      label: 'Avatar: ninguno (personaje clásico)',
      kind: 'avatar',
      run: () => requestAppearance({ avatar: NO_AVATAR }, 'button')
    })
  }
  return out.slice(0, MAX_ACTIONS)
}
