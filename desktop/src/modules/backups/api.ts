import { backend, runConfirmable } from '../remote'
import type { BundleInfo, ExportResponse, VerifyResponse } from './types'

export const listBackups = () => backend<readonly BundleInfo[]>('GET', '/backups')

export const createBackup = (includeStorage = false) =>
  backend<BundleInfo>('POST', '/backups', { label: 'manual', include_storage: includeStorage })

export const exportWorkspace = () => backend<ExportResponse>('POST', '/backups/export', {})

export const verifyBackup = (name: string) =>
  backend<VerifyResponse>('POST', `/backups/${encodeURIComponent(name)}/verify`, {})

/** Borrar es confirmable: 409 y la decisión la toma el diálogo nativo. No existe ruta para restaurar. */
export const deleteBackup = (name: string) =>
  runConfirmable(() => backend<void>('DELETE', `/backups/${encodeURIComponent(name)}`))
