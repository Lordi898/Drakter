import { useCallback, useEffect, useId, useState, type ReactNode } from 'react'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'

interface SettingRowProps {
  readonly title: string
  readonly description?: string
  readonly labelFor?: string
  /** Si es función, recibe el id de la descripción para enlazarlo con `aria-describedby`. */
  readonly children?: ReactNode | ((describedBy: string | undefined) => ReactNode)
}

export function SettingRow({ title, description, labelFor, children }: SettingRowProps) {
  const descriptionId = useId()
  const describedBy = description ? descriptionId : undefined
  const content = typeof children === 'function' ? children(describedBy) : children
  return (
    <div className="flex items-center justify-between gap-6 py-4">
      <div className="min-w-0">
        {labelFor ? (
          <Label htmlFor={labelFor} className="text-base">
            {title}
          </Label>
        ) : (
          <p className="text-base font-medium text-foreground">{title}</p>
        )}
        {description ? (
          <p id={descriptionId} className="mt-1 text-sm text-muted-foreground">
            {description}
          </p>
        ) : null}
      </div>
      {content ? <div className="flex shrink-0 items-center">{content}</div> : null}
    </div>
  )
}

export function Section({ title, children }: { readonly title: string; readonly children: ReactNode }) {
  return (
    <section className="pb-8">
      <h2 className="pb-2 text-lg font-semibold text-foreground">{title}</h2>
      <Separator />
      {children}
    </section>
  )
}

export function Rows({ children }: { readonly children: ReactNode }) {
  const items = (Array.isArray(children) ? children : [children]).filter(
    (child) => child !== null && child !== undefined && child !== false
  )
  return (
    <div>
      {items.map((child, index) => (
        <div key={index}>
          {index > 0 ? <Separator /> : null}
          {child}
        </div>
      ))}
    </div>
  )
}

export type Loadable<T> =
  | { readonly status: 'loading' }
  | { readonly status: 'error'; readonly error: unknown }
  | { readonly status: 'ready'; readonly data: T }

/** Carga una vez al montar; descarta respuestas obsoletas al desmontar o recargar. */
export function useLoad<T>(load: () => Promise<T>): readonly [Loadable<T>, () => void, (data: T) => void] {
  const [state, setState] = useState<Loadable<T>>({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    load()
      .then((data) => {
        if (!cancelled) setState({ status: 'ready', data })
      })
      .catch((error: unknown) => {
        if (!cancelled) setState({ status: 'error', error })
      })
    return () => {
      cancelled = true
    }
    // `load` es una función de módulo estable.
  }, [load, attempt])

  const reload = useCallback(() => {
    setState({ status: 'loading' })
    setAttempt((n) => n + 1)
  }, [])
  const set = useCallback((data: T) => setState({ status: 'ready', data }), [])
  return [state, reload, set]
}
