/**
 * Contrato del puente preload ↔ renderer. Es lo ÚNICO que el renderer ve del
 * sistema: `window.drakter`. Todo mensaje se valida en el proceso principal.
 */
export const IPC_CHANNELS = {
  getAppInfo: 'drakter:app-info',
  showDesktopNotification: 'drakter:desktop-notification',
  reportRendererError: 'drakter:renderer-error'
} as const

export interface AppInfo {
  readonly appVersion: string
  readonly electronVersion: string
  readonly chromeVersion: string
  readonly nodeVersion: string
  readonly platform: string
  readonly packaged: boolean
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

export interface DrakterBridge {
  getAppInfo(): Promise<AppInfo>
  showDesktopNotification(request: DesktopNotificationRequest): Promise<void>
  reportRendererError(report: RendererErrorReport): Promise<void>
}
