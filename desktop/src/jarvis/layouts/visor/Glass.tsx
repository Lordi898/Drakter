/**
 * Cristal del Visor (fijo en pantalla): cinta de rumbo (los sectores son rumbos), escala de elevación,
 * retícula que fija objetivos (`[data-lock]`) y muelle de navegación. La esquina superior derecha es
 * del shell. Sin React por fotograma: la cinta se dibuja desde la capa solo si cambia el rumbo.
 */
import { useEffect, useRef } from 'react'
import { SECTOR_STEP, type VisorWorld } from './stage/world'

interface GlassProps {
  readonly world: VisorWorld | null
  readonly sector: number
  readonly names: readonly string[]
  readonly go: (sector: number) => void
  readonly exit: () => void
}
const ICE = '139,233,255', CORE = '233,252,255'

export function Glass({ world, sector, names, go, exit }: GlassProps) {
  const tapeRef = useRef<HTMLCanvasElement>(null)
  const ladderRef = useRef<HTMLCanvasElement>(null)
  const retRef = useRef<HTMLDivElement>(null)
  const lockRef = useRef<HTMLDivElement>(null)
  const labelRef = useRef<HTMLSpanElement>(null)
  const sectorRef = useRef(sector)
  sectorRef.current = sector

  // Cinta y escala: solo se redibujan si cambian rumbo, parallax, sector o tamaño.
  useEffect(() => {
    if (!world) return
    const sig = new Float64Array(6).fill(NaN)
    return world.onTick(() => {
      const tape = tapeRef.current, ladder = ladderRef.current
      if (!tape || !ladder) return
      const W = tape.clientWidth, LH = ladder.clientHeight
      const yawDeg = (((world.yaw * 180) / Math.PI) % 360 + 360) % 360, px = world.parallax
      if (Math.abs(yawDeg - sig[0]!) < 0.005 && Math.abs(px.x - sig[1]!) < 0.0005 && Math.abs(px.y - sig[2]!) < 0.0005 && W === sig[3] && LH === sig[4] && sectorRef.current === sig[5]) return
      sig[0] = yawDeg; sig[1] = px.x; sig[2] = px.y; sig[3] = W; sig[4] = LH; sig[5] = sectorRef.current
      if (tape.width !== W) { tape.width = W; tape.height = 58 }
      const x = tape.getContext('2d')!, perDeg = W / 110, cx = W / 2, cur = yawDeg + px.x * 2.6
      x.clearRect(0, 0, W, 58); x.globalCompositeOperation = 'lighter'
      for (let d = Math.floor(cur - 60); d <= cur + 60; d++) {
        const p = cx + (d - cur) * perDeg, edge = 1 - Math.min(1, Math.abs(p - cx) / (W * 0.48)), dd = ((d % 360) + 360) % 360, major = dd % 10 === 0
        x.fillStyle = `rgba(${ICE},${(major ? 0.7 : 0.25) * edge})`; x.fillRect(p, major ? 30 : 36, 1, major ? 12 : 6)
        if (major) { x.font = '300 9px "Recursive Variable", monospace'; x.textAlign = 'center'; x.fillStyle = `rgba(${ICE},${0.55 * edge})`; x.fillText(String(dd).padStart(3, '0'), p, 54) }
      }
      names.forEach((n, i) => {
        let d = (i * SECTOR_STEP * 180) / Math.PI - cur; d = ((d + 540) % 360) - 180
        if (Math.abs(d) > 58) return
        const p = cx + d * perDeg, on = sectorRef.current === i, edge = 1 - Math.min(1, Math.abs(p - cx) / (W * 0.5))
        x.font = `${on ? 600 : 400} ${on ? 13 : 12}px "Recursive Variable", sans-serif`; x.textAlign = 'center'
        x.fillStyle = on ? `rgba(${CORE},1)` : `rgba(${ICE},${0.7 * edge + 0.15})`; x.fillText(n, p, 20)
        x.beginPath(); x.moveTo(p - 4, 26); x.lineTo(p + 4, 26); x.lineTo(p, 31); x.fill()
      })
      x.fillStyle = `rgba(${CORE},1)`; x.beginPath(); x.moveTo(cx - 6, 58); x.lineTo(cx + 6, 58); x.lineTo(cx, 50); x.fill()
      if (ladder.height !== LH) { ladder.height = LH; ladder.width = 64 }
      const l = ladder.getContext('2d')!, pitch = -px.y * 7, cy = LH / 2
      l.clearRect(0, 0, 64, LH); l.globalCompositeOperation = 'lighter'
      for (let d = -30; d <= 30; d += 2) {
        const py = cy + (d - pitch) * 9; if (py < 0 || py > LH) continue
        const major = d % 10 === 0, fade = 1 - Math.abs(py - cy) / (LH / 2)
        l.fillStyle = `rgba(${ICE},${(major ? 0.7 : 0.28) * fade})`; l.fillRect(major ? 8 : 16, py, major ? 22 : 12, 1)
        if (major) { l.font = '300 9px "Recursive Variable", monospace'; l.fillText(`${d > 0 ? '+' : ''}${d}`, 34, py + 3) }
      }
    }, 30)
  }, [world, names])

  // Al girar, el objetivo fijado se va de su sitio: se suelta hasta el siguiente movimiento del puntero.
  const targetRef = useRef<HTMLElement | null>(null)
  useEffect(() => { targetRef.current = null; if (lockRef.current) lockRef.current.dataset.on = 'false' }, [sector])

  // Retícula y fijación de objetivos: solo con eventos del puntero (nada por fotograma).
  useEffect(() => {
    const T = targetRef
    const place = (): void => {
      const lock = lockRef.current
      if (!lock) return
      if (!T.current || !T.current.isConnected) { lock.dataset.on = 'false'; return }
      const r = T.current.getBoundingClientRect()
      lock.style.transform = `translate3d(${r.left - 6}px,${r.top - 6}px,0)`; lock.style.width = `${r.width + 12}px`; lock.style.height = `${r.height + 12}px`
      lock.dataset.on = 'true'
    }
    const onMove = (e: PointerEvent): void => {
      const ret = retRef.current
      if (ret) ret.style.transform = `translate3d(${e.clientX}px,${e.clientY}px,0)`
      const t = (e.target as HTMLElement | null)?.closest?.('.jv-visor [data-lock]') as HTMLElement | null
      if (t !== T.current) {
        T.current = t
        if (labelRef.current) labelRef.current.textContent = t ? `${t.closest('[data-code]')?.getAttribute('data-code') ?? ''}  ${t.dataset.lock ?? ''}` : ''
        lockRef.current?.classList.remove('fix'); void lockRef.current?.offsetWidth; if (t) lockRef.current?.classList.add('fix')
      }
      place()
    }
    addEventListener('pointermove', onMove, { passive: true })
    return () => removeEventListener('pointermove', onMove)
  }, [])

  return (
    <div className="jv-visor-glass" aria-hidden={false}>
      <div className="jv-visor-bezel" aria-hidden="true" />
      <canvas ref={tapeRef} className="jv-visor-tape" aria-hidden="true" onClick={(e) => {
        const W = e.currentTarget.clientWidth, perDeg = W / 110, cur = world ? (((world.yaw * 180) / Math.PI) % 360 + 360) % 360 : 0
        let best = 0, bd = Infinity
        names.forEach((_, i) => { let d = (i * SECTOR_STEP * 180) / Math.PI - cur; d = ((d + 540) % 360) - 180; const dd = Math.abs(W / 2 + d * perDeg - e.clientX); if (dd < bd) { bd = dd; best = i } })
        go(best)
      }} />
      <canvas ref={ladderRef} className="jv-visor-ladder" aria-hidden="true" />
      <div className="jv-visor-brand"><b>DRAKTER <span>visor</span></b></div>
      <div className="jv-visor-hz"><span>{names[sector]}</span><small>{String(Math.round((sector * 360) / 7)).padStart(3, '0')}°</small></div>
      <nav className="jv-visor-dock" aria-label="Sectores del visor">
        {names.map((n, i) => (
          <button key={n} type="button" className={i === sector ? 'on' : ''} aria-current={i === sector} data-lock={`Ir a ${n}  tecla ${i}`} onClick={() => go(i)}>
            <kbd>{i}</kbd>{n}
          </button>
        ))}
        <button type="button" className="exit" data-lock="Volver a Drakter" onClick={exit}>Volver a Drakter</button>
      </nav>
      <div ref={lockRef} className="jv-visor-lock" data-on="false" aria-hidden="true"><i /><i /><i /><i /><span ref={labelRef} /></div>
      <div ref={retRef} className="jv-visor-ret" aria-hidden="true"><i className="rr" /><i className="rd" /></div>
    </div>
  )
}
