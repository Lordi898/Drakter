import type { ReactNode } from 'react'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'
import { addDays, minutesToText } from './dateUtils'
import { ApiError, errorText, isBackendUnavailable } from './workspaceApi'

export const inputClass =
  'h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm shadow-xs outline-none transition-[color,box-shadow] placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive dark:bg-input/30'

export function Field({ id, label, hint, error, className, children }: {
  readonly id: string
  readonly label: string
  readonly hint?: string
  readonly error?: string | null
  readonly className?: string
  readonly children: ReactNode
}) {
  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <Label htmlFor={id}>{label}</Label>
      {children}
      {hint && !error ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
      {error ? (
        <p id={`${id}-error`} role="alert" className="text-xs text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  )
}

export interface DraftRange {
  startDate: string
  startTime: string
  endDate: string
  endTime: string
}

/** Rango inicial de una hora desde `minutes` del día `day`. */
export function defaultRange(day: string, minutes: number): DraftRange {
  const end = minutes + 60
  return {
    startDate: day,
    startTime: minutesToText(minutes),
    endDate: end >= 1440 ? addDays(day, 1) : day,
    endTime: minutesToText(end % 1440)
  }
}

export const localIso = (date: string, time: string): string => `${date}T${time.slice(0, 5)}`

export interface FormFailure {
  readonly message: string
  /** La hora local no existe en la zona (salto de horario de verano). */
  readonly nonexistentTime: boolean
}

export function describeFailure(error: unknown, timezone: string): FormFailure {
  if (error instanceof ApiError && error.code === 'nonexistent_local_time') {
    return {
      nonexistentTime: true,
      message: `Esa hora local no existe en ${timezone} (cambio de horario). Elige otra hora.`
    }
  }
  if (isBackendUnavailable(error)) {
    return { nonexistentTime: false, message: 'El espacio de trabajo no está conectado. No se ha guardado nada.' }
  }
  return { nonexistentTime: false, message: errorText(error) }
}
