/**
 * Rutas de Hoy y Ajustes sobre el cliente común (`@/services/api`). Aquí no hay token,
 * sesión ni transporte: cuando el cliente pase a `window.drakter.api`, esto no cambia salvo
 * los identificadores de operación.
 */
import { ApiError, apiRequest } from '@/services/api'
import type { BackupItem, SettingItem, SettingsList, SettingsStatus, TodayResponse } from './contract'

export function fetchToday(timezone: string): Promise<TodayResponse> {
  return apiRequest<TodayResponse>(`/api/v1/today?timezone=${encodeURIComponent(timezone)}`)
}

export function fetchSettings(): Promise<SettingsList> {
  return apiRequest<SettingsList>('/api/v1/settings')
}

export function saveSetting(key: string, value: string): Promise<SettingItem> {
  return apiRequest<SettingItem>(`/api/v1/settings/${encodeURIComponent(key)}`, {
    method: 'POST',
    body: { value }
  })
}

export function fetchSettingsStatus(): Promise<SettingsStatus> {
  return apiRequest<SettingsStatus>('/api/v1/settings/status')
}

export function fetchBackups(): Promise<{ readonly items: readonly BackupItem[] }> {
  return apiRequest<{ readonly items: readonly BackupItem[] }>('/api/v1/settings/backups')
}

export function createBackup(): Promise<BackupItem> {
  return apiRequest<BackupItem>('/api/v1/settings/backups', { method: 'POST' })
}

/** `status === 0`: no hay respuesta del servicio local (sin sesión, red o tiempo agotado). */
export function isDisconnected(error: unknown): boolean {
  return error instanceof ApiError && error.status === 0
}
