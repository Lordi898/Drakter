import { Mic, MicOff } from 'lucide-react'
import { CHARACTER_STATE_LABELS } from '@/character/labels'
import type { CharacterState } from '@/character/types'
import { retryBackendLink } from '@/services/ws'
import { useDrakterState } from '@/stores/agent'
import { useLinkStatus } from '@/stores/connection'
import { cn } from '@/lib/utils'
import { useVoice } from '@/stores/voice'

type Tone = 'active' | 'off' | 'error'

const TONES: Record<CharacterState, Tone> = {
  idle: 'active',
  listening: 'active',
  thinking: 'active',
  speaking: 'active',
  executing: 'active',
  success: 'active',
  error: 'error',
  interrupted: 'active',
  offline: 'off'
}

const LIGHT: Record<Tone, string> = {
  active: 'bg-ambar',
  off: 'border border-chassis-muted',
  error: 'bg-destructive'
}

const LINK_TEXT = {
  connecting: 'Conectando…',
  reconnecting: 'Reconectando…',
  disconnected: 'Sin conexión con el backend'
} as const

/** Única región viva del estado de Drakter: el personaje (role="img") no anuncia nada. */
export function DrakterStatus() {
  const state = useDrakterState()
  const link = useLinkStatus()
  const { mic, voiceState } = useVoice()
  const MicIcon = mic === 'off' || mic === 'error' ? MicOff : Mic
  const micText =
    mic === 'error'
      ? 'Voz con error'
      : mic === 'off'
        ? 'Micrófono apagado'
        : mic === 'live'
          ? 'Escuchando'
          : voiceState?.wake_enabled === false
            ? 'Micrófono en espera'
            : 'Esperando "Jarvis"'
  const tone = TONES[state]
  const linkText = state === 'offline' && link in LINK_TEXT ? LINK_TEXT[link as keyof typeof LINK_TEXT] : null

  return (
    <div role="status" aria-live="polite" className="px-3 py-3 text-chassis-foreground">
      <div className="flex items-center gap-2 text-sm">
        <span aria-hidden="true" className={cn('size-2.5 shrink-0 rounded-full', LIGHT[tone])} />
        <span>{CHARACTER_STATE_LABELS[state]}</span>
      </div>
      <p className="mt-1 flex items-center gap-1.5 pl-[1.125rem] text-xs text-chassis-muted">
        <MicIcon aria-hidden="true" className="size-3 shrink-0" />
        {micText}
      </p>
      {linkText && <p className="mt-1 pl-[1.125rem] text-xs text-chassis-muted">{linkText}</p>}
      {link === 'disconnected' && (
        <button
          type="button"
          onClick={() => void retryBackendLink()}
          className="mt-1.5 ml-[1.125rem] rounded border border-chassis-line px-2 py-0.5 text-xs text-chassis-foreground hover:bg-chassis-raised focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-chassis-foreground"
        >
          Reintentar conexión
        </button>
      )}
    </div>
  )
}
