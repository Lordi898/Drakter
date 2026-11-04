/**
 * Raíces de almacén (D-14): exigen el token `approver`, así que solo pasan por
 * aquí. El renderer no envía rutas: el directorio sale del selector nativo.
 */
import { basename } from 'node:path'
import { dialog, type OpenDialogOptions } from 'electron'
import type { ApiCallResult, StorageLocationChanges } from '../shared/bridge'
import { BackendRequestError, extractErrorCode, parseReplyBody, requestBackend } from './apiProxy'
import { sanitize, UUID_PATTERN } from './approvals'
import type { BackendEndpoint, BackendHost } from './host-types'
import { describeError, logError } from './log'
import { getMainWindow } from './window'

const BASE = '/api/v1/storage-locations'
const READY_TIMEOUT_MS = 10_000
const MAX_LABEL_CHARS = 200
const CHANGE_KEYS = ['label', 'enabled', 'read_only', 'agent_read'] as const

const invalid: ApiCallResult = { ok: false, status: 0, code: 'invalid_request', body: null }

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function parent(): Electron.BrowserWindow | undefined {
  const window = getMainWindow()
  return window && !window.isDestroyed() ? window : undefined
}

/** Ejecuta `action` con el backend listo y traduce el resultado al sobre común. */
async function withBackend(
  host: BackendHost,
  action: (endpoint: BackendEndpoint) => Promise<{ status: number; text: string } | ApiCallResult>
): Promise<ApiCallResult> {
  try {
    const endpoint = await host.waitUntilReady(READY_TIMEOUT_MS)
    if (endpoint === null) return { ok: false, status: 0, code: 'backend_unavailable', body: null }
    const reply = await action(endpoint)
    if ('ok' in reply) return reply
    const parsed = parseReplyBody(reply.text)
    if (reply.status >= 200 && reply.status < 300) return { ok: true, status: reply.status, data: parsed }
    return { ok: false, status: reply.status, code: extractErrorCode(parsed), body: parsed }
  } catch (error) {
    if (error instanceof BackendRequestError) return { ok: false, status: 0, code: error.code, body: null }
    logError('storage-roots', 'Fallo en la operación', describeError(error))
    return { ok: false, status: 0, code: 'backend_unavailable', body: null }
  }
}

/** `null` si el usuario cancela. Nace de solo lectura y sin acceso del agente. */
export async function addStorageLocation(host: BackendHost, payload: unknown): Promise<ApiCallResult | null> {
  if (payload !== undefined && typeof payload !== 'string') return invalid
  const options: OpenDialogOptions = { title: 'Elegir carpeta del almacén', properties: ['openDirectory'] }
  const window = parent()
  const picked = window ? await dialog.showOpenDialog(window, options) : await dialog.showOpenDialog(options)
  const path = picked.filePaths[0]
  if (picked.canceled || path === undefined) return null

  const label = sanitize(payload ?? '', MAX_LABEL_CHARS) || sanitize(basename(path), MAX_LABEL_CHARS) || path.slice(0, MAX_LABEL_CHARS)
  const body = { path, label, read_only: true, agent_read: false }
  return withBackend(host, (endpoint) => requestBackend(endpoint, endpoint.approverToken, 'POST', BASE, body))
}

function parseChanges(payload: unknown): StorageLocationChanges | null {
  if (!isRecord(payload)) return null
  const entries = Object.entries(payload).filter(([, value]) => value !== undefined)
  if (entries.length === 0) return null
  for (const [key, value] of entries) {
    if (!(CHANGE_KEYS as readonly string[]).includes(key)) return null
    if (key === 'label' ? typeof value !== 'string' : typeof value !== 'boolean') return null
  }
  return Object.fromEntries(entries) as StorageLocationChanges
}

function describeChanges(changes: StorageLocationChanges): string {
  const lines: string[] = []
  if (changes.label !== undefined) lines.push(`Nombre: ${sanitize(changes.label, MAX_LABEL_CHARS)}`)
  if (changes.enabled !== undefined) lines.push(changes.enabled ? 'Se activa' : 'Se desactiva')
  if (changes.read_only !== undefined) lines.push(changes.read_only ? 'Solo lectura' : 'Permite escritura')
  if (changes.agent_read !== undefined) {
    lines.push(changes.agent_read ? 'El agente podrá leer esta carpeta' : 'El agente deja de leer esta carpeta')
  }
  return lines.join('\n')
}

/** Busca la ruta real en el backend: lo mostrado no puede venir del renderer. */
async function locationPath(endpoint: BackendEndpoint, id: string): Promise<string | null> {
  const reply = await requestBackend(endpoint, endpoint.uiToken, 'GET', BASE)
  if (reply.status < 200 || reply.status >= 300) return null
  const body = parseReplyBody(reply.text)
  const items: unknown = isRecord(body) ? body['items'] : body
  if (!Array.isArray(items)) return null
  const found = items.find((item) => isRecord(item) && item['id'] === id) as Record<string, unknown> | undefined
  return found !== undefined && typeof found['path'] === 'string' ? found['path'] : null
}

/** `null` si el usuario cancela el diálogo nativo. */
export async function updateStorageLocation(host: BackendHost, payload: unknown): Promise<ApiCallResult | null> {
  if (!isRecord(payload) || typeof payload['id'] !== 'string' || !UUID_PATTERN.test(payload['id'])) return invalid
  const id = payload['id']
  const changes = parseChanges(payload['changes'])
  if (changes === null) return invalid

  let cancelled = false
  const result = await withBackend(host, async (endpoint) => {
    const path = await locationPath(endpoint, id)
    if (path === null) return { ok: false, status: 404, code: 'not_found', body: null }
    const options = {
      type: 'warning' as const,
      title: 'Cambiar ubicación del almacén',
      message: sanitize(path, 500),
      detail: describeChanges(changes),
      buttons: ['Cancelar', 'Aplicar'],
      defaultId: 0,
      cancelId: 0,
      noLink: true
    }
    const window = parent()
    // Como propiedad: el arnés e2e sustituye `dialog.showMessageBox`.
    const choice = window ? await dialog.showMessageBox(window, options) : await dialog.showMessageBox(options)
    if (choice.response !== 1) {
      cancelled = true
      return { ok: false, status: 0, code: 'cancelled', body: null }
    }
    const current = host.getEndpoint()
    if (current === null) return { ok: false, status: 0, code: 'backend_unavailable', body: null }
    return requestBackend(current, current.approverToken, 'PATCH', `${BASE}/${id}`, changes)
  })
  return cancelled ? null : result
}

/** Responde 409 `confirmation_required`: el renderer sigue con `requestApproval`. */
export function deleteStorageLocation(host: BackendHost, payload: unknown): Promise<ApiCallResult> {
  if (typeof payload !== 'string' || !UUID_PATTERN.test(payload)) return Promise.resolve(invalid)
  return withBackend(host, (endpoint) =>
    requestBackend(endpoint, endpoint.approverToken, 'DELETE', `${BASE}/${payload}`)
  )
}
