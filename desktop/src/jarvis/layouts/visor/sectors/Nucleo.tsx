/**
 * Sector Núcleo (rumbo 000°, sección `home`): avatar con su halo, voz, conversación real, trabajos en
 * segundo plano, actividad del agente y su estado. Nada simulado: stores y `jarvis/data`.
 */
import { useContext, useEffect, useRef, useState, type FormEvent } from 'react'
import { CHARACTER_STATES, type CharacterState } from '@/character/types'
import { useJarvisData } from '@/jarvis/data'
import { useDrakterState } from '@/stores/agent'
import { sendMessage, useActiveTurn, useChatMessages } from '@/stores/chat'
import { useJobs } from '@/stores/jobs'
import { readWaveform, WAVEFORM_SAMPLES } from '@/voice/levels'
import type { JarvisAvatarSlot } from '../../types'
import { Panel, WorldContext } from '../Panel'
import { D } from '../stage/world'

export const STATE_ES: Record<CharacterState, string> = {
  idle: 'En reposo', listening: 'Escuchando', thinking: 'Pensando', speaking: 'Hablando', executing: 'Ejecutando',
  success: 'Hecho', error: 'Error', interrupted: 'Interrumpido', offline: 'Sin conexión'
}
const time = (iso: string): string => new Date(iso).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })
const elapsed = (s: number): string => (s < 60 ? `${Math.round(s)} s` : `${Math.floor(s / 60)} min ${Math.round(s % 60)} s`)

/** Forma de onda real (`voice/levels`) en un lienzo 2D, a ritmo limitado por la capa. */
function Wave({ state }: { readonly state: CharacterState }) {
  const world = useContext(WorldContext)
  const ref = useRef<HTMLCanvasElement>(null)
  const stateRef = useRef(state)
  stateRef.current = state
  useEffect(() => {
    const cv = ref.current
    if (!world || !cv) return
    const x = cv.getContext('2d')
    if (!x) return
    const buf = new Float32Array(WAVEFORM_SAMPLES)
    let wasFlat = false
    return world.onTick(() => {
      const s = stateRef.current
      const got = readWaveform(s === 'listening' ? 'input' : 'output', buf)
      let peak = 0
      if (got) for (let i = 0; i < buf.length; i++) peak = Math.max(peak, Math.abs(buf[i]!))
      const flat = peak < 0.01
      if (flat && wasFlat) return // en silencio no se redibuja: cero trabajo en reposo
      wasFlat = flat
      const { width: w, height: h } = cv, mid = h / 2
      x.clearRect(0, 0, w, h)
      x.globalCompositeOperation = 'lighter'
      const rgb = s === 'error' ? '255,75,92' : s === 'listening' ? '95,200,255' : '139,233,255'
      for (let px = 0; px <= w; px += 10) { x.fillStyle = `rgba(${rgb},${px % 50 === 0 ? 0.35 : 0.14})`; x.fillRect(px, mid - (px % 50 === 0 ? 5 : 2), 1, px % 50 === 0 ? 10 : 4) }
      x.beginPath()
      for (let px = 0; px <= w; px += 2) { const v = got ? buf[Math.floor((px / w) * (buf.length - 1))]! : 0; const yy = mid + v * h * 0.45 * Math.sin((px / w) * Math.PI); px ? x.lineTo(px, yy) : x.moveTo(px, yy) }
      x.strokeStyle = `rgba(${rgb},0.18)`; x.lineWidth = 6; x.stroke(); x.strokeStyle = `rgba(${rgb},0.95)`; x.lineWidth = 1.5; x.stroke()
      x.globalCompositeOperation = 'source-over'
    }, 30)
  }, [world])
  return <canvas ref={ref} width={400} height={52} className="jv-visor-wave" aria-hidden="true" />
}

function Chat() {
  const messages = useChatMessages()
  const active = useActiveTurn()
  const [text, setText] = useState('')
  const listRef = useRef<HTMLDivElement>(null)
  const last = messages.slice(-8)
  useEffect(() => { listRef.current?.scrollTo({ top: 1e6 }) }, [last.length, last.at(-1)?.content])
  const submit = (e: FormEvent): void => {
    e.preventDefault()
    const t = text.trim()
    if (!t) return
    setText('')
    void sendMessage(t)
  }
  return (
    <>
      <div className="jv-visor-msgs" ref={listRef} aria-live="polite">
        {last.length === 0 && <p className="jv-visor-note">Escribe o habla para empezar.</p>}
        {last.map((m) => (
          <div key={m.id} className={`jv-visor-msg ${m.role === 'user' ? 'yo' : 'dk'}`}>
            <span className="who">{m.role === 'user' ? 'Tú' : 'Drakter'}{m.status === 'failed' ? ' · no se pudo enviar' : ''}</span>
            <p>{m.content}</p>
          </div>
        ))}
      </div>
      <form className="jv-visor-chat-in" onSubmit={submit}>
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder={active ? 'Drakter está respondiendo…' : 'Escribe a Drakter…'} aria-label="Mensaje para Drakter" />
        <button type="submit" data-lock="Enviar mensaje" disabled={!text.trim()}>Enviar</button>
      </form>
    </>
  )
}

function Jobs() {
  const jobs = useJobs()
  const { activity } = useJarvisData(['activity'])
  const running = jobs.filter((j) => j.state === 'running')
  const recent = jobs.filter((j) => j.state !== 'running').slice(0, Math.max(0, 3 - running.length))
  return (
    <>
      {running.length === 0 && recent.length === 0 && <p className="jv-visor-note">No hay trabajos en segundo plano.</p>}
      {[...running, ...recent].map((j) => (
        <div key={j.job_id} className={`jv-visor-job ${j.state}`} data-lock={`${j.title}  ${j.state === 'running' ? elapsed(j.elapsed_s) : j.state}`}>
          <div className="jb-h"><b>{j.title}</b><em>{j.state === 'running' ? elapsed(j.elapsed_s) : j.state === 'completed' ? 'hecho' : j.state === 'failed' ? 'falló' : 'cancelado'}</em></div>
          <small>{j.tool_calls} herramientas{j.last_tool ? `  ·  ${j.last_tool}` : ''}{j.pending_actions ? `  ·  ${j.pending_actions} por confirmar` : ''}</small>
          <div className="jb-bar"><i className={j.state === 'running' ? 'run' : ''} /></div>
        </div>
      ))}
      <div className="jv-visor-feed">
        {(activity.data ?? []).slice(0, 4).map((e) => (
          <div key={e.id} className="fl"><time>{time(e.occurred_at)}</time>{e.tool_name ?? e.action}{e.entity_type ? ` · ${e.entity_type}` : ''}</div>
        ))}
        {activity.status === 'offline' && <div className="fl">Sin conexión con el backend</div>}
      </div>
    </>
  )
}

export function Nucleo({ avatar }: { readonly avatar: JarvisAvatarSlot }) {
  const state = useDrakterState()
  const { memory } = useJarvisData(['memory'])
  const jobs = useJobs()
  const messages = useChatMessages()
  const tools = messages.at(-1)?.tools ?? []
  const world = useContext(WorldContext)
  useEffect(() => { world?.setAgentState(state) }, [world, state])
  const running = jobs.filter((j) => j.state === 'running').length

  return (
    <>
      <Panel sector={0} R={D + 100} y={46} w={540} h={640} alpha={0.18} avatar title="Drakter" code="NUC-AV" className="av">
        {!avatar.available && <div className="jv-visor-orb" aria-hidden="true" />}
        <div className="jv-visor-callouts" aria-hidden="true">
          <div className="co c1"><b>{STATE_ES[state]}</b><span>estado</span></div>
          <div className="co c2"><b>{running}</b><span>trabajos en curso</span></div>
          <div className="co c3"><b>{memory.data ? (memory.data.available ? 'activa' : 'sin conexión') : '…'}</b><span>memoria {memory.data?.backend ?? ''}</span></div>
          <div className="co c4"><b>{tools.length}</b><span>herramientas en el último turno</span></div>
        </div>
      </Panel>
      <Panel sector={0} R={D - 60} y={-330} w={440} h={92} side title="Voz" code="NUC-VZ" className="wave">
        <Wave state={state} />
      </Panel>
      <Panel sector={0} dA={23.5} R={D - 120} y={-6} w={450} h={640} side title="Conversación" code="NUC-CH" className="chat">
        <Chat />
      </Panel>
      <Panel sector={0} dA={-23.5} R={D - 120} y={150} w={430} h={360} side title="Trabajos en segundo plano" code="NUC-JB">
        <Jobs />
      </Panel>
      <Panel sector={0} dA={-23.5} R={D - 120} y={-205} w={430} h={262} side title="Estado del agente" code="NUC-ST">
        <div className="jv-visor-st"><b>{STATE_ES[state]}</b></div>
        <ul className="jv-visor-chips">
          {CHARACTER_STATES.map((s) => <li key={s} className={s === state ? 'on' : ''}>{STATE_ES[s]}</li>)}
        </ul>
      </Panel>
    </>
  )
}
