import { useState, type KeyboardEvent } from 'react'
import { SendHorizontal, Square } from 'lucide-react'
import { ChatTranscript } from '@/chat/ChatTranscript'
import { ConfirmationHost } from '@/chat/ConfirmationDialog'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { useDrakterState } from '@/stores/agent'
import { useLinkStatus, type LinkStatus } from '@/stores/connection'
import { MAX_MESSAGE_CHARS, cancelActiveTurn, sendMessage, useActiveTurn, useChatMessages } from '@/stores/chat'

const LINK_NOTICES: Readonly<Record<Exclude<LinkStatus, 'open'>, string>> = {
  idle: 'Conectando con Drakter…',
  connecting: 'Conectando con Drakter…',
  reconnecting: 'Reconectando con Drakter. Podrás escribirle en cuanto vuelva la conexión.',
  disconnected: 'Drakter no está conectado ahora. Podrás escribirle cuando vuelva la conexión.'
}
const TOO_LONG_NOTICE = `El mensaje supera el límite de ${MAX_MESSAGE_CHARS} caracteres.`
const SEND_FAILED_NOTICE = 'No se ha podido enviar el mensaje. Inténtalo de nuevo.'

export function ChatComposer({ className }: { className?: string }) {
  useDrakterState() // la primera suscripción arranca el enlace con el backend
  const link = useLinkStatus()
  const offline = link !== 'open'
  const activeTurn = useActiveTurn()
  const sending = useChatMessages().some((message) => message.status === 'sending')
  const [draft, setDraft] = useState('')
  const [failure, setFailure] = useState<string | null>(null)

  const text = draft.trim()
  const tooLong = text.length > MAX_MESSAGE_CHARS
  const canSend = !offline && !sending && activeTurn === null && text.length > 0 && !tooLong
  const notice = link !== 'open' ? LINK_NOTICES[link] : tooLong ? TOO_LONG_NOTICE : failure

  function send(): void {
    if (!canSend) return
    setFailure(null)
    setDraft('')
    // Los fallos de red quedan en la transcripción con Reintentar; aquí solo llega lo no aceptado.
    sendMessage(text).catch(() => {
      setDraft((current) => current || text)
      setFailure(SEND_FAILED_NOTICE)
    })
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>): void {
    if (event.key !== 'Enter' || event.shiftKey || event.nativeEvent.isComposing) return
    event.preventDefault()
    send()
  }

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      <ChatTranscript />
      <ConfirmationHost />
      {notice ? (
        <p id="chat-notice" className="text-sm text-muted-foreground">
          {notice}
        </p>
      ) : null}
      <div className="flex items-end gap-2">
        <Textarea
          rows={1}
          disabled={offline}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={onKeyDown}
          aria-label="Mensaje para Drakter"
          aria-describedby={notice ? 'chat-notice' : undefined}
          aria-invalid={tooLong || undefined}
          placeholder="Escribe un mensaje"
          className="min-h-9 max-h-28 resize-none py-1.5"
        />
        {activeTurn === null ? (
          <Button type="button" disabled={!canSend} onClick={send}>
            <SendHorizontal aria-hidden="true" />
            Enviar
          </Button>
        ) : (
          <Button type="button" variant="outline" disabled={offline} onClick={() => void cancelActiveTurn()}>
            <Square aria-hidden="true" />
            Detener
          </Button>
        )}
      </div>
    </div>
  )
}
