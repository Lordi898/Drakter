import { useLayoutEffect } from 'react'
import { usePreferences } from '@/stores/preferences'

const PREFERS_DARK = '(prefers-color-scheme: dark)'

function applyDarkTheme(dark: boolean): void {
  const root = document.documentElement
  root.classList.toggle('dark', dark)
  // Las barras de desplazamiento nativas siguen a color-scheme, no a la clase.
  root.style.colorScheme = dark ? 'dark' : 'light'
}

/** Refleja tema y movimiento reducido en <html>, antes de pintar para evitar un destello. */
export function useDocumentPreferences(): void {
  const { theme, reduceMotion } = usePreferences()

  useLayoutEffect(() => {
    if (theme !== 'system') {
      applyDarkTheme(theme === 'dark')
      return
    }
    const media = window.matchMedia(PREFERS_DARK)
    const onChange = (): void => applyDarkTheme(media.matches)
    onChange()
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [theme])

  useLayoutEffect(() => {
    document.documentElement.dataset.reduceMotion = String(reduceMotion)
  }, [reduceMotion])
}
