/**
 * Columnas de la vista núcleo. Izquierda: estado del agente y de la voz, actividad de herramientas en
 * directo (de `stores/chat`) y trabajos en segundo plano (Drakter Jobs, cancelables). Derecha: la
 * conversación real con su osciloscopio (`voice/levels.ts`) y la entrada de texto.
 */
import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import type { CharacterState } from '@/character/types'
import { CHARACTER_STATE_LABELS } from '@/character/labels'
import { describeError } from '@/services/api'
import { cancelActiveTurn, sendMessage, useActiveTurn, useChatMessages, type ChatMessage } from '@/stores/chat'
import { cancelJob, useJobs } from '@/stores/jobs'
import { useLinkStatus } from '@/stores/connection'
import { setTtsEnabled, useVoice } from '@/stores/voice'
import { readWaveform, WAVEFORM_SAMPLES } from '@/voice/levels'
import { stateCss } from '../gl/scene'

const SUB: Readonly<Record<CharacterState, string>> = {
  idle: 'a la escucha de «Hey Jarvis»', listening: 'micrófono abierto', thinking: 'razonando la respuesta', speaking: 'hablando',
  executing: 'usando una herramienta', success: 'acción completada', error: 'algo ha fallado', interrupted: 'interrumpido', offline: 'el servicio local no responde'
}
const MIC: Readonly<Record<string, string>> = { off: 'apagado', standby: 'en espera', live: 'abierto', error: 'con error' }
const pad2 = (n: number): string => String(n).padStart(2, '0')

export function LeftColumn({ state }: { readonly state: CharacterState }) {
  const messages = useChatMessages()
  const jobs = useJobs()
  const link = useLinkStatus()
  const { ttsEnabled, mic } = useVoice()
  const [jobError, setJobError] = useState<string | null>(null)
  const tools = useMemo(() => {
    const out: { id: string; name: string; state: string }[] = []
    for (let i = messages.length - 1; i >= 0 && out.length < 7; i--) for (const t of [...messages[i]!.tools].reverse()) if (out.length < 7) out.push(t)
    return out
  }, [messages])
  const running = jobs.filter((j) => j.state === 'running')

  return (
    <aside className="nx-col nx-colL ui" aria-label="Estado y actividad">
      <section className="pn" data-lock="Estado del agente">
        <h3><b>Estado del agente</b><span>Hermes</span></h3>
        <div className="nx-stbig">
          <svg viewBox="0 0 64 64" className="nx-stg" aria-hidden="true"><circle cx="32" cy="32" r="27" className="a" /><circle cx="32" cy="32" r="20" className="b" /><circle cx="32" cy="32" r="7" className="c" /></svg>
          <div><b>{CHARACTER_STATE_LABELS[state]}</b><span>{SUB[state]}</span></div>
        </div>
        <div className="nx-meta">
          <span>Enlace</span><b>{link === 'open' ? 'conectado' : link}</b>
          <span>Micrófono</span><b>{MIC[mic] ?? mic}</b>
          <span>Voz de Drakter</span>
          <b><button type="button" className="btn ghost" data-lock={ttsEnabled ? 'Silenciar la voz' : 'Activar la voz'} onClick={() => void setTtsEnabled(!ttsEnabled)}>{ttsEnabled ? 'activada' : 'silenciada'}</button></b>
        </div>
      </section>
      <section className="pn" aria-live="polite">
        <h3><b>Actividad</b><span>herramientas</span></h3>
        {tools.length ? (
          <ul className="nx-log">{tools.map((t) => <li key={t.id} className={t.state}><i /><b>{t.name}</b><span>{t.state === 'running' ? 'en curso' : t.state === 'ok' ? 'correcto' : 'falló'}</span></li>)}</ul>
        ) : <p className="nx-empty">Sin herramientas en esta conversación.</p>}
      </section>
      <section className="pn nx-pJobs">
        <h3><b>Trabajos en segundo plano</b><span>{running.length} en curso</span></h3>
        {jobs.length ? (
          <ul className="nx-jobs">
            {jobs.slice(0, 5).map((j) => (
              <li key={j.job_id} className={j.state} data-lock={j.title}>
                <div><b>{j.title}</b><em>{j.state === 'running' ? `${Math.round(j.elapsed_s)} s` : j.state === 'completed' ? 'hecho' : j.state === 'failed' ? 'falló' : 'cancelado'}</em></div>
                <span className="bar" style={{ ['--p' as string]: j.state === 'running' ? 0.5 : 1, ['--c' as string]: j.state === 'failed' ? 'var(--red)' : j.state === 'completed' ? 'var(--warm)' : 'var(--cyan)' }}><i /></span>
                <small>{j.last_tool ? `última: ${j.last_tool} · ` : ''}{j.tool_calls} llamadas{j.reason ? ` · ${j.reason}` : ''}</small>
                {j.state === 'running' ? <button type="button" className="btn ghost" onClick={() => cancelJob(j.job_id).catch((e: unknown) => setJobError(describeError(e, 'No se pudo cancelar.')))}>Cancelar</button> : null}
              </li>
            ))}
          </ul>
        ) : <p className="nx-empty">No hay trabajos.</p>}
        {jobError ? <p className="err" role="alert">{jobError}</p> : null}
      </section>
    </aside>
  )
}

/** Osciloscopio 2D: solo se dibuja mientras hay voz (hablando o escuchando); en reposo, una línea plana y nada más. */
function Oscilloscope({ state, quality }: { readonly state: CharacterState; readonly quality: string }) {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const cv = ref.current, g = cv?.getContext('2d')
    if (!cv || !g) return
    const buf = new Float32Array(WAVEFORM_SAMPLES), col = stateCss(state)
    const draw = (flat: boolean): void => {
      const w = cv.width, h = cv.height
      g.clearRect(0, 0, w, h)
      g.lineJoin = 'round'
      for (const [lw, al] of [[7, 0.13], [1.8, 1]] as const) {
        g.beginPath(); g.lineWidth = lw; g.strokeStyle = col; g.globalAlpha = al
        for (let i = 0; i <= 150; i++) {
          const x = (i / 150) * w, s = flat ? 0 : buf[Math.floor((i / 150) * (WAVEFORM_SAMPLES - 1))]! * Math.sin((i / 150) * Math.PI)
          if (i) g.lineTo(x, h / 2 + Math.max(-0.46, Math.min(0.46, s * 0.9)) * h); else g.moveTo(x, h / 2)
        }
        g.stroke()
      }
      g.globalAlpha = 1
    }
    const tap = state === 'speaking' ? 'output' : state === 'listening' ? 'input' : null
    if (!tap || quality === 'ahorro') { draw(true); return }
    let raf = 0, last = 0
    const loop = (now: number): void => {
      raf = requestAnimationFrame(loop)
      if (now - last < 66) return // 15 Hz
      last = now
      draw(!readWaveform(tap, buf))
    }
    raf = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(raf)
  }, [state, quality])
  return <canvas ref={ref} className="nx-osc" width={600} height={96} aria-hidden="true" />
}

const SUGGESTIONS = ['¿Qué tengo hoy?', '¿Qué tareas vencen esta semana?', 'Resúmeme mis hábitos']

export function useSend(): { send: (text: string) => void; error: string | null } {
  const [error, setError] = useState<string | null>(null)
  return {
    error,
    send: (text) => {
      const t = text.trim()
      if (!t) return
      setError(null)
      sendMessage(t).catch((e: unknown) => setError(describeError(e, 'No se pudo enviar el mensaje.')))
    }
  }
}

export function SayForm({ id, placeholder, levelRef }: { readonly id: string; readonly placeholder: string; readonly levelRef?: React.Ref<HTMLElement> }) {
  const { send, error } = useSend()
  const active = useActiveTurn()
  const onSubmit = (e: FormEvent<HTMLFormElement>): void => {
    e.preventDefault()
    const input = e.currentTarget.elements.namedItem('q') as HTMLInputElement
    send(input.value)
    input.value = ''
  }
  return (
    <>
      <form className="nx-say" onSubmit={onSubmit}>
        <label className="nx-sr" htmlFor={id}>Mensaje para Drakter</label>
        <input id={id} name="q" autoComplete="off" placeholder={placeholder} maxLength={8000} />
        {active ? <button type="button" data-lock="Parar la respuesta" onClick={() => void cancelActiveTurn()}>Parar</button> : <button type="submit" data-lock="Enviar mensaje">Enviar</button>}
        {levelRef ? <i className="nx-lvl" ref={levelRef} /> : null}
      </form>
      {error ? <p className="err" role="alert">{error}</p> : null}
    </>
  )
}

function stamp(m: ChatMessage): string {
  return m.role === 'user' ? (m.viaVoice ? 'Tú · por voz' : 'Tú') : m.status === 'failed' ? 'Drakter · error' : 'Drakter'
}

export function RightColumn({ state, quality }: { readonly state: CharacterState; readonly quality: string }) {
  const messages = useChatMessages()
  const { send } = useSend()
  const last = messages.slice(-9)
  return (
    <aside className="nx-col nx-colR ui" aria-label="Conversación">
      <section className="pn nx-chat">
        <h3><b>Conversación</b><span>voz y texto</span></h3>
        <div className="nx-msgs" aria-live="polite">
          {last.map((m) => (
            <div key={m.id} className={`nx-m ${m.role} ${m.status === 'failed' ? 'failed' : ''} ${m.status === 'streaming' ? 'live' : ''}`}>
              <span>{stamp(m)}</span>
              <p>{m.status === 'failed' ? m.error ?? 'La respuesta falló.' : m.content}</p>
            </div>
          ))}
          {!last.length ? <p className="nx-empty">Di «Hey Jarvis» o escribe abajo.</p> : null}
        </div>
        <Oscilloscope state={state} quality={quality} />
        <div className="nx-sugg">{SUGGESTIONS.map((s) => <button key={s} type="button" data-lock={`Preguntar: ${s}`} onClick={() => send(s)}>{s}</button>)}</div>
        <SayForm id="nx-say-main" placeholder="Habla con Drakter…" />
      </section>
    </aside>
  )
}

export const timeOf = (d: Date): string => `${pad2(d.getHours())}:${pad2(d.getMinutes())}`
