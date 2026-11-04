import type { ReactNode } from 'react'

export interface PageHeaderProps {
  readonly title: string
  readonly summary: string
  readonly actions?: ReactNode
}

export function PageHeader({ title, summary, actions }: PageHeaderProps) {
  return (
    <header className="flex items-end justify-between gap-6 pb-8">
      <div>
        <h1 className="type-display text-4xl text-foreground">{title}</h1>
        <p className="mt-2 max-w-[60ch] text-muted-foreground">{summary}</p>
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </header>
  )
}
