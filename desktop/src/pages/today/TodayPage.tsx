import { RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { describeError } from '@/services/api'
import { dayNumberOf, monthOf, summaryPhrase, weekdayOf } from './format'
import { isDisconnected } from './requests'
import { TodaySections } from './TodaySections'
import { useToday } from './useToday'

const DISCONNECTED = 'El servicio local de Drakter no está conectado.'

function errorMessage(error: unknown): string {
  return isDisconnected(error) ? DISCONNECTED : describeError(error, 'No se pudo cargar el día.')
}

export function TodayPage() {
  const { data, error, loading, reload } = useToday()

  if (!data) {
    return (
      <div className="@container mx-auto w-full max-w-6xl" aria-live="polite">
        {loading ? (
          <p className="text-muted-foreground">Cargando tu día…</p>
        ) : (
          <div className="flex max-w-xl flex-col items-start gap-4">
            <h1 className="type-display text-3xl text-foreground">{errorMessage(error)}</h1>
            <Button variant="outline" onClick={reload}>
              Reintentar
            </Button>
          </div>
        )}
      </div>
    )
  }

  const phrase = summaryPhrase(data)
  return (
    <div className="@container mx-auto w-full max-w-6xl">
      <header className="flex items-start justify-between gap-6 pb-10">
        <div className="min-w-0">
          <h1 className="type-display text-foreground">
            <span className="block text-2xl font-light first-letter:uppercase @xl:text-3xl">
              {weekdayOf(data.date)}
            </span>
            <span className="block text-5xl @xl:text-6xl @3xl:text-7xl">
              {dayNumberOf(data.date)} {monthOf(data.date)}
            </span>
          </h1>
          {phrase ? <p className="mt-3 text-lg text-muted-foreground">{phrase}</p> : null}
        </div>
        <Button variant="ghost" size="sm" onClick={reload} className="shrink-0 text-muted-foreground">
          <RefreshCw aria-hidden="true" className={loading ? 'motion-safe:animate-spin' : undefined} />
          Actualizar
        </Button>
      </header>
      <div aria-live="polite" className="empty:hidden">
        {error ? (
          <p className="mb-6 flex flex-wrap items-center gap-3 text-destructive">
            {isDisconnected(error) ? `${DISCONNECTED} Se muestran los últimos datos.` : errorMessage(error)}
            <Button variant="outline" size="sm" onClick={reload}>
              Reintentar
            </Button>
          </p>
        ) : null}
      </div>
      <TodaySections data={data} />
    </div>
  )
}
