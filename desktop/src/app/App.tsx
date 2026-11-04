import { AppShell } from '@/app/AppShell'
import { useDocumentPreferences } from '@/app/useDocumentPreferences'
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
        <AppShell />
        <Toaster position="bottom-right" />
      </TooltipProvider>
    </ErrorBoundary>
  )
}
