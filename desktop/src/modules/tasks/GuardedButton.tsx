import { useId, type ComponentProps } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export interface GuardedButtonProps extends ComponentProps<typeof Button> {
  /** Si existe, el botón no está disponible y este es el motivo (se anuncia con `aria-describedby`). */
  readonly unavailableReason?: string | null
}

/** Botón no disponible pero enfocable: `aria-disabled` + motivo, en vez de `disabled`. */
export function GuardedButton({ unavailableReason, onClick, className, children, ...props }: GuardedButtonProps) {
  const reasonId = useId()
  const blocked = unavailableReason !== undefined && unavailableReason !== null
  return (
    <>
      <Button
        {...props}
        aria-disabled={blocked ? true : undefined}
        aria-describedby={blocked ? reasonId : props['aria-describedby']}
        title={blocked ? unavailableReason : props.title}
        className={cn(blocked && 'cursor-not-allowed opacity-50', className)}
        onClick={blocked ? (event) => event.preventDefault() : onClick}
      >
        {children}
      </Button>
      {blocked ? (
        <span id={reasonId} className="sr-only">
          {unavailableReason}
        </span>
      ) : null}
    </>
  )
}
