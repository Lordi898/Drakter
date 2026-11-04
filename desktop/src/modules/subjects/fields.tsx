import type { ComponentProps } from 'react'
import { cn } from '@/lib/utils'

export const inputClass =
  'h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:opacity-50 aria-invalid:border-destructive'

export function TextInput({ className, ...props }: ComponentProps<'input'>) {
  return <input className={cn(inputClass, className)} {...props} />
}

export function Field({ label, htmlFor, hint, children }: {
  readonly label: string
  readonly htmlFor?: string
  readonly hint?: string
  readonly children: React.ReactNode
}) {
  return (
    <div className="grid gap-1.5">
      <label htmlFor={htmlFor} className="text-sm font-medium text-foreground">
        {label}
      </label>
      {children}
      {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  )
}

export function FormError({ message }: { readonly message: string | null }) {
  if (!message) return null
  return (
    <p role="alert" className="rounded-md border border-destructive/50 px-3 py-2 text-sm text-destructive">
      {message}
    </p>
  )
}
