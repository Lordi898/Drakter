/** Señales de actividad del usuario para el personaje (hoy: escribir en el chat). Sin suscriptores no cuesta nada. */

type Listener = () => void

const typingListeners = new Set<Listener>()
const THROTTLE_MS = 400
let lastTyping = 0

/** La llama el campo del chat en cada pulsación; se limita a un aviso cada 400 ms. */
export function signalUserTyping(): void {
  const now = performance.now()
  if (now - lastTyping < THROTTLE_MS) return
  lastTyping = now
  for (const listener of typingListeners) listener()
}

export function subscribeUserTyping(listener: Listener): () => void {
  typingListeners.add(listener)
  return () => {
    typingListeners.delete(listener)
  }
}
