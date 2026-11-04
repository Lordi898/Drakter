import { Component, type ErrorInfo, type ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { reportError } from '@/services/errors'

export interface ErrorBoundaryProps {
  /** Nombre de la zona protegida; aparece en el aviso y en el registro. */
  readonly scope: string
  /** Al cambiar, se limpia el error (por ejemplo, al navegar de sección). */
  readonly resetKey?: string
  readonly children: ReactNode
}

interface ErrorBoundaryState {
  readonly error: Error | null
}

function toError(value: unknown): Error {
  return value instanceof Error ? value : new Error(String(value))
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  override state: ErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: unknown): ErrorBoundaryState {
    return { error: toError(error) }
  }

  override componentDidCatch(error: unknown, _info: ErrorInfo): void {
    reportError(this.props.scope, error)
  }

  override componentDidUpdate(prev: ErrorBoundaryProps): void {
    if (prev.resetKey !== this.props.resetKey && this.state.error) {
      this.setState({ error: null })
    }
  }

  private readonly reset = (): void => {
    this.setState({ error: null })
  }

  override render(): ReactNode {
    const { error } = this.state
    if (!error) return this.props.children

    const detail = (
      <details className="mt-4 text-sm">
        <summary className="cursor-pointer rounded-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">
          Detalle técnico
        </summary>
        <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap break-words text-xs opacity-80">
          {error.message}
        </pre>
      </details>
    )

    if (this.props.scope === 'aplicación') {
      return (
        <div
          role="alert"
          className="flex h-screen w-screen items-center justify-center bg-chassis p-8 text-chassis-foreground"
        >
          <div className="max-w-md">
            <h1 className="type-display text-3xl">Drakter ha tenido un error</h1>
            <p className="mt-3 text-chassis-muted">
              La aplicación no puede seguir en este estado. Recárgala para continuar.
            </p>
            <Button type="button" className="mt-5" onClick={() => window.location.reload()}>
              Recargar
            </Button>
            {detail}
          </div>
        </div>
      )
    }

    return (
      <div role="alert" className="flex h-full w-full items-center justify-center p-8">
        <div className="max-w-md">
          <h2 className="type-display text-2xl">Esta sección ha fallado</h2>
          <p className="mt-3 text-muted-foreground">
            El resto de la aplicación sigue funcionando. Puedes reintentar o ir a otra sección.
          </p>
          <Button type="button" variant="outline" className="mt-5" onClick={this.reset}>
            Reintentar
          </Button>
          {detail}
        </div>
      </div>
    )
  }
}
