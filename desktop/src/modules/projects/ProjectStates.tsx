import { Button } from '@/components/ui/button'
import type { LoadError } from './useLoad'

export function LoadingNote({ label }: { readonly label: string }) {
  return (
    <p role="status" className="text-sm text-muted-foreground">
      {label}
    </p>
  )
}

/** Error honesto: dice qué pasó y deja reintentar. Nunca muestra datos inventados. */
export function LoadFailure({
  error,
  what,
  onRetry
}: {
  readonly error: LoadError
  readonly what: string
  readonly onRetry: () => void
}) {
  const offline = error.code === 'backend_unavailable'
  return (
    <div
      role="alert"
      className="flex max-w-xl flex-col items-start gap-3 rounded-[var(--radius-sheet)] border border-destructive/40 bg-card p-5"
    >
      <p className="font-medium text-foreground">
        {offline ? 'No hay conexión con el espacio de trabajo' : `No se pudo cargar ${what}`}
      </p>
      <p className="text-sm text-muted-foreground">{error.message}</p>
      <Button variant="outline" size="sm" onClick={onRetry}>
        Reintentar
      </Button>
    </div>
  )
}
