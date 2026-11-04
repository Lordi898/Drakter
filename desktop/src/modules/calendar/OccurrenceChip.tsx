import { TriangleAlert } from 'lucide-react'
import { cn } from '@/lib/utils'
import { timeText } from './dateUtils'
import { KIND_STYLES } from './kinds'
import { normalizeKind, type AgendaItem } from './types'

export interface OccurrenceChipProps {
  readonly item: AgendaItem
  readonly overlapping: boolean
  readonly showTime?: boolean
  readonly className?: string
  readonly style?: React.CSSProperties
  readonly onSelect: (item: AgendaItem) => void
}

export function OccurrenceChip({ item, overlapping, showTime = true, className, style, onSelect }: OccurrenceChipProps) {
  const kind = normalizeKind(item.kind)
  const styles = KIND_STYLES[kind]
  const cancelled = item.status === 'cancelled' || item.status === 'skipped'
  const time = !item.all_day && item.display_start && item.display_end ? `${timeText(item.display_start)}–${timeText(item.display_end)}` : 'Todo el día'
  const label = `${styles.label}: ${item.title}, ${time}${overlapping ? ', se solapa con otro elemento' : ''}${cancelled ? ', cancelado' : ''}`
  return (
    <button
      type="button"
      aria-label={label}
      onClick={(e) => {
        e.stopPropagation()
        onSelect(item)
      }}
      style={{ ...style, ...(item.color && kind === 'class' ? { borderLeftColor: item.color, borderLeftWidth: 4 } : {}) }}
      className={cn(
        'flex min-w-0 flex-col items-start overflow-hidden rounded-sm border px-1.5 py-0.5 text-left text-xs leading-tight outline-none focus-visible:ring-[3px] focus-visible:ring-ring/60',
        styles.chip,
        overlapping && 'ring-1 ring-warning',
        cancelled && 'opacity-60 line-through',
        className
      )}
    >
      <span className="flex w-full items-center gap-1">
        {overlapping ? <TriangleAlert className="size-3 shrink-0 text-warning" aria-hidden="true" /> : null}
        <span className="truncate font-medium">{item.title}</span>
      </span>
      {showTime ? <span className="truncate text-[11px] text-muted-foreground">{time}</span> : null}
    </button>
  )
}
