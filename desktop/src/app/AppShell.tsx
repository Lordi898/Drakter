import { lazy, Suspense, useEffect, useLayoutEffect, useRef, useSyncExternalStore, type ComponentType } from 'react'
import { PanelRightClose, PanelRightOpen } from 'lucide-react'
import { toggleContextPanel, useAppShortcuts } from '@/app/useAppShortcuts'
import { ChatDock } from '@/chat/ChatDock'
import { ConfirmationHost } from '@/chat/ConfirmationDialog'
import { ContextPanel } from '@/components/context/ContextPanel'
import { ErrorBoundary } from '@/components/errors/ErrorBoundary'
import { NotificationCenter } from '@/components/notifications/NotificationCenter'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import { startNotificationFeed } from '@/modules/notifications'
import { SearchPalette } from '@/modules/search'
import { PAGES } from '@/navigation/pages'
import { useCurrentSection } from '@/navigation/route'
import { Sidebar } from '@/navigation/Sidebar'
import { usePreferences } from '@/stores/preferences'

const CONTEXT_PANEL_ID = 'context-panel'

// VoiceHost lo aporta WP8a (src/voice/VoiceHost.tsx). Hasta la fusión el glob queda vacío y no se monta nada.
const voiceHostModules = import.meta.glob<{ VoiceHost: ComponentType }>('../voice/VoiceHost.tsx')
const voiceHostLoader = Object.values(voiceHostModules)[0]
const VoiceHost = voiceHostLoader
  ? lazy(async () => ({ default: (await voiceHostLoader()).VoiceHost }))
  : null

const wideWindow = window.matchMedia('(min-width: 1100px)')

function subscribeToWidth(listener: () => void): () => void {
  wideWindow.addEventListener('change', listener)
  return () => wideWindow.removeEventListener('change', listener)
}

function useWideWindow(): boolean {
  return useSyncExternalStore(subscribeToWidth, () => wideWindow.matches)
}

function ContextPanelToggle({ expanded }: { expanded: boolean }) {
  const label = expanded ? 'Ocultar panel de contexto' : 'Mostrar panel de contexto'
  const Icon = expanded ? PanelRightClose : PanelRightOpen

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label={label}
          aria-expanded={expanded}
          aria-controls={CONTEXT_PANEL_ID}
          aria-keyshortcuts="Control+\"
          onClick={toggleContextPanel}
        >
          <Icon aria-hidden="true" />
        </Button>
      </TooltipTrigger>
      <TooltipContent side="bottom" sideOffset={6}>
        {label} (Ctrl+\)
      </TooltipContent>
    </Tooltip>
  )
}

export function AppShell() {
  const section = useCurrentSection()
  const { contextPanelOpen } = usePreferences()
  const wide = useWideWindow()
  const panelVisible = wide && contextPanelOpen
  const scrollerRef = useRef<HTMLElement>(null)
  const Page = PAGES[section]

  useAppShortcuts(wide)

  useEffect(() => startNotificationFeed(), [])

  useLayoutEffect(() => {
    scrollerRef.current?.scrollTo({ top: 0 })
  }, [section])

  return (
    <div
      className={cn(
        'grid h-full grid-rows-[minmax(0,1fr)] bg-chassis transition-[grid-template-columns] duration-150 ease-out',
        panelVisible ? 'grid-cols-[212px_minmax(0,1fr)_288px]' : 'grid-cols-[212px_minmax(0,1fr)_0px]'
      )}
    >
      <Sidebar current={section} />

      <div
        className={cn(
          'my-2.5 flex min-h-0 min-w-0 flex-col overflow-hidden rounded-sheet bg-background text-foreground transition-[margin] duration-150 ease-out',
          !panelVisible && 'mr-2.5'
        )}
      >
        <header className="flex shrink-0 items-center justify-end gap-1 px-3 pt-2.5">
          <NotificationCenter />
          {wide && <ContextPanelToggle expanded={contextPanelOpen} />}
        </header>

        <main ref={scrollerRef} className="min-h-0 flex-1 overflow-y-auto px-10 py-8">
          <ErrorBoundary scope={section} resetKey={section}>
            <Page />
          </ErrorBoundary>
        </main>

        {/*
          px-6 más el px-4 propio del dock alinean el mensaje con los 40px de la página.
          Además retira su filete del borde: la pestaña de Configuración se une a la hoja
          a esa altura y una línea que llegara hasta allí cortaría la pieza de papel.
        */}
        {section !== 'home' && (
          <div className="shrink-0 px-6">
            <ChatDock />
          </div>
        )}
      </div>

      {/* Ancho fijo por dentro: el panel se recorta al plegarse en vez de recomponer su texto. */}
      <div id={CONTEXT_PANEL_ID} inert={!panelVisible} className="min-h-0 overflow-hidden">
        <div className="h-full w-72">
          <ContextPanel />
        </div>
      </div>

      <SearchPalette />
      <ConfirmationHost />
      {VoiceHost ? (
        <Suspense fallback={null}>
          <VoiceHost />
        </Suspense>
      ) : null}
    </div>
  )
}
