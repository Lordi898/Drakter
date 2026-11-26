/** Piezas del HUD de la Holomesa. Datos de stores y del modelo real; sin trabajo por fotograma salvo la onda de voz activa. */
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { CHARACTER_STATE_LABELS } from '@/character/labels'
import type { CharacterState } from '@/character/types'
import { cancelActiveTurn, MAX_MESSAGE_CHARS, sendMessage, useActiveTurn, useChatMessages } from '@/stores/chat'
import { cancelJob, useJobs } from '@/stores/jobs'
import { acquireAudioTaps, readSpectrum, SPECTRUM_BANDS } from '@/voice/levels'
import { getSection } from '@/navigation/sections'
import { SECTION_NAMES, SECTION_ORDER, TO_APP_SECTION, type SectionId } from '../model'

// ───────────────────────────── estado del agente

const AGENT_DESC: Record<CharacterState, string> = {
  idle: 'Atento a «Hey Jarvis»', listening: 'Te escucho', thinking: 'Consultando el Workspace', speaking: 'Respuesta en voz',
  executing: 'Herramienta en curso', success: 'Acción completada', error: 'Algo falló', interrupted: 'Te cedo la palabra', offline: 'Sin conexión con el servicio'
}
const AGENT_COLOR: Record<CharacterState, string> = {
  idle: '#6fd6ff', listening: '#9fe8ff', thinking: '#8fb4ff', speaking: '#dff6ff', executing: '#6cf2d6', success: '#ffffff', error: '#ff7a5c', interrupted: '#ffb050', offline: '#47627a'
}

export function AgentChip({ state }: { readonly state: CharacterState }) {
  const active = state === 'thinking' || state === 'executing' || state === 'listening' || state === 'speaking'
  return (
    <div className={`hm-agent st-${state}`} role="status" aria-live="polite">
      <svg className={`hm-glyph${active ? ' spin' : ''}${state === 'executing' ? ' fast' : ''}`} viewBox="-20 -20 40 40" style={{ color: AGENT_COLOR[state] }} aria-hidden="true">
        <g className="g1"><circle r="17" fill="none" stroke="currentColor" strokeOpacity=".35" strokeDasharray="2 3" /></g>
        <g className="g2">
          <path d="M0 -13 A13 13 0 0 1 11.3 6.5" fill="none" stroke="currentColor" strokeWidth="2" />
          <path d="M-11.3 6.5 A13 13 0 0 1 -6 -11.5" fill="none" stroke="currentColor" strokeOpacity=".7" />
        </g>
        <circle r="8" fill="none" stroke="currentColor" strokeOpacity=".8" />
        <circle r="3.4" fill="currentColor" />
      </svg>
      <div>
        <div className="an">{CHARACTER_STATE_LABELS[state]}</div>
        <div className="ad">{AGENT_DESC[state]}</div>
      </div>
    </div>
  )
}

// ───────────────────────────── reloj (se repinta una vez por minuto)

export function Clock({ timezone }: { readonly timezone: string }) {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    let timer = 0
    const tick = (): void => {
      setNow(new Date())
      timer = window.setTimeout(tick, 60_000 - (Date.now() % 60_000) + 50)
    }
    timer = window.setTimeout(tick, 60_000 - (Date.now() % 60_000) + 50)
    return () => clearTimeout(timer)
  }, [])
  const tm = new Intl.DateTimeFormat('es-ES', { timeZone: timezone, hour: '2-digit', minute: '2-digit', hour12: false }).format(now)
  const dt = new Intl.DateTimeFormat('es-ES', { timeZone: timezone, weekday: 'long', day: 'numeric', month: 'long' }).format(now)
  return (
    <div className="hm-clock">
      <div className="tm num">{tm}</div>
      <div className="dt">{dt}</div>
    </div>
  )
}

// ───────────────────────────── carril

const ICONS: Record<SectionId, string> = {
  hoy: '<circle cx="8" cy="8" r="6"/><path d="M8 8V2.5M8 8l3.5 2"/>',
  calendario: '<path d="M3 4h10M3 7h10M3 10h10M3 13h10"/><path d="M5 2v13" opacity=".6"/>',
  tareas: '<rect x="2" y="9" width="4" height="5"/><rect x="7" y="5" width="4" height="9"/><rect x="12" y="11" width="2" height="3"/>',
  proyectos: '<path d="M2 14h12M4 14V7h3v7M9 14V4h3v10"/>',
  habitos: '<ellipse cx="8" cy="4" rx="5" ry="1.6"/><ellipse cx="8" cy="8" rx="5" ry="1.6"/><ellipse cx="8" cy="12" rx="5" ry="1.6"/>',
  relaciones: '<circle cx="4" cy="5" r="1.6"/><circle cx="12" cy="4" r="1.6"/><circle cx="9" cy="12" r="1.6"/><path d="M5.4 5.6l2.8 5M5.5 4.8l5-.6M11.5 5.5l-1.8 5"/>',
  almacen: '<path d="M2 4.5q6-3 12 0M2 8.5q6-3 12 0M2 12.5q6-3 12 0"/>'
}

export function Rail({ focus, metrics, onGo }: { readonly focus: SectionId | null; readonly metrics: Readonly<Record<SectionId, string>>; readonly onGo: (id: SectionId | null) => void }) {
  return (
    <nav className="hm-rail hm-unfold" style={{ ['--d' as string]: '0.1s' }} aria-label="Secciones de la Holomesa">
      <button type="button" className={focus === null ? 'on' : ''} onClick={() => onGo(null)} aria-current={focus === null ? 'true' : undefined} aria-keyshortcuts={getSection('home').shortcut}>
        <span className="k num">{getSection('home').shortcut}</span>
        <span className="txt"><span className="n">Vista general</span><span className="m">la mesa completa</span></span>
      </button>
      <div className="sep" />
      {SECTION_ORDER.map((id) => (
        <button key={id} type="button" className={focus === id ? 'on' : ''} onClick={() => onGo(id)} aria-current={focus === id ? 'true' : undefined} aria-keyshortcuts={getSection(TO_APP_SECTION[id]).shortcut}>
          {/* Iconos fijos del propio HUD (no vienen del usuario). */}
          <span className="k num"><svg viewBox="0 0 16 16" aria-hidden="true" dangerouslySetInnerHTML={{ __html: ICONS[id] }} />{getSection(TO_APP_SECTION[id]).shortcut}</span>
          <span className="txt"><span className="n">{SECTION_NAMES[id]}</span><span className="m">{metrics[id]}</span></span>
        </button>
      ))}
    </nav>
  )
}

// ───────────────────────────── conversación

const CHIPS = ['¿Qué tengo hoy?', '¿Qué tareas son urgentes?', '¿Cómo van mis hábitos?', 'Resume mis proyectos']
const QUIET_MS = 9000

export function Chat({ inputRef }: { readonly inputRef: React.RefObject<HTMLInputElement | null> }) {
  const messages = useChatMessages()
  const activeTurn = useActiveTurn()
  const [text, setText] = useState('')
  const [quiet, setQuiet] = useState(false)
  const logRef = useRef<HTMLDivElement>(null)
  const last = messages.slice(-30)

  // Se recoge tras un rato sin actividad (un temporizador, nada por fotograma).
  useEffect(() => {
    setQuiet(false)
    const timer = setTimeout(() => setQuiet(true), QUIET_MS)
    return () => clearTimeout(timer)
  }, [messages, text])

  useEffect(() => {
    const el = logRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages])

  const send = (value: string): void => {
    const v = value.trim()
    if (!v || v.length > MAX_MESSAGE_CHARS) return
    setText('')
    void sendMessage(v)
  }
  const onSubmit = (e: FormEvent): void => {
    e.preventDefault()
    send(text)
  }

  return (
    <section className={`hm-pane hm-chat hm-unfold${quiet ? ' quiet' : ''}`} style={{ ['--d' as string]: '0.25s' }} aria-label="Conversación con Drakter">
      <div className="hm-ph">
        <h3>Conversación</h3>
        <span>{activeTurn ? 'respondiendo…' : 'Hermes · Haiku'}</span>
      </div>
      <div className="hm-log" ref={logRef} aria-live="polite">
        {last.length === 0 ? <p className="hm-empty">Pregúntame lo que quieras o di «Hey Jarvis».</p> : null}
        {last.map((m) => (
          <div key={m.id} className={`hm-msg${m.role === 'user' ? ' me' : ''}${m.status === 'failed' ? ' failed' : ''}`}>
            <div className="who">{m.role === 'user' ? (m.viaVoice ? 'Tú · voz' : 'Tú') : 'Drakter'}</div>
            {m.content || (m.status === 'streaming' || m.status === 'sending' ? '…' : '')}
            {m.error ? <div className="who" style={{ color: '#ffb3bd' }}>{m.error}</div> : null}
            {m.tools.length ? (
              <div className="tools">
                {m.tools.map((t) => <span key={t.id} className={t.state === 'failed' ? 'failed' : ''}>{t.name}{t.state === 'running' ? '…' : ''}</span>)}
              </div>
            ) : null}
          </div>
        ))}
      </div>
      <div className="hm-chips">
        {CHIPS.map((c) => <button key={c} type="button" onClick={() => send(c)} disabled={activeTurn !== null}>{c}</button>)}
      </div>
      <form className="hm-composer" onSubmit={onSubmit}>
        <input ref={inputRef} value={text} maxLength={MAX_MESSAGE_CHARS} onChange={(e) => setText(e.target.value)} placeholder="Escribe a Drakter… (/)" aria-label="Mensaje para Drakter" />
        {activeTurn ? (
          <button type="button" className="hm-btn" onClick={() => void cancelActiveTurn()}>Parar</button>
        ) : (
          <button type="submit" className="hm-btn" disabled={!text.trim()}>Enviar</button>
        )}
      </form>
    </section>
  )
}

// ───────────────────────────── consola de voz

/** Espectro real (salida si habla, micrófono si escucha) en un canvas 2D sin sombras; parado en reposo. */
export function VoiceConsole({ state, dockRef }: { readonly state: CharacterState; readonly dockRef: React.RefObject<HTMLDivElement | null> }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [db, setDb] = useState<string>('—')
  const active = state === 'speaking' || state === 'listening'
  useEffect(() => {
    const canvas = canvasRef.current
    const g = canvas?.getContext('2d')
    if (!canvas || !g) return
    const fit = (): { w: number; h: number } => {
      const w = canvas.clientWidth, h = canvas.clientHeight, dpr = Math.min(2, window.devicePixelRatio || 1)
      if (canvas.width !== Math.round(w * dpr)) {
        canvas.width = Math.round(w * dpr)
        canvas.height = Math.round(h * dpr)
      }
      g.setTransform(dpr, 0, 0, dpr, 0, 0)
      return { w, h }
    }
    const bands = new Uint8Array(SPECTRUM_BANDS)
    const smooth = new Float32Array(SPECTRUM_BANDS)
    const draw = (live: boolean): number => {
      const { w, h } = fit()
      g.clearRect(0, 0, w, h)
      const got = live && readSpectrum(state === 'listening' ? 'input' : 'output', bands)
      const n = 48, bw = w / n, mid = h / 2
      let peak = 0
      for (let i = 0; i < n; i++) {
        const v = got ? (bands[Math.floor((i / n) * SPECTRUM_BANDS)] ?? 0) / 255 : 0
        smooth[i] = smooth[i]! + (v - smooth[i]!) * 0.45
        peak = Math.max(peak, smooth[i]!)
        const bh = Math.max(1, smooth[i]! * h * 0.46)
        g.fillStyle = `rgba(${120 + smooth[i]! * 130},${215 + smooth[i]! * 40},255,${0.35 + smooth[i]! * 0.65})`
        g.fillRect(i * bw + bw * 0.22, mid - bh, bw * 0.56, bh * 2)
      }
      g.strokeStyle = 'rgba(234,250,255,.55)'
      g.lineWidth = 1
      g.beginPath()
      g.moveTo(0, mid)
      g.lineTo(w, mid)
      g.stroke()
      return peak
    }
    if (!active) {
      draw(false)
      setDb('—')
      return
    }
    const release = acquireAudioTaps()
    let raf = 0, last = 0, lastDb = 0
    const loop = (t: number): void => {
      raf = requestAnimationFrame(loop)
      if (t - last < 33 || document.hidden) return
      last = t
      const peak = draw(true)
      if (t - lastDb > 500) {
        lastDb = t
        setDb(peak > 0.02 ? `${Math.round(-60 + peak * 54)} dB` : '—')
      }
    }
    raf = requestAnimationFrame(loop)
    return () => {
      cancelAnimationFrame(raf)
      release()
    }
  }, [active, state])

  const text = state === 'listening' ? 'Micrófono abierto' : state === 'speaking' ? 'Voz de Drakter' : state === 'offline' ? 'Voz no disponible' : 'En espera · «Hey Jarvis» o Super+J'
  return (
    <section className="hm-pane hm-voice hm-unfold" style={{ ['--d' as string]: '0.35s' }} aria-label="Consola de voz">
      <div className="dock" ref={dockRef} aria-hidden="true" />
      <canvas ref={canvasRef} aria-hidden="true" />
      <div className="vl">
        <span><b>{text}</b></span>
        <span className="num">{db}</span>
      </div>
    </section>
  )
}

// ───────────────────────────── trabajos en segundo plano

const JOB_STATE: Record<string, string> = { running: 'en curso', completed: 'hecho', failed: 'falló', cancelled: 'cancelado' }

export function Jobs() {
  const jobs = useJobs()
  const shown = [...jobs].sort((a, b) => Number(b.state === 'running') - Number(a.state === 'running') || b.created_at.localeCompare(a.created_at)).slice(0, 4)
  const running = jobs.filter((j) => j.state === 'running').length
  return (
    <section className="hm-pane hm-jobs hm-unfold" style={{ ['--d' as string]: '0.45s' }} aria-label="Trabajos en segundo plano">
      <div className="hm-ph">
        <h3>Trabajos</h3>
        <span>{running ? `${running} activos` : 'ninguno activo'}</span>
      </div>
      {shown.length === 0 ? <p className="hm-empty">Sin trabajos recientes.</p> : null}
      {shown.map((j) => (
        <div key={j.job_id} className={`hm-job ${j.state}`}>
          <div className="jn">
            <span>{j.title}</span>
            <em>
              {JOB_STATE[j.state] ?? j.state}
              {j.state === 'running' ? (
                <button type="button" className="hm-btn" style={{ marginLeft: 8, padding: '0 6px' }} onClick={() => void cancelJob(j.job_id)} aria-label={`Cancelar ${j.title}`}>×</button>
              ) : null}
            </em>
          </div>
          <div className="jb"><i style={j.state === 'running' ? undefined : { transform: 'scaleX(1)', opacity: j.state === 'completed' ? 0.6 : 0.3 }} /></div>
        </div>
      ))}
    </section>
  )
}
