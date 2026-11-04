import { useEffect, useState } from 'react'
import { BellRing, TriangleAlert } from 'lucide-react'
import { cn } from '@/lib/utils'
import { parseStatus } from './parse'
import type { NotificationCall, NotificationsStatus } from './types'

const FIXED_TEXT = 'Los recordatorios solo funcionan con Drakter abierto. Con la app cerrada no recibirás avisos.'

export interface RemindersNoticeProps {
  readonly call: NotificationCall
  readonly compact?: boolean
}

export function RemindersNotice({ call, compact = false }: RemindersNoticeProps): React.JSX.Element {
  const [status, setStatus] = useState<NotificationsStatus | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    call('notifications.status')
      .then((raw) => {
        if (cancelled) return
        const parsed = parseStatus(raw)
        setStatus(parsed)
        setFailed(parsed === null)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })
    return () => {
      cancelled = true
    }
  }, [call])

  const stopped = failed || (status !== null && (!status.running || status.last_error !== null))
  const Icon = stopped ? TriangleAlert : BellRing

  return (
    <div
      role="status"
      className={cn(
        'flex items-start gap-3 rounded-lg border bg-card text-sm',
        compact ? 'p-2' : 'p-3',
        stopped ? 'border-warning/50 text-warning' : 'border-border text-muted-foreground'
      )}
    >
      <Icon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <div className="space-y-1">
        {stopped ? <p className="font-medium">Los recordatorios están detenidos ahora mismo.</p> : null}
        <p>{FIXED_TEXT}</p>
        {status !== null && !failed ? <p>{`Al abrirla verás los de las últimas ${status.catch_up_hours} horas.`}</p> : null}
      </div>
    </div>
  )
}
