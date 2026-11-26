import { useEffect } from 'react'
import { UI_MODE_SHORTCUT, UI_MODE_SHORTCUT_LABEL } from '@/app/useGlobalShortcuts'
import { CHARACTER_STATE_LABELS } from '@/character/labels'
import { useDrakterState } from '@/stores/agent'
import { requestUiMode, settleUiMode } from '@/stores/uiMode'

// Fondo estático en CSS (sin lienzo ni bucle): retícula fina y halo central. Coste de GPU ~0.
const BACKDROP = [
  'radial-gradient(ellipse at 50% 45%, rgba(56, 189, 248, 0.16), transparent 60%)',
  'linear-gradient(rgba(125, 211, 252, 0.06) 1px, transparent 1px)',
  'linear-gradient(90deg, rgba(125, 211, 252, 0.06) 1px, transparent 1px)'
].join(', ')

/**
 * Shell del modo Jarvis. STUB de W1: fondo y «Volver a Drakter». El HUD real (Stage WebGL, paneles,
 * arranque) llega en W3 y W8-W10 sobre este mismo punto de entrada (export default, carga diferida).
 * Todo lo de sesión (voz, avisos, confirmaciones) sigue vivo en `SessionHosts`.
 */
export default function JarvisShell() {
  const state = useDrakterState()

  // Ya montado y pintado: la transición termina y Drakter se desmonta.
  useEffect(() => {
    const frame = requestAnimationFrame(() => settleUiMode('ready'))
    return () => cancelAnimationFrame(frame)
  }, [])

  return (
    <main
      aria-label="Modo Jarvis"
      className="dark flex size-full animate-in flex-col items-center justify-center gap-8 bg-[#02060c] text-sky-100 duration-500 fade-in"
      style={{ backgroundImage: BACKDROP, backgroundSize: '100% 100%, 48px 48px, 48px 48px' }}
    >
      <div className="flex flex-col items-center gap-3 text-center">
        <p className="font-mono text-xs tracking-[0.4em] text-sky-300/70 uppercase">Drakter</p>
        <h1 className="text-4xl font-light tracking-[0.25em] text-sky-50 uppercase [text-shadow:0_0_18px_rgba(56,189,248,0.55)]">
          Modo Jarvis
        </h1>
        <p className="max-w-[46ch] text-sm text-sky-200/75">
          La interfaz holográfica está en construcción. La voz, los avisos y las confirmaciones siguen
          funcionando como siempre.
        </p>
        <p className="font-mono text-xs text-sky-300/80" role="status">
          Estado: {CHARACTER_STATE_LABELS[state]}
        </p>
      </div>

      <button
        type="button"
        autoFocus
        aria-keyshortcuts={UI_MODE_SHORTCUT}
        onClick={() => requestUiMode('drakter', 'button')}
        className="rounded-md border border-sky-400/50 bg-sky-400/10 px-5 py-2.5 text-sm font-medium tracking-wide text-sky-50 shadow-[0_0_24px_rgba(56,189,248,0.25)] transition-colors outline-none hover:bg-sky-400/20 focus-visible:ring-2 focus-visible:ring-sky-300"
      >
        Volver a Drakter
        <span className="ml-2 font-mono text-xs text-sky-300/80">{UI_MODE_SHORTCUT_LABEL}</span>
      </button>
    </main>
  )
}
