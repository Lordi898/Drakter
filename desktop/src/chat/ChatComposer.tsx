import { SendHorizontal } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { useDrakterState } from '@/stores/agent'

const SEND_WIRED = false
const OFFLINE_NOTICE = 'Drakter aún no está conectado. Podrás escribirle desde aquí.'

export function ChatComposer({ className }: { className?: string }) {
  const offline = useDrakterState() === 'offline'
  // TODO envío: el equipo de comunicación conectará aquí el envío; hasta entonces queda deshabilitado también con conexión.
  const disabled = offline || !SEND_WIRED

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      <p id="chat-notice" className="text-sm text-muted-foreground">
        {OFFLINE_NOTICE}
      </p>
      <div className="flex items-end gap-2">
        <Textarea
          rows={1}
          disabled={disabled}
          aria-label="Mensaje para Drakter"
          aria-describedby="chat-notice"
          placeholder="Escribe un mensaje"
          className="min-h-9 max-h-28 resize-none py-1.5"
        />
        <Button type="submit" disabled={disabled}>
          <SendHorizontal aria-hidden="true" />
          Enviar
        </Button>
      </div>
    </div>
  )
}
