/**
 * Contrato del puente preload ↔ renderer. Es lo ÚNICO que el renderer ve del
 * sistema: `window.drakter`. Todo mensaje se valida en el proceso principal.
 */
import type {
  JobList,
  JobOut,
  VoiceActivateIn,
  VoiceModeIn,
  VoiceOfferIn,
  VoiceOfferOut,
  VoiceState,
  VoiceStatusOut
} from '../../../contracts/ts'
import type { HttpMethod } from './operations'

export type { HttpMethod } from './operations'

export const IPC_CHANNELS = {
  getAppInfo: 'drakter:app-info',
  showDesktopNotification: 'drakter:desktop-notification',
  reportRendererError: 'drakter:renderer-error',
  apiCall: 'drakter:api-call',
  requestApproval: 'drakter:request-approval',
  getConnection: 'drakter:get-connection',
  addStorageLocation: 'drakter:storage-add',
  updateStorageLocation: 'drakter:storage-update',
  deleteStorageLocation: 'drakter:storage-delete',
  /** Renderer → main: pide el puerto de eventos. Main responde por `eventsPort`. */
  openEvents: 'drakter:open-events',
  /** Main → preload: entrega el `MessagePort` de eventos. */
  eventsPort: 'drakter:events-port',
  /** Main → preload: cambios del estado del backend. */
  connectionChanged: 'drakter:connection-changed',
  /** Main → renderer: alternar el micrófono desde la bandeja (voz v2). */
  voiceMicToggle: 'voice:mic-toggle',
  /** Renderer → main: el micrófono quedó abierto o cerrado (etiqueta de la bandeja). */
  voiceMicState: 'voice:mic-state'
} as const

export interface AppInfo {
  readonly appVersion: string
  readonly electronVersion: string
  readonly chromeVersion: string
  readonly nodeVersion: string
  readonly platform: string
  readonly packaged: boolean
  /** Solo en desarrollo con DRAKTER_DEV_NO_SANDBOX=1. Debe mostrarse como aviso. */
  readonly sandboxDisabled: boolean
}

/** Máximos que el proceso principal hace cumplir. */
export const DESKTOP_NOTIFICATION_LIMITS = { title: 120, body: 500 } as const
export const ERROR_REPORT_LIMITS = { source: 80, message: 2000, stack: 8000 } as const

export interface DesktopNotificationRequest {
  readonly title: string
  readonly body?: string
}

export interface RendererErrorReport {
  readonly source: string
  readonly message: string
  readonly stack?: string
}

/**
 * No se rechaza por errores HTTP: `ok: false` lleva el estado y el cuerpo sin
 * interpretar (dato no confiable). `status: 0` significa que no hubo respuesta:
 * `code` vale `backend_unavailable`, `timeout`, `invalid_request` o `response_too_large`.
 */
export type ApiCallResult =
  | { readonly ok: true; readonly status: number; readonly data: unknown }
  | { readonly ok: false; readonly status: number; readonly code: string; readonly body: unknown }

/**
 * `approved`: el backend ejecutó la acción. `conflict`: los objetivos cambiaron.
 * `failed`: la acción falló o no se pudo decidir. Nada de esto reanuda el turno (D-13).
 */
export type ApprovalOutcome = 'approved' | 'rejected' | 'expired' | 'conflict' | 'failed'

export type BackendState = 'starting' | 'ready' | 'restarting' | 'failed' | 'stopped'

/** Sin puerto ni credenciales: el renderer no los conoce nunca (D-14). */
export interface BackendConnection {
  readonly state: BackendState
  /** Solo en `failed`: texto propio para mostrar al usuario, con lo que debe hacer. */
  readonly detail?: string
}

/** `events`: cada evento de `/ws`, parseado y SIN validar. `connection`: `BackendConnection`. */
export type ApiTopic = 'events' | 'connection'

/** Solo estas dos cabeceras; main las valida y no acepta cabeceras libres. */
export interface ApiCallOptions {
  readonly ifMatch?: string
  readonly idempotencyKey?: string
}

export interface StorageLocationChanges {
  readonly label?: string
  readonly enabled?: boolean
  readonly read_only?: boolean
  readonly agent_read?: boolean
}

/**
 * Resultado tipado de una operación: igual que `ApiCallResult`, con `data` ya
 * del tipo del contrato (sin validar en el renderer: lo valida el backend).
 */
export type ApiResult<T> =
  | { readonly ok: true; readonly status: number; readonly data: T }
  | { readonly ok: false; readonly status: number; readonly code: string; readonly body: unknown }

/** `window.api.voice` (voz v2). El micrófono no pasa por aquí: es local al renderer. */
export interface VoiceApi {
  offer(body: VoiceOfferIn): Promise<ApiResult<VoiceOfferOut>>
  activate(body: VoiceActivateIn): Promise<ApiResult<VoiceState>>
  mode(body: VoiceModeIn): Promise<ApiResult<VoiceState>>
  status(): Promise<ApiResult<VoiceStatusOut>>
  /** Canal main→renderer `voice:mic-toggle` (bandeja). Devuelve la baja. */
  onMicToggle(callback: () => void): () => void
  /** Canal renderer→main `voice:mic-state`: la bandeja refleja si el micrófono está abierto. */
  reportMicState(open: boolean): Promise<void>
}

/** `window.api.jobs`: trabajos en segundo plano. */
export interface JobsApi {
  list(): Promise<ApiResult<JobList>>
  cancel(jobId: string): Promise<ApiResult<JobOut>>
}

/**
 * `window.api`: ÚNICA interfaz del renderer con el backend (D-14). El renderer no
 * tiene token, puerto ni red. Main valida método y ruta contra `ALLOWED_ROUTES` y
 * añade la credencial; `path` puede llevar query (`/api/v1/tasks?status=open`).
 */
export interface DrakterApi {
  call(method: HttpMethod, path: string, body?: unknown, options?: ApiCallOptions): Promise<ApiCallResult>
  subscribe(topic: ApiTopic, callback: (event: unknown) => void): () => void
  /** Abre el diálogo nativo en main. El renderer no puede aprobar por otra vía. */
  requestApproval(actionId: string): Promise<ApprovalOutcome>
  getConnection(): Promise<BackendConnection>
  /** Selector nativo en main; el renderer no envía rutas. `null` si se cancela. */
  addStorageLocation(label?: string): Promise<ApiCallResult | null>
  /** Confirma con diálogo nativo en main. `null` si se cancela. */
  updateStorageLocation(id: string, changes: StorageLocationChanges): Promise<ApiCallResult | null>
  /** Devuelve 409 `confirmation_required`; se sigue con `requestApproval`. */
  deleteStorageLocation(id: string): Promise<ApiCallResult>
  readonly voice: VoiceApi
  readonly jobs: JobsApi
}

/** `window.drakter`: solo servicios de escritorio, sin relación con el backend. */
export interface DrakterBridge {
  getAppInfo(): Promise<AppInfo>
  showDesktopNotification(request: DesktopNotificationRequest): Promise<void>
  reportRendererError(report: RendererErrorReport): Promise<void>
}
