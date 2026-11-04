import { useEffect, useState } from 'react'
import { AlertTriangle, Bell, CheckCircle2, Info, OctagonAlert, type LucideIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { ScrollArea } from '@/components/ui/scroll-area'
import { RemindersNotice } from '@/modules/notifications'
import {
  clearNotifications,
  markAllNotificationsRead,
  useNotifications,
  type NotificationTone
} from '@/stores/notifications'

const toneStyle: Record<NotificationTone, { icon: LucideIcon; className: string }> = {
  info: { icon: Info, className: 'text-plan-line' },
  success: { icon: CheckCircle2, className: 'text-success' },
  warning: { icon: AlertTriangle, className: 'text-warning' },
  error: { icon: OctagonAlert, className: 'text-destructive' }
}

const relativeFormat = new Intl.RelativeTimeFormat('es', { numeric: 'auto' })

function relativeTime(date: Date, now: number): string {
  const seconds = Math.round((date.getTime() - now) / 1000)
  const abs = Math.abs(seconds)
  if (abs < 60) return relativeFormat.format(0, 'second')
  if (abs < 3600) return relativeFormat.format(Math.round(seconds / 60), 'minute')
  if (abs < 86400) return relativeFormat.format(Math.round(seconds / 3600), 'hour')
  return relativeFormat.format(Math.round(seconds / 86400), 'day')
}

export function NotificationCenter() {
  const notifications = useNotifications()
  const [open, setOpen] = useState(false)
  const [now, setNow] = useState(() => Date.now())
  const unread = notifications.filter((item) => !item.read).length

  useEffect(() => {
    if (!open) return
    setNow(Date.now())
    markAllNotificationsRead()
  }, [open, notifications.length])

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon-sm"
          className="relative"
          aria-label={unread === 0 ? 'Notificaciones' : `Notificaciones, ${unread} sin leer`}
        >
          <Bell aria-hidden />
          {unread > 0 && (
            <span aria-hidden className="absolute right-1.5 top-1.5 size-2 rounded-full bg-primary" />
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 p-0">
        <div className="flex items-center justify-between border-b border-border px-3 py-2">
          <h2 className="text-sm font-medium">Notificaciones</h2>
          {notifications.length > 0 && (
            <Button variant="ghost" size="xs" onClick={clearNotifications}>
              Vaciar
            </Button>
          )}
        </div>
        {notifications.length === 0 ? (
          <p className="px-3 py-6 text-sm text-muted-foreground">Sin notificaciones.</p>
        ) : (
          <ScrollArea className="max-h-80 overflow-y-auto">
            <ul className="divide-y divide-border">
              {notifications.map((item) => {
                const { icon: Icon, className } = toneStyle[item.tone]
                return (
                  <li key={item.id} className="flex gap-2.5 px-3 py-2.5">
                    <Icon aria-hidden className={`mt-0.5 size-4 shrink-0 ${className}`} />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium">{item.title}</p>
                      {item.body !== undefined && (
                        <p className="text-sm text-muted-foreground">{item.body}</p>
                      )}
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {relativeTime(item.createdAt, now)}
                      </p>
                    </div>
                  </li>
                )
              })}
            </ul>
          </ScrollArea>
        )}
        <div className="border-t border-border p-2">
          <RemindersNotice compact />
        </div>
      </PopoverContent>
    </Popover>
  )
}
