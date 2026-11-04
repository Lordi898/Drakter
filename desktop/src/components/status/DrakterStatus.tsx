import type { CharacterState } from '@/character/types'
import { useDrakterState } from '@/stores/agent'
import { cn } from '@/lib/utils'

type Tone = 'active' | 'off' | 'error'

const STATUS: Record<CharacterState, { label: string; tone: Tone }> = {
  idle: { label: 'Disponible', tone: 'active' },
  listening: { label: 'Escuchando', tone: 'active' },
  thinking: { label: 'Pensando', tone: 'active' },
  speaking: { label: 'Hablando', tone: 'active' },
  executing: { label: 'Trabajando', tone: 'active' },
  success: { label: 'Hecho', tone: 'active' },
  error: { label: 'Con un error', tone: 'error' },
  interrupted: { label: 'Interrumpido', tone: 'active' },
  offline: { label: 'Desconectado', tone: 'off' }
}

const LIGHT: Record<Tone, string> = {
  active: 'bg-ambar',
  off: 'border border-chassis-muted',
  error: 'bg-destructive'
}

export function DrakterStatus() {
  const state = useDrakterState()
  const { label, tone } = STATUS[state]

  return (
    <div role="status" className="px-3 py-3 text-chassis-foreground">
      <div className="flex items-center gap-2 text-sm">
        <span aria-hidden="true" className={cn('size-2.5 shrink-0 rounded-full', LIGHT[tone])} />
        <span>{label}</span>
      </div>
      {state === 'offline' && <p className="mt-1 pl-[1.125rem] text-xs text-chassis-muted">Aún no está conectado</p>}
    </div>
  )
}
