/**
 * Interfaz Jarvis «Visor» (concepto C): el usuario en el centro de un cilindro; cada sección es un rumbo
 * y navegar es girar la cabeza. Capa propia del Stage (`visor-world`) + paneles DOM curvos (CSS3D) + cristal.
 * Plan y estado del port: ~/.local/share/drakter/plan/visor-port.md
 */
import { useEffect, useRef, useState } from 'react'
import type { SectionId } from '@/navigation/sections'
import type { JarvisLayoutProps } from '../types'
import { Glass } from './Glass'
import { WorldContext } from './Panel'
import { Nucleo } from './sectors/Nucleo'
import { SectorStub } from './sectors/SectorStub'
import { createVisorWorld, type VisorWorld } from './stage/world'
import './visor.css'

/** Sector (0-6) de cada sección; `settings` no tiene sector (queda en el Núcleo). */
const SECTOR_OF: Partial<Record<SectionId, number>> = { home: 0, today: 1, tasks: 2, projects: 2, habits: 3, calendar: 4, subjects: 4, relationships: 5, storage: 6 }
/** Sección que se publica al girar a cada sector. */
export const SECTION_OF: readonly SectionId[] = ['home', 'today', 'tasks', 'habits', 'calendar', 'relationships', 'storage']
export const SECTOR_NAMES = ['Núcleo', 'Hoy', 'Tareas y proyectos', 'Hábitos', 'Calendario y asignaturas', 'Relaciones', 'Almacén'] as const

const isField = (t: EventTarget | null): boolean => t instanceof HTMLElement && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))

export default function VisorLayout({ stage, avatar, reducedMotion, section, navigate, onReady, exit }: JarvisLayoutProps) {
  const [world, setWorld] = useState<VisorWorld | null>(null)
  const hostRef = useRef<HTMLDivElement>(null)
  const readyRef = useRef(false)
  const ready = (): void => { if (!readyRef.current) { readyRef.current = true; onReady() } }

  // Capa del Stage: se añade al montar y se quita (y libera) al desmontar.
  useEffect(() => {
    if (!stage) return
    const w = createVisorWorld()
    stage.add(w)
    hostRef.current?.appendChild(w.cssRoot)
    avatar.setViewport((frame) => w.avatarViewport(frame))
    setWorld(w)
    let alive = true
    void stage.ready.then(() => w.onFirstFrame).then(() => { if (alive) { w.setRevealed(true); ready() } })
    return () => { alive = false; avatar.setViewport(null); stage.remove(w.id); setWorld(null) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage])
  // Sin lienzo: el HUD en DOM ya se ve.
  useEffect(() => { if (!stage) ready() })

  // Sección común → rumbo.
  useEffect(() => { world?.goSector(SECTOR_OF[section] ?? 0) }, [world, section])
  const go = (i: number): void => { const s = ((i % 7) + 7) % 7; world?.goSector(s); navigate(SECTION_OF[s]!) }

  // Teclas del visor (no con el foco en un campo: el chat y la búsqueda las necesitan).
  useEffect(() => {
    const onKey = (e: KeyboardEvent): void => {
      if (e.ctrlKey || e.metaKey || e.altKey || isField(e.target)) return
      const cur = SECTOR_OF[section] ?? 0
      if (e.key >= '0' && e.key <= '6') go(Number(e.key))
      else if (e.key === 'ArrowRight') go(cur + 1)
      else if (e.key === 'ArrowLeft') go(cur - 1)
      else if (e.key === 'Escape') go(0)
      else return
      e.preventDefault()
    }
    addEventListener('keydown', onKey)
    return () => removeEventListener('keydown', onKey)
  })

  return (
    <WorldContext.Provider value={world}>
      <div className={`jv-visor ${stage ? '' : 'flat'}`} data-reduced={reducedMotion ? 'true' : 'false'}>
        <div className="jv-visor-host" ref={hostRef} />
        <div className="jv-visor-grid">
          <Nucleo avatar={avatar} />
          {SECTOR_NAMES.slice(1).map((name, i) => <SectorStub key={name} sector={i + 1} name={name} />)}
        </div>
        <Glass world={world} sector={SECTOR_OF[section] ?? 0} names={SECTOR_NAMES} go={go} exit={exit} />
      </div>
    </WorldContext.Provider>
  )
}
