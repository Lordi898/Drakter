import { Volume2, VolumeX } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import { setTtsEnabled, useVoice, type VoiceSnapshot } from '@/stores/voice'

const MIC_LABEL: Record<VoiceSnapshot['mic'], string> = {
  off: 'Micrófono apagado',
  standby: 'Esperando la palabra de activación',
  live: 'Escuchando',
  error: 'Voz con error'
}
const MIC_DOT: Record<VoiceSnapshot['mic'], string> = {
  off: 'border border-muted-foreground',
  standby: 'bg-muted-foreground',
  live: 'bg-ambar',
  error: 'bg-destructive'
}

/** Altavoz (leer respuestas en voz alta) y punto con el estado del micrófono. */
export function SpeakerToggle() {
  const { ttsEnabled, mic } = useVoice()
  const Icon = ttsEnabled ? Volume2 : VolumeX

  return (
    <div className="flex items-center gap-1.5 self-end">
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-pressed={ttsEnabled}
            aria-label="Leer respuestas en voz alta"
            onClick={() => void setTtsEnabled(!ttsEnabled)}
          >
            <Icon aria-hidden="true" className={cn(!ttsEnabled && 'text-muted-foreground')} />
          </Button>
        </TooltipTrigger>
        <TooltipContent side="top" sideOffset={6}>
          {ttsEnabled ? 'Leer respuestas en voz alta: activado' : 'Leer respuestas en voz alta: desactivado'}
        </TooltipContent>
      </Tooltip>
      <Tooltip>
        <TooltipTrigger asChild>
          <span role="img" aria-label={MIC_LABEL[mic]} tabIndex={0} className="flex size-4 items-center justify-center">
            <span aria-hidden="true" className={cn('size-1.5 rounded-full', MIC_DOT[mic])} />
          </span>
        </TooltipTrigger>
        <TooltipContent side="top" sideOffset={6}>
          {MIC_LABEL[mic]}
        </TooltipContent>
      </Tooltip>
    </div>
  )
}
