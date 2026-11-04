import type { CSSProperties } from 'react'
import { DrakterStatus } from '@/components/status/DrakterStatus'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import { navigateTo } from '@/navigation/route'
import { SECTIONS, type Section, type SectionId } from '@/navigation/sections'

/*
 * La junta entre la pestaña activa y la hoja.
 *
 * La pestaña desborda 1px sobre la hoja: con escalado fraccionario, dos cajas que solo
 * se tocan pueden dejar ver una línea del chasis por el antialias del borde común.
 *
 * Cada esquina cóncava es un cuadrado de lado r (radio de pestaña) apoyado en la hoja y en
 * la pestaña, pintado con el color de la hoja salvo un cuarto de círculo de radio r centrado
 * en su vértice libre. El círculo es tangente a ambos bordes, así que la curva arranca y
 * termina sin quiebro. El cuadrado crece 1px hacia la pestaña y hacia la hoja para repetir
 * el mismo solape; el centro no se mueve porque se ancla en el vértice libre.
 *
 * El gradiente sube en 1px alrededor de r para que la curva salga con antialias.
 */
const FILLET_RADIUS = 'var(--radius-tab)'
const FILLET_SIZE = `calc(${FILLET_RADIUS} + 1px)`

function filletGradient(center: string): string {
  return `radial-gradient(circle at ${center}, transparent calc(${FILLET_RADIUS} - 0.5px), var(--background) calc(${FILLET_RADIUS} + 0.5px))`
}

const FILLET_ABOVE: CSSProperties = {
  width: FILLET_SIZE,
  height: FILLET_SIZE,
  right: 0,
  bottom: 'calc(100% - 1px)',
  background: filletGradient('0 0')
}

const FILLET_BELOW: CSSProperties = {
  width: FILLET_SIZE,
  height: FILLET_SIZE,
  right: 0,
  top: 'calc(100% - 1px)',
  background: filletGradient('0 100%')
}

function Fillet({ style }: { style: CSSProperties }) {
  return <span aria-hidden="true" className="pointer-events-none absolute" style={style} />
}

function SectionTab({ section, active }: { section: Section; active: boolean }) {
  const Icon = section.icon

  return (
    <li>
      <Tooltip>
        <TooltipTrigger asChild>
          <a
            href={`#/${section.id}`}
            draggable={false}
            aria-current={active ? 'page' : undefined}
            aria-keyshortcuts={`Control+${section.shortcut}`}
            onClick={(event) => {
              event.preventDefault()
              navigateTo(section.id)
            }}
            className={cn(
              'relative flex h-10 items-center gap-2.5 pl-3 text-sm',
              // Sin transiciones de color: la pestaña y su junta aparecen y desaparecen a la vez.
              active
                ? '-mr-px rounded-l-tab bg-background font-medium text-foreground'
                : 'mr-2.5 rounded-tab text-chassis-muted hover:bg-chassis-raised hover:text-chassis-foreground'
            )}
          >
            <Icon aria-hidden="true" className="size-4 shrink-0" />
            {section.label}
            {active && (
              <>
                <Fillet style={FILLET_ABOVE} />
                <Fillet style={FILLET_BELOW} />
              </>
            )}
          </a>
        </TooltipTrigger>
        <TooltipContent side="right" sideOffset={8}>
          Ctrl+{section.shortcut}
        </TooltipContent>
      </Tooltip>
    </li>
  )
}

export function Sidebar({ current }: { current: SectionId }) {
  const sections = SECTIONS.filter((section) => section.id !== 'settings')
  const settings = SECTIONS.filter((section) => section.id === 'settings')

  return (
    // Por encima de la hoja: aquí vive el píxel de solape de la pestaña activa.
    <div className="relative z-10 flex min-h-0 flex-col pl-2.5 text-chassis-foreground select-none">
      <p className="type-display px-3 pt-5 pb-4 text-2xl">Drakter</p>

      {/* gap-1 mantiene las pestañas vecinas fuera de las esquinas cóncavas: acaban 10px antes de la hoja. */}
      <nav aria-label="Secciones" className="flex min-h-0 flex-1 flex-col justify-between">
        <ul className="flex flex-col gap-1">
          {sections.map((section) => (
            <SectionTab key={section.id} section={section} active={section.id === current} />
          ))}
        </ul>
        <ul>
          {settings.map((section) => (
            <SectionTab key={section.id} section={section} active={section.id === current} />
          ))}
        </ul>
      </nav>

      {/* Altura mínima: la esquina cóncava inferior de Configuración debe acabar antes de que se curve la hoja. */}
      <div className="min-h-14 shrink-0 pr-3">
        <DrakterStatus />
      </div>
    </div>
  )
}
