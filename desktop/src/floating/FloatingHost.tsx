import { useEffect } from 'react'
import { holdAudioAwake } from '@/voice/levels'
import { floatingApi } from './api'
import { FloatingHelpDialog } from './FloatingHelpDialog'
import { startLevelsForwarder } from './levels'
import { startFloatingState, useFloating } from './store'

/**
 * Vive en `SessionHosts` (los dos modos): refleja el estado de main, reenvía los niveles de voz
 * cuando main los pide y pinta la ayuda de instalación. Con el modo activo la ventana se oculta a la
 * bandeja, pero el `AudioContext` de los niveles no se suspende (CONTRACT §4.4).
 */
export function FloatingHost() {
  const active = useFloating().state?.active === true

  useEffect(() => startFloatingState(), [])
  useEffect(() => startLevelsForwarder(floatingApi()), [])
  useEffect(() => (active ? holdAudioAwake() : undefined), [active])

  return <FloatingHelpDialog />
}
