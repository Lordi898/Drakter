import { ModeRoot } from '@/app/ModeRoot'
import { SessionHosts } from '@/app/SessionHosts'
import { useDocumentPreferences } from '@/app/useDocumentPreferences'
import { ConfirmationHost } from '@/chat/ConfirmationDialog'
import { ErrorBoundary } from '@/components/errors/ErrorBoundary'
import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { installGlobalErrorHandlers } from '@/services/errors'

installGlobalErrorHandlers()

export function App() {
  useDocumentPreferences()

  return (
    <ErrorBoundary scope="aplicación">
      <TooltipProvider delayDuration={500}>
        <SessionHosts />
        <ModeRoot />
        {/* Común a los dos modos: una confirmación puede llegar estando en Jarvis. */}
        <ConfirmationHost />
        <Toaster position="bottom-right" />
      </TooltipProvider>
    </ErrorBoundary>
  )
}
