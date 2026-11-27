import { LoaderCircle, PictureInPicture2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import { FLOATING_SHORTCUT, FLOATING_SHORTCUT_LABEL } from './shortcut'
import { requestFloating, useFloating, type FloatingSnapshot } from './store'

function describe({ state }: FloatingSnapshot): { readonly label: string; readonly hint: string } {
  if (!state) return { label: 'Modo flotante', hint: FLOATING_SHORTCUT_LABEL }
  if (state.busy === 'activating') return { label: 'Activando el modo flotante…', hint: '' }
  if (state.busy === 'deactivating') return { label: 'Quitando el modo flotante…', hint: '' }
  if (!state.available) return { label: 'Modo flotante no disponible', hint: 'ver cómo instalarlo' }
  if (state.active) return { label: 'Quitar el modo flotante', hint: 'Super+Alt+D' }
  return { label: 'Modo flotante', hint: FLOATING_SHORTCUT_LABEL }
}

/**
 * Botón del modo flotante. `drakter`: icono en la cabecera, como el del modo Jarvis. `jarvis`: botón
 * de los controles comunes de `JarvisShell` (vale para Núcleo, Holomesa y Visor); solo icono, para no
 * invadir la barra de las interfaces (Holomesa reserva 400 px a la derecha).
 */
export function FloatingButton({ variant }: { readonly variant: 'drakter' | 'jarvis' }) {
  const snapshot = useFloating()
  const { state } = snapshot
  const { label, hint } = describe(snapshot)
  const busy = state?.busy != null
  const active = state?.active === true
  const unavailable = state !== null && !state.available
  const Icon = busy ? LoaderCircle : PictureInPicture2
  const onClick = (): void => requestFloating('toggle')

  if (variant === 'jarvis') {
    return (
      <button
        type="button"
        aria-label={label}
        aria-pressed={active}
        aria-busy={busy}
        aria-keyshortcuts={FLOATING_SHORTCUT}
        title={hint ? `${label} (${hint})` : label}
        onClick={onClick}
        className={cn(
          'relative flex size-[30px] items-center justify-center rounded-md border outline-none focus-visible:ring-2 focus-visible:ring-sky-300',
          active
            ? 'border-sky-300/80 bg-sky-400/25 text-sky-50 shadow-[0_0_18px_rgba(56,189,248,0.35)]'
            : 'border-sky-400/40 bg-sky-950/60 text-sky-100 hover:bg-sky-900/60',
          unavailable && 'text-sky-100/70'
        )}
      >
        <Icon className={cn('size-4', busy && 'animate-spin')} aria-hidden="true" />
        {unavailable ? (
          <span className="absolute top-1 right-1 size-1.5 rounded-full bg-amber-300/90" aria-hidden="true" />
        ) : null}
      </button>
    )
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label={label}
          aria-pressed={active}
          aria-busy={busy}
          aria-keyshortcuts={FLOATING_SHORTCUT}
          onClick={onClick}
          className={cn('relative', active && 'bg-accent text-accent-foreground')}
        >
          <Icon className={cn(busy && 'animate-spin')} aria-hidden="true" />
          {unavailable ? (
            <span className="absolute top-1 right-1 size-1.5 rounded-full bg-amber-500" aria-hidden="true" />
          ) : null}
        </Button>
      </TooltipTrigger>
      <TooltipContent side="bottom" sideOffset={6}>
        {hint ? `${label} (${hint})` : label}
      </TooltipContent>
    </Tooltip>
  )
}
