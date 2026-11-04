import { Mic } from 'lucide-react'
import { CharacterSlot } from '@/character/CharacterSlot'
import type { CharacterState } from '@/character/types'
import { ChatComposer } from '@/chat/ChatComposer'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { navigateTo } from '@/navigation/route'
import { getSection, type SectionId } from '@/navigation/sections'
import { useDrakterState } from '@/stores/agent'

const DRAKTER_SAYS: Record<CharacterState, string> = {
  idle: 'Estoy aquí. Dime qué necesitas.',
  listening: 'Te estoy escuchando.',
  thinking: 'Estoy pensando.',
  speaking: 'Te estoy respondiendo.',
  executing: 'Estoy trabajando en ello.',
  success: 'Ya lo he hecho.',
  error: 'No he podido terminarlo.',
  interrupted: 'Me he detenido.',
  offline: 'Todavía no estoy conectado.'
}

const QUICK_LINKS: readonly SectionId[] = ['tasks', 'calendar', 'habits']

function MicrophoneButton() {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          {/* aria-disabled en lugar de disabled: así el aviso también llega con el teclado. */}
          <Button
            type="button"
            variant="outline"
            size="icon"
            aria-label="Micrófono"
            aria-disabled="true"
            className="cursor-not-allowed opacity-50 hover:bg-background hover:text-foreground dark:hover:bg-input/30"
          >
            <Mic aria-hidden="true" />
          </Button>
        </TooltipTrigger>
        <TooltipContent>La voz llegará cuando Drakter esté conectado</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

export function HomePage() {
  const state = useDrakterState()

  return (
    <div className="@container flex min-h-full flex-col gap-8">
      <div className="grid flex-1 grid-cols-[minmax(0,2fr)_minmax(0,3fr)] items-center gap-10">
        <div className="flex justify-center">
          <CharacterSlot state={state} size="expanded" />
        </div>

        <div>
          {/* Sin .type-display: su corte de letra anularía el casual de .voice-drakter. */}
          <h1 className="voice-drakter text-4xl leading-[1.08] font-extrabold tracking-tight text-foreground @4xl:text-5xl @5xl:text-6xl">
            {DRAKTER_SAYS[state]}
          </h1>
          {state === 'offline' ? (
            <p className="mt-4 max-w-[48ch] text-muted-foreground">
              Cuando Drakter esté conectado, podrás hablar con él aquí, por escrito o por voz.
            </p>
          ) : null}

          <p className="mt-8 max-w-[48ch] text-sm text-muted-foreground">
            El resumen del día y la actividad reciente aparecerán aquí cuando el espacio de trabajo esté conectado.
          </p>
          <nav aria-label="Accesos rápidos" className="mt-3">
            <ul className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
              {QUICK_LINKS.map((id) => (
                <li key={id}>
                  <button
                    type="button"
                    onClick={() => navigateTo(id)}
                    className="cursor-pointer rounded-sm text-foreground underline underline-offset-4 hover:no-underline"
                  >
                    {getSection(id).label}
                  </button>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </div>

      <div className="flex items-end gap-2">
        <ChatComposer className="min-w-0 flex-1" />
        <MicrophoneButton />
      </div>
    </div>
  )
}
