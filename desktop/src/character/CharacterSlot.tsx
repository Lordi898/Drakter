import { ErrorBoundary } from '@/components/errors/ErrorBoundary'
import { cn } from '@/lib/utils'
import { characterRenderer as Renderer } from './plug'
import type { CharacterRendererProps, CharacterSize, CharacterState } from './types'

const SIZE_CLASSES: Record<CharacterSize, string> = {
  compact: 'size-[120px] shrink-0',
  expanded: 'aspect-square w-full max-w-[360px]'
}

const STATE_LABELS: Record<CharacterState, string> = {
  idle: 'en reposo',
  listening: 'escuchando',
  thinking: 'pensando',
  speaking: 'hablando',
  executing: 'ejecutando',
  success: 'éxito',
  error: 'error',
  interrupted: 'interrumpido',
  offline: 'sin conexión'
}

// Extensiones y marcas oblicuas de las dos cotas del contorno.
const DIMENSION_LINES = [
  'M12 20H46M12 308H46M20 20V308M14 26L26 14M14 314L26 302',
  'M52 314V348M340 314V348M52 340H340M46 346L58 334M334 346L346 334'
].join('')

/** Hueco de plano a la espera del personaje real: a propósito no dibuja ninguna figura. */
function EmptyFrame() {
  return (
    <svg
      viewBox="0 0 360 360"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.25"
      aria-hidden="true"
      className="size-full"
    >
      <rect
        x="52"
        y="20"
        width="288"
        height="288"
        rx="10"
        strokeDasharray="9 7"
        vectorEffect="non-scaling-stroke"
      />
      <path d={DIMENSION_LINES} vectorEffect="non-scaling-stroke" />
      <path d="M186 164H206M196 154V174" vectorEffect="non-scaling-stroke" />
    </svg>
  )
}

export function CharacterSlot({ state, size }: CharacterRendererProps) {
  return (
    <div
      role="img"
      aria-label={`Personaje de Drakter: ${STATE_LABELS[state]}`}
      data-character-state={state}
      data-character-size={size}
      className={cn('text-plan-line', SIZE_CLASSES[size])}
    >
      {Renderer ? (
        <ErrorBoundary scope="personaje">
          <Renderer state={state} size={size} />
        </ErrorBoundary>
      ) : (
        <EmptyFrame />
      )}
    </div>
  )
}
