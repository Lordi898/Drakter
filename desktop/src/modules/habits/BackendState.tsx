import { Button } from '@/components/ui/button'
import { errorText, isBackendUnavailable } from '@/modules/calendar/workspaceApi'

export function BackendState({ error, onRetry }: { readonly error: unknown; readonly onRetry: () => void }) {
  const offline = isBackendUnavailable(error)
  return (
    <section role="alert" className="flex max-w-xl flex-col items-start gap-3">
      <h2 className="text-xl font-semibold text-foreground">
        {offline ? 'El espacio de trabajo no está conectado' : 'No se pudieron cargar los datos'}
      </h2>
      <p className="max-w-[60ch] text-muted-foreground">
        {offline ? 'No hay conexión con el backend, así que no se muestran hábitos. Reintenta cuando esté en marcha.' : errorText(error)}
      </p>
      <Button type="button" variant="outline" onClick={onRetry}>
        Reintentar
      </Button>
    </section>
  )
}
