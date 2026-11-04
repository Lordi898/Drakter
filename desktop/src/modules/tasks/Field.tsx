import { useId, type ComponentProps, type ReactNode } from 'react'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'

export interface FieldControlProps {
  readonly id: string
  readonly 'aria-describedby': string | undefined
  readonly 'aria-invalid': true | undefined
}

export interface FieldProps {
  readonly label: string
  readonly hint?: string
  readonly error?: string | null
  readonly className?: string
  /** Recibe los atributos que asocian la etiqueta, la ayuda y el error al control. */
  readonly children: (control: FieldControlProps) => ReactNode
}

/** Etiqueta + control + ayuda/error, con los `aria-*` ya conectados. */
export function Field({ label, hint, error, className, children }: FieldProps) {
  const id = useId()
  const hintId = `${id}-hint`
  const errorId = `${id}-error`
  const describedBy = [hint ? hintId : null, error ? errorId : null].filter(Boolean).join(' ')
  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <Label htmlFor={id}>{label}</Label>
      {children({
        id,
        'aria-describedby': describedBy === '' ? undefined : describedBy,
        'aria-invalid': error ? true : undefined
      })}
      {hint ? (
        <p id={hintId} className="text-xs text-muted-foreground">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} role="alert" className="text-xs text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  )
}

/** Input nativo con los tokens de la hoja; no existe `components/ui/input`. */
export function TextInput({ className, type = 'text', ...props }: ComponentProps<'input'>) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        'flex h-9 w-full min-w-0 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-[color,box-shadow] outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:bg-input/30 dark:aria-invalid:ring-destructive/40',
        className
      )}
      {...props}
    />
  )
}
