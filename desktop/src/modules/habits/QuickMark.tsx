import { Check, Minus, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { STATUS_ACTIVE_CLASS, STATUS_LABEL, STATUS_ORDER } from './status'
import type { RecordStatus } from './types'

const ICON = { done: Check, skipped: Minus, missed: X } as const

export interface QuickMarkProps {
  readonly current: RecordStatus | null
  readonly disabled?: boolean
  readonly busy?: boolean
  readonly label: string
  readonly onMark: (status: RecordStatus) => void
}

/** Tres botones con estado pulsado; el color nunca es la única señal (icono + texto). */
export function QuickMark({ current, disabled, busy, label, onMark }: QuickMarkProps) {
  return (
    <div role="group" aria-label={label} className="flex items-center gap-1.5">
      {STATUS_ORDER.map((status) => {
        const Icon = ICON[status]
        const active = current === status
        return (
          <Button
            key={status}
            type="button"
            size="sm"
            variant="outline"
            aria-pressed={active}
            disabled={disabled || busy}
            onClick={() => onMark(status)}
            className={cn(active && STATUS_ACTIVE_CLASS[status])}
          >
            <Icon aria-hidden="true" />
            {STATUS_LABEL[status]}
          </Button>
        )
      })}
    </div>
  )
}
