import { ChatComposer } from '@/chat/ChatComposer'

export function ChatDock() {
  return (
    <div className="border-t border-border bg-background px-4 py-3">
      <ChatComposer />
    </div>
  )
}
