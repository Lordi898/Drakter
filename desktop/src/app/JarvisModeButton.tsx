import { Radar } from 'lucide-react'
import { UI_MODE_SHORTCUT, UI_MODE_SHORTCUT_LABEL } from '@/app/useGlobalShortcuts'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { jarvisAvailable, prefetchJarvis, requestUiMode } from '@/stores/uiMode'

/** Recibe el foco al volver de Jarvis. */
export const UI_MODE_BUTTON_ID = 'ui-mode-toggle'

const LABEL = 'Modo Jarvis'

/** Botón de la cabecera de Drakter. Pasar por encima o enfocarlo ya precarga el chunk de Jarvis. */
export function JarvisModeButton() {
  if (!jarvisAvailable()) return null
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          id={UI_MODE_BUTTON_ID}
          variant="ghost"
          size="icon-sm"
          aria-label={LABEL}
          aria-keyshortcuts={UI_MODE_SHORTCUT}
          onPointerEnter={prefetchJarvis}
          onFocus={prefetchJarvis}
          onClick={() => requestUiMode('jarvis', 'button')}
        >
          <Radar aria-hidden="true" />
        </Button>
      </TooltipTrigger>
      <TooltipContent side="bottom" sideOffset={6}>
        {LABEL} ({UI_MODE_SHORTCUT_LABEL})
      </TooltipContent>
    </Tooltip>
  )
}
