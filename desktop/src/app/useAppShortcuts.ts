import { useEffect } from 'react'
import { getPreferences, updatePreferences } from '@/stores/preferences'

export function toggleContextPanel(): void {
  updatePreferences({ contextPanelOpen: !getPreferences().contextPanelOpen })
}

/**
 * Atajos propios del shell de Drakter: Ctrl+\ alterna el panel contextual. Los comunes a los dos
 * modos (secciones y modo Jarvis) están en `useGlobalShortcuts`.
 * `code` cubre el teclado español, donde esa tecla física es la ç y la barra exige AltGr.
 */
export function useAppShortcuts(panelAvailable: boolean): void {
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent): void {
      if (!event.ctrlKey || event.metaKey || event.repeat) return
      if (event.key !== '\\' && event.code !== 'Backslash') return
      event.preventDefault()
      if (panelAvailable) toggleContextPanel()
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [panelAvailable])
}
