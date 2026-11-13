import {
  Blocks,
  BookOpen,
  CalendarDays,
  Flame,
  FolderKanban,
  Network,
  Settings,
  Smile,
  SquareCheckBig,
  Sun,
  type LucideIcon
} from 'lucide-react'

/**
 * Las secciones son predefinidas (MASTER_PLAN §5.2): el orden es el de §5.3,
 * precedido por Hoy, que es la pantalla inicial.
 */
export const SECTION_IDS = [
  'today',
  'home',
  'habits',
  'tasks',
  'projects',
  'storage',
  'calendar',
  'subjects',
  'relationships',
  'settings'
] as const

export type SectionId = (typeof SECTION_IDS)[number]

export interface Section {
  readonly id: SectionId
  readonly label: string
  readonly icon: LucideIcon
  /** Dígito de Ctrl+<dígito>. */
  readonly shortcut: string
}

export const SECTIONS: readonly Section[] = [
  { id: 'today', label: 'Hoy', icon: Sun, shortcut: '0' },
  { id: 'home', label: 'Drakter', icon: Smile, shortcut: '1' },
  { id: 'habits', label: 'Hábitos', icon: Flame, shortcut: '2' },
  { id: 'tasks', label: 'Tareas', icon: SquareCheckBig, shortcut: '3' },
  { id: 'projects', label: 'Proyectos', icon: FolderKanban, shortcut: '4' },
  { id: 'storage', label: 'Almacén', icon: Blocks, shortcut: '5' },
  { id: 'calendar', label: 'Calendario', icon: CalendarDays, shortcut: '6' },
  { id: 'subjects', label: 'Asignaturas', icon: BookOpen, shortcut: '7' },
  { id: 'relationships', label: 'Relaciones', icon: Network, shortcut: '8' },
  { id: 'settings', label: 'Configuración', icon: Settings, shortcut: '9' }
]

export function isSectionId(value: string): value is SectionId {
  return (SECTION_IDS as readonly string[]).includes(value)
}

export function getSection(id: SectionId): Section {
  const section = SECTIONS.find((candidate) => candidate.id === id)
  if (!section) throw new Error(`Sección desconocida: ${id}`)
  return section
}
