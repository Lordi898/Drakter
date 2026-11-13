import { memo, useLayoutEffect, useRef } from 'react'
import { Check, Loader2, Mic, RotateCcw, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useDrakterState } from '@/stores/agent'
import { retryMessage, useActiveTurn, useChatMessages, type ChatMessage, type ToolActivity } from '@/stores/chat'

/** Distancia al final por debajo de la cual se considera que el usuario sigue la conversación. */
const FOLLOW_THRESHOLD_PX = 32

const TOOL_STATES: Record<ToolActivity['state'], string> = {
  running: 'en curso',
  ok: 'hecho',
  failed: 'ha fallado'
}

function ToolLine({ tool }: { tool: ToolActivity }) {
  const Icon = tool.state === 'running' ? Loader2 : tool.state === 'ok' ? Check : X

  return (
    <li className="flex items-center gap-1.5 text-xs text-muted-foreground">
      <Icon
        aria-hidden="true"
        className={cn(
          'size-3 shrink-0',
          tool.state === 'running' && 'motion-safe:animate-spin',
          tool.state === 'failed' && 'text-destructive'
        )}
      />
      <span className="min-w-0 break-all">
        {tool.name}: {TOOL_STATES[tool.state]}
      </span>
    </li>
  )
}

/** `memo`: cada fragmento del streaming solo repinta el mensaje que cambia. */
const MessageItem = memo(function MessageItem({ message, canRetry }: { message: ChatMessage; canRetry: boolean }) {
  const fromUser = message.role === 'user'

  return (
    <li className={cn('flex max-w-[85%] flex-col gap-1', fromUser ? 'items-end self-end' : 'items-start')}>
      <span className="sr-only">{fromUser ? (message.viaVoice ? 'Tú (por voz):' : 'Tú:') : 'Drakter:'}</span>

      {message.tools.length > 0 ? (
        <ul className="flex flex-col gap-0.5">
          {message.tools.map((tool) => (
            <ToolLine key={tool.id} tool={tool} />
          ))}
        </ul>
      ) : null}

      {message.content || message.status === 'streaming' ? (
        <p
          className={cn(
            'max-w-full rounded-lg px-3 py-1.5 text-sm break-words whitespace-pre-wrap',
            fromUser
              ? 'bg-secondary text-secondary-foreground'
              : 'voice-drakter border border-border bg-card text-card-foreground'
          )}
        >
          {message.viaVoice ? <Mic aria-hidden="true" className="mr-1 inline size-3 align-[-0.1em] opacity-70" /> : null}
          {message.content}
          {message.status === 'streaming' ? (
            <span
              aria-hidden="true"
              className="ml-0.5 inline-block h-[1em] w-0.5 translate-y-[0.15em] bg-ambar motion-safe:animate-pulse"
            />
          ) : null}
        </p>
      ) : null}

      {message.status === 'sending' ? <span className="text-xs text-muted-foreground">Enviando…</span> : null}

      {message.status === 'interrupted' ? (
        <span className="text-xs text-warning">Esta respuesta se ha cortado y puede estar incompleta.</span>
      ) : null}

      {message.status === 'failed' ? (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-destructive">{message.error ?? 'No se ha podido completar.'}</span>
          {message.retryable !== false ? (
            <Button
              type="button"
              variant="outline"
              size="xs"
              disabled={!canRetry}
              onClick={() => void retryMessage(message.id)}
            >
              <RotateCcw aria-hidden="true" />
              Reintentar
            </Button>
          ) : null}
        </div>
      ) : null}
    </li>
  )
})

export function ChatTranscript() {
  const messages = useChatMessages()
  const offline = useDrakterState() === 'offline'
  const activeTurn = useActiveTurn()
  const logRef = useRef<HTMLDivElement>(null)
  const followingRef = useRef(true)

  useLayoutEffect(() => {
    const log = logRef.current
    if (log && followingRef.current) log.scrollTop = log.scrollHeight
  }, [messages])

  if (messages.length === 0) return null

  // Reintentar lanza otro turno: no puede solaparse con uno en marcha.
  const canRetry =
    !offline && activeTurn === null && !messages.some((message) => message.status === 'sending')

  function onScroll(): void {
    const log = logRef.current
    if (!log) return
    followingRef.current = log.scrollHeight - log.scrollTop - log.clientHeight < FOLLOW_THRESHOLD_PX
  }

  return (
    <div
      ref={logRef}
      role="log"
      aria-live="polite"
      aria-label="Conversación con Drakter"
      // Sin esto un lector de pantalla anunciaría cada fragmento del streaming.
      aria-busy={messages.some((message) => message.status === 'streaming')}
      tabIndex={0}
      onScroll={onScroll}
      className="max-h-[38vh] overflow-y-auto rounded-md"
    >
      <ol className="flex flex-col gap-2 pr-1">
        {messages.map((message) => (
          <MessageItem key={message.id} message={message} canRetry={canRetry} />
        ))}
      </ol>
    </div>
  )
}
