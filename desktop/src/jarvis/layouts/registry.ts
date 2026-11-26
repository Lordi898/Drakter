/**
 * Registro de interfaces Jarvis: una por carpeta (`./<id>/index.tsx`, export default `JarvisLayout`).
 * Carga diferida por interfaz: solo se descarga la elegida. Una carpeta que aún no existe no rompe
 * la build: `JarvisShell` muestra su fondo de respaldo. Los nombres están en `app/jarvisLayouts.ts`.
 */
import { DEFAULT_JARVIS_LAYOUT, JARVIS_LAYOUT_CHOICES } from '@/stores/preferences'
import type { JarvisLayout, JarvisLayoutId } from './types'

type LayoutModule = { readonly default: JarvisLayout }

const modules = import.meta.glob<LayoutModule>('./*/index.tsx')

/** Cargador de la interfaz, o `null` si esa interfaz no está en esta build. */
export function layoutLoader(id: JarvisLayoutId): (() => Promise<LayoutModule>) | null {
  return modules[`./${id}/index.tsx`] ?? null
}

/** Interfaces presentes en esta build, en el orden del catálogo. */
export function availableLayouts(): readonly JarvisLayoutId[] {
  return JARVIS_LAYOUT_CHOICES.filter((id) => layoutLoader(id) !== null)
}

/** La pedida si está; si no, la de por defecto; si tampoco, la primera disponible; `null` si no hay ninguna. */
export function resolveLayout(id: JarvisLayoutId): JarvisLayoutId | null {
  if (layoutLoader(id)) return id
  if (layoutLoader(DEFAULT_JARVIS_LAYOUT)) return DEFAULT_JARVIS_LAYOUT
  return availableLayouts()[0] ?? null
}
