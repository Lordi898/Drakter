import { getSection } from '@/navigation/sections'
import type { SectionId } from '@/navigation/sections'
import { useCurrentSection } from '@/navigation/route'

const SELECTION_HELP: Record<SectionId, string> = {
  today:
    'Aquí ves lo que vence, la agenda y los hábitos del día. Cada elemento te lleva a su sección.',
  home:
    'Aquí verás la actividad reciente y el detalle de lo que Drakter esté haciendo, cuando esté conectado.',
  habits:
    'Al elegir un hábito verás su frecuencia, su historial cumplido y a qué proyectos u objetivos se relaciona.',
  tasks:
    'Al elegir una tarea verás sus subtareas, sus fechas y a qué proyecto o asignatura está vinculada.',
  projects:
    'Al elegir un proyecto verás sus objetivos, fechas, tareas y recursos asociados, y su progreso.',
  storage:
    'Al elegir un recurso verás su tipo, su ruta, sus etiquetas y con qué otros elementos está relacionado.',
  calendar:
    'Al elegir un evento o un bloque de tiempo verás su horario, su recordatorio y las tareas o asignaturas asociadas.',
  subjects:
    'Al elegir una asignatura verás su horario de clases, el aula, sus apuntes y las tareas relacionadas.',
  relationships:
    'Al elegir un elemento verás con qué otros está conectado y de qué tipo es cada conexión.',
  settings: 'Aquí cambias tus preferencias y se guardan en este equipo.'
}

const SHORTCUTS: readonly { keys: readonly string[]; label: string }[] = [
  { keys: ['Ctrl', '0–9'], label: 'Cambiar de sección' },
  { keys: ['Ctrl', 'K'], label: 'Buscar' },
  { keys: ['Ctrl', '\\'], label: 'Ocultar este panel' }
]

function Kbd({ children }: { children: string }) {
  return (
    <kbd className="rounded-tab border border-chassis-line bg-chassis-raised px-1.5 py-0.5 text-xs leading-none text-chassis-foreground">
      {children}
    </kbd>
  )
}

export function ContextPanel() {
  const section = getSection(useCurrentSection())

  return (
    <aside
      aria-label="Información contextual"
      className="flex h-full flex-col gap-6 overflow-y-auto p-5 text-chassis-foreground"
    >
      <header className="flex flex-col gap-1">
        <h2 className="text-base font-semibold">{section.label}</h2>
        <p className="text-sm text-chassis-muted">Nada seleccionado</p>
      </header>

      <p className="text-sm leading-relaxed text-chassis-muted">{SELECTION_HELP[section.id]}</p>

      <section aria-labelledby="context-shortcuts" className="mt-auto border-t border-chassis-line pt-4">
        <h3 id="context-shortcuts" className="mb-3 text-sm font-medium">
          Atajos
        </h3>
        <ul className="flex flex-col gap-2 text-sm">
          {SHORTCUTS.map((shortcut) => (
            <li key={shortcut.label} className="flex items-center justify-between gap-3">
              <span className="text-chassis-muted">{shortcut.label}</span>
              <span className="flex items-center gap-1">
                {shortcut.keys.map((key) => (
                  <Kbd key={key}>{key}</Kbd>
                ))}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </aside>
  )
}
