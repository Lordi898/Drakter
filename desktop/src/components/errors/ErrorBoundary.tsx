import type { ReactNode } from 'react'

export interface ErrorBoundaryProps {
  /** Nombre de la zona protegida; aparece en el aviso y en el registro. */
  readonly scope: string
  /** Al cambiar, se limpia el error (por ejemplo, al navegar de sección). */
  readonly resetKey?: string
  readonly children: ReactNode
}

// Stub: lo sustituye la pieza de errores.
export function ErrorBoundary({ children }: ErrorBoundaryProps) {
  return <>{children}</>
}
