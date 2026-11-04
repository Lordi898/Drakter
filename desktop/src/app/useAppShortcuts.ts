import { useEffect } from 'react'
import { navigateTo } from '@/navigation/route'
import { SECTIONS } from '@/navigation/sections'
import { getPreferences, updatePreferences } from '@/stores/preferences'

export function toggleContextPanel(): void {
  updatePreferences({ contextPanelOpen: !getPreferences().contextPanelOpen })
}

/**
 * Ctrl+1 a Ctrl+9 cambian de sección y Ctrl+\ alterna el panel contextual.
 * `code` cubre el teclado español, donde esa tecla física es la ç y la barra exige AltGr.
 */
export function useAppShortcuts(panelAvailable: boolean): void {
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent): void {
      if (!event.ctrlKey || event.metaKey || event.repeat) return

      if (event.key === '\\' || event.code === 'Backslash') {
        event.preventDefault()
        if (panelAvailable) toggleContextPanel()
        return
      }

      if (event.altKey || event.shiftKey) return
      const section = SECTIONS.find((candidate) => candidate.shortcut === event.key)
      if (!section) return
      event.preventDefault()
      navigateTo(section.id)
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [panelAvailable])
}
