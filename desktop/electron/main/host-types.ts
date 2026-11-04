import type { WebContents } from 'electron'
import type { BackendConnection } from '../shared/bridge'

/** Solo existe en main. Nunca cruza IPC, ni va a logs, argv, entorno o disco. */
export interface BackendEndpoint {
  readonly port: number
  readonly uiToken: string
  readonly approverToken: string
}

export interface BackendHost {
  start(): void
  /** EOF por stdin; SIGTERM y SIGKILL si no sale. No relanza después. */
  stop(): Promise<void>
  getConnection(): BackendConnection
  /** Avisa de cada cambio. Devuelve la baja. */
  onConnection(listener: (connection: BackendConnection) => void): () => void
  /** `null` salvo en estado `ready`. Cambia con cada reinicio: no se guarda. */
  getEndpoint(): BackendEndpoint | null
  /** Resuelve con `null` si vence el plazo o el backend queda `failed` o `stopped`. */
  waitUntilReady(timeoutMs: number): Promise<BackendEndpoint | null>
}

export interface EventsBridge {
  /** Crea un `MessagePort` nuevo para ese renderer y cierra el anterior. */
  attach(contents: WebContents): void
  dispose(): void
}
