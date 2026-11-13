import { useSyncExternalStore } from 'react'
import { isSectionId, type SectionId } from './sections'

// La sección actual vive en el hash: funciona con file:// y sobrevive a recargas.
const DEFAULT_SECTION: SectionId = 'today'

function readSection(): SectionId {
  const hash = window.location.hash.replace(/^#\/?/, '')
  return isSectionId(hash) ? hash : DEFAULT_SECTION
}

function subscribe(listener: () => void): () => void {
  window.addEventListener('hashchange', listener)
  return () => window.removeEventListener('hashchange', listener)
}

export function useCurrentSection(): SectionId {
  return useSyncExternalStore(subscribe, readSection)
}

export function navigateTo(section: SectionId): void {
  window.location.hash = `/${section}`
}
