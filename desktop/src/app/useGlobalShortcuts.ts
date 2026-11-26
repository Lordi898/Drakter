import { useEffect } from 'react'
import { navigateTo } from '@/navigation/route'
import { SECTIONS } from '@/navigation/sections'
import { requestUiMode } from '@/stores/uiMode'

/** Atajo del modo Jarvis, para `aria-keyshortcuts` y los textos de ayuda. */
export const UI_MODE_SHORTCUT = 'Control+Shift+J'
export const UI_MODE_SHORTCUT_LABEL = 'Ctrl+Shift+J'

/**
 * Atajos comunes a los dos modos: Ctrl+0…Ctrl+9 cambian de sección (la sección se comparte entre
 * Drakter y Jarvis) y Ctrl+Shift+J alterna el modo. `code` cubre cualquier distribución de teclado.
 * Los propios de Drakter (Ctrl+\, Ctrl+K) siguen en su shell.
 */
export function useGlobalShortcuts(): void {
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent): void {
      if (!event.ctrlKey || event.metaKey || event.altKey || event.repeat) return

      if (event.shiftKey) {
        if (event.code !== 'KeyJ') return
        event.preventDefault()
        requestUiMode('toggle', 'shortcut')
        return
      }

      const section = SECTIONS.find((candidate) => candidate.shortcut === event.key)
      if (!section) return
      event.preventDefault()
      navigateTo(section.id)
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])
}
