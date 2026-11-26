import { Component, lazy, Suspense, useEffect, useRef, type ReactNode } from 'react'
import { AppShell } from '@/app/AppShell'
import { UI_MODE_BUTTON_ID } from '@/app/JarvisModeButton'
import { notify } from '@/services/notify'
import { getUiMode, loadJarvisShell, resetUiMode, settleUiMode, useUiMode, type UiMode } from '@/stores/uiMode'

// React guarda el resultado de `lazy`: tras un fallo de carga se crea otro para poder reintentar.
let JarvisShell = lazy(loadJarvisShell)

class JarvisBoundary extends Component<{ readonly children: ReactNode }, { readonly failed: boolean }> {
  override state = { failed: false }

  static getDerivedStateFromError(): { failed: boolean } {
    return { failed: true }
  }

  override componentDidCatch(error: unknown): void {
    console.warn('El modo Jarvis falló; se vuelve a Drakter.', error)
    JarvisShell = lazy(loadJarvisShell)
    if (getUiMode().phase === 'entering') settleUiMode('failed')
    else resetUiMode()
    notify({
      tone: 'warning',
      title: 'No se pudo abrir el modo Jarvis',
      body: 'Sigues en Drakter. Puedes volver a intentarlo.'
    })
  }

  override render(): ReactNode {
    return this.state.failed ? null : this.props.children
  }
}

const ANNOUNCEMENTS: Record<UiMode, string> = {
  jarvis: 'Modo Jarvis activado',
  drakter: 'Modo Drakter activado'
}

/**
 * Elige el shell. Solo hay uno montado salvo en la transición: al entrar, Jarvis se monta encima
 * de Drakter y avisa con `settleUiMode('ready')`; al salir, Drakter se monta debajo y aquí se
 * cierra la transición en cuanto está pintado. Lo que no puede cortarse vive en `SessionHosts`.
 */
export function ModeRoot() {
  const { mode, target, phase, source } = useUiMode()
  const showDrakter = mode === 'drakter' || target === 'drakter'
  const showJarvis = mode === 'jarvis' || target === 'jarvis'
  const previousPhase = useRef(phase)

  useEffect(() => {
    document.documentElement.dataset.uiMode = mode
  }, [mode])

  useEffect(() => {
    if (phase !== 'leaving') return
    const frame = requestAnimationFrame(() => settleUiMode('ready'))
    return () => cancelAnimationFrame(frame)
  }, [phase])

  // De vuelta en Drakter, el foco va al botón que abre Jarvis en vez de perderse en <body>.
  useEffect(() => {
    const was = previousPhase.current
    previousPhase.current = phase
    if (was === 'leaving' && phase === 'idle' && mode === 'drakter') {
      document.getElementById(UI_MODE_BUTTON_ID)?.focus()
    }
  }, [phase, mode])

  return (
    <>
      {showDrakter ? (
        <div className="h-full" inert={showJarvis}>
          <AppShell />
        </div>
      ) : null}
      {showJarvis ? (
        <div className="fixed inset-0 z-40">
          <JarvisBoundary>
            <Suspense fallback={<div className="size-full bg-[#02060c]" aria-hidden="true" />}>
              <JarvisShell />
            </Suspense>
          </JarvisBoundary>
        </div>
      ) : null}
      <p role="status" className="sr-only">
        {source !== null && phase === 'idle' ? ANNOUNCEMENTS[mode] : ''}
      </p>
    </>
  )
}
