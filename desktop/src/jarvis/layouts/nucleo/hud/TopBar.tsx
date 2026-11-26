/**
 * Barra superior: marca, reloj, estado del agente, telemetría del Stage (de Visor) y nivel de calidad.
 * El reloj y la telemetría escriben en el DOM por ref (1 Hz), sin renders de React.
 */
import { useEffect, useRef } from 'react'
import type { CharacterState } from '@/character/types'
import { CHARACTER_STATE_LABELS } from '@/character/labels'
import { updatePreferences, usePreferences, type JarvisQuality } from '@/stores/preferences'
import type { Stage } from '../../../stage/types'

const QUALITIES: readonly [JarvisQuality, string][] = [['auto', 'Auto'], ['cine', 'Cine'], ['equilibrado', 'Equilibrado'], ['ahorro', 'Ahorro']]
const pad2 = (n: number): string => String(n).padStart(2, '0')
const fecha = new Intl.DateTimeFormat('es-ES', { weekday: 'long', day: 'numeric', month: 'long' })

export function TopBar({ state, stage, tz }: { readonly state: CharacterState; readonly stage: Stage | null; readonly tz: string }) {
  const clock = useRef<HTMLElement>(null)
  const date = useRef<HTMLSpanElement>(null)
  const tel = useRef<HTMLDivElement>(null)
  const { jarvisQuality } = usePreferences()

  useEffect(() => {
    const fmt = new Intl.DateTimeFormat('es-ES', { timeZone: tz, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
    const day = new Intl.DateTimeFormat('es-ES', { timeZone: tz, weekday: 'long', day: 'numeric', month: 'long' })
    const fps: number[] = []
    const tick = (): void => {
      const now = new Date()
      if (clock.current) { const t = fmt.format(now); if (clock.current.textContent !== t) clock.current.textContent = t }
      if (date.current) { const d = (tz ? day : fecha).format(now); if (date.current.textContent !== d) date.current.textContent = d }
      const el = tel.current
      if (!el || !stage) return
      const s = stage.stats()
      fps.push(s.fps)
      if (fps.length > 30) fps.shift()
      const [f, ms, calls, tier, line] = el.querySelectorAll('b, polyline')
      if (f) f.textContent = `${s.fps.toFixed(0)} fps`
      if (ms) ms.textContent = `${s.p90ms.toFixed(1)} ms`
      if (calls) calls.textContent = `${s.calls} llamadas`
      if (tier) tier.textContent = `×${s.renderScale.toFixed(2)} ${s.tier}`
      line?.setAttribute('points', fps.map((v, i) => `${(i / 29) * 100},${10 - Math.min(10, (v / 60) * 10)}`).join(' '))
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [stage, tz])

  return (
    <header className="nx-top ui">
      <div className="nx-brand">
        <svg viewBox="0 0 40 40" className="nx-sigil" aria-hidden="true">
          <circle cx="20" cy="20" r="17" /><path d="M20 3a17 17 0 0 1 14.7 8.5" className="hot" /><circle cx="20" cy="20" r="11" className="dash" /><circle cx="20" cy="20" r="4" className="f" />
        </svg>
        <div><b>Drakter</b><span>modo Jarvis · núcleo</span></div>
      </div>
      <div className="nx-clock" aria-hidden="true"><b ref={clock}>--:--</b><span ref={date} /></div>
      <div className="nx-tools">
        <div className="nx-chip" role="status"><i /><span>{CHARACTER_STATE_LABELS[state]}</span></div>
        {stage ? (
          <div className="nx-tel" ref={tel} aria-label="Telemetría del lienzo">
            <b>— fps</b><b>— ms</b><b>—</b><b>—</b>
            <svg viewBox="0 0 100 10" preserveAspectRatio="none" aria-hidden="true"><polyline points="" /></svg>
          </div>
        ) : null}
        <div className="nx-seg" role="group" aria-label="Calidad gráfica">
          {QUALITIES.map(([q, name]) => (
            <button key={q} type="button" aria-pressed={jarvisQuality === q} onClick={() => updatePreferences({ jarvisQuality: q })}>{name}</button>
          ))}
        </div>
      </div>
    </header>
  )
}
