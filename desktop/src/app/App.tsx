import { useCurrentSection } from '@/navigation/route'
import { PAGES } from '@/navigation/pages'

// Stub: lo sustituye la pieza del shell.
export function App() {
  const Page = PAGES[useCurrentSection()]
  return <Page />
}
