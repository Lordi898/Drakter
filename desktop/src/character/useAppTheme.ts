import { useSyncExternalStore } from 'react'
import type { AvatarTheme } from './avatars/types'

/**
 * Tema que se ve de verdad: la clase `dark` de <html> (la pone `useDocumentPreferences` según la
 * preferencia o el sistema, y Jarvis la fuerza). Así el avatar sigue exactamente lo que pinta la app.
 */
function subscribe(onChange: () => void): () => void {
  const observer = new MutationObserver(onChange)
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
  return () => observer.disconnect()
}

export function getAppTheme(): AvatarTheme {
  return document.documentElement.classList.contains('dark') ? 'dark' : 'light'
}

export function useAppTheme(): AvatarTheme {
  return useSyncExternalStore(subscribe, getAppTheme)
}
