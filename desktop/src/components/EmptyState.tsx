import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export interface EmptyStateProps {
  readonly title: string
  readonly description: string
  /** SVG propio del módulo: plano a línea con `stroke="currentColor"`. */
  readonly drawing?: ReactNode
  /** Acción que existirá; va deshabilitada con el motivo real mientras no haya backend. */
  readonly pendingAction?: { readonly label: string; readonly reason: string }
  readonly className?: string
}

/** Estado vacío honesto: dice qué habrá aquí y por qué aún no lo hay. Nunca muestra datos de ejemplo. */
export function EmptyState({ title, description, drawing, pendingAction, className }: EmptyStateProps) {
  return (
    <section className={cn('flex max-w-xl flex-col items-start gap-4', className)}>
      {drawing ? (
        <div className="text-plan-line" aria-hidden="true">
          {drawing}
        </div>
      ) : null}
      <h2 className="text-xl font-semibold text-foreground">{title}</h2>
      <p className="max-w-[60ch] text-muted-foreground">{description}</p>
      {pendingAction ? (
        <div className="flex flex-wrap items-center gap-3">
          <Button disabled>{pendingAction.label}</Button>
          <span className="text-sm text-muted-foreground">{pendingAction.reason}</span>
        </div>
      ) : null}
    </section>
  )
}
