/**
 * Proxy REST del proceso principal (D-14). El renderer no tiene token ni red:
 * el payload es NO CONFIABLE y se valida aquí a mano antes de tocar el backend.
 */
import { request } from 'node:http'
import type { ApiCallResult } from '../shared/bridge'
import { ALLOWED_ROUTES, type HttpMethod } from '../shared/operations'
import type { BackendHost } from './host-types'
import { describeError, logError } from './log'

export interface HttpReply {
  readonly status: number
  readonly text: string
}

/** Fallo sin respuesta HTTP. `code` es uno de los códigos de `ApiCallResult` con status 0. */
export class BackendRequestError extends Error {
  constructor(readonly code: 'invalid_request' | 'timeout' | 'backend_unavailable' | 'response_too_large') {
    super(code)
    this.name = 'BackendRequestError'
  }
}

const READY_TIMEOUT_MS = 10_000
const REQUEST_TIMEOUT_MS = 15_000
const MAX_BODY_BYTES = 1024 * 1024
const MAX_RESPONSE_BYTES = 16 * 1024 * 1024
const MAX_TEXT_CHARS = 2000
const CODE_PATTERN = /^[A-Za-z0-9_.-]{1,64}$/
const CONFIRMATIONS_PREFIX = '/api/v1/confirmations/'
const STORAGE_LOCATIONS = '/api/v1/storage-locations'
const MAX_PATH_CHARS = 2048
/** ASCII imprimible: excluye CR y LF, así que no se pueden inyectar cabeceras. */
const HEADER_VALUE_PATTERN = /^[\x20-\x7e]{1,128}$/
const METHODS: ReadonlySet<string> = new Set(['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])

// Defensa en profundidad: decidir confirmaciones y escribir raíces de almacén exigen
// el token approver y solo los usa main. Otras rutas `/approve` (memoria, mejora) son legítimas.
for (const route of ALLOWED_ROUTES) {
  const decides = route.path.startsWith(CONFIRMATIONS_PREFIX) && /\/(approve|reject)\/?$/.test(route.path)
  const writesStorage = isStorageLocations(route.path) && route.method !== 'GET'
  if (decides || writesStorage) throw new Error(`Ruta prohibida en ALLOWED_ROUTES: ${route.method} ${route.path}`)
}

function isStorageLocations(path: string): boolean {
  return path === STORAGE_LOCATIONS || path.startsWith(`${STORAGE_LOCATIONS}/`)
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return false
  const proto = Object.getPrototypeOf(value)
  return proto === Object.prototype || proto === null
}

function invalid(): ApiCallResult {
  return { ok: false, status: 0, code: 'invalid_request', body: null }
}

function failure(code: string): ApiCallResult {
  return { ok: false, status: 0, code, body: null }
}

const ROUTE_TEMPLATES = ALLOWED_ROUTES.map((route) => ({
  method: route.method,
  segments: route.path.split('/')
}))

function matchesAllowed(method: string, segments: readonly string[]): boolean {
  return ROUTE_TEMPLATES.some(
    (route) =>
      route.method === method &&
      route.segments.length === segments.length &&
      route.segments.every((part, i) => (part.startsWith('{') && part.endsWith('}') ? segments[i] !== '' : part === segments[i]))
  )
}

/**
 * Valida y normaliza `path` (con query opcional) contra `ALLOWED_ROUTES`.
 * Devuelve la ruta lista para enviar o `null`. La query se reserializa.
 */
function validatePath(method: string, raw: unknown): string | null {
  if (typeof raw !== 'string' || raw.length > MAX_PATH_CHARS || !raw.startsWith('/') || raw.startsWith('//')) {
    return null
  }
  if (!/^[\x21-\x7e]+$/.test(raw) || raw.includes('#') || raw.includes('\\')) return null

  const queryAt = raw.indexOf('?')
  const pathname = queryAt === -1 ? raw : raw.slice(0, queryAt)
  const queryText = queryAt === -1 ? '' : raw.slice(queryAt + 1)

  const segments = pathname.split('/')
  for (const segment of segments.slice(1)) {
    if (segment === '') return null
    let decoded: string
    try {
      decoded = decodeURIComponent(segment)
    } catch {
      return null
    }
    if (decoded === '.' || decoded === '..' || decoded.includes('/') || decoded.includes('\\')) return null
    if (/[\p{Cc}]/u.test(decoded)) return null
  }
  if (pathname.startsWith(CONFIRMATIONS_PREFIX) && hasDecisionSegment(pathname)) return null
  if (isStorageLocations(pathname) && method !== 'GET') return null
  if (!matchesAllowed(method, segments)) return null

  const query = new URLSearchParams(queryText).toString()
  return query ? `${pathname}?${query}` : pathname
}

/** Ningún segmento approve o reject bajo /api/v1/confirmations/. */
function hasDecisionSegment(path: string): boolean {
  return path.split('/').some((segment) => {
    let decoded = segment
    try {
      decoded = decodeURIComponent(segment)
    } catch {
      /* segmento no decodificable: se compara tal cual */
    }
    const lower = decoded.toLowerCase()
    return lower === 'approve' || lower === 'reject'
  })
}

/** Traduce `options` a cabeceras. `null` si no es válido. */
function headersFromOptions(method: string, options: unknown): Record<string, string> | null {
  if (options === undefined) return {}
  if (!isPlainObject(options)) return null
  const headers: Record<string, string> = {}
  for (const [key, value] of Object.entries(options)) {
    if (value === undefined) continue
    if (typeof value !== 'string' || !HEADER_VALUE_PATTERN.test(value) || method === 'GET') return null
    if (key === 'ifMatch') headers['If-Match'] = value
    else if (key === 'idempotencyKey') headers['Idempotency-Key'] = value
    else return null
  }
  return headers
}

function serializeBody(body: unknown): string {
  let json: string | undefined
  try {
    json = JSON.stringify(body)
  } catch {
    throw new BackendRequestError('invalid_request')
  }
  if (json === undefined || Buffer.byteLength(json, 'utf8') > MAX_BODY_BYTES) {
    throw new BackendRequestError('invalid_request')
  }
  return json
}

/**
 * Una sola petición, sin reintentos ni redirecciones: reenviar una escritura
 * podría ejecutarla dos veces. Rechaza con `BackendRequestError`.
 */
export function requestBackend(
  endpoint: { port: number },
  token: string,
  method: HttpMethod,
  path: string,
  body?: unknown,
  timeoutMs: number = REQUEST_TIMEOUT_MS,
  extraHeaders: Readonly<Record<string, string>> = {}
): Promise<HttpReply> {
  return new Promise<HttpReply>((resolve, reject) => {
    let payload: string | undefined
    try {
      if (body !== undefined) {
        if (method === 'GET') throw new BackendRequestError('invalid_request')
        payload = serializeBody(body)
      }
    } catch (error) {
      reject(error)
      return
    }

    const headers: Record<string, string | number> = {
      ...extraHeaders,
      Authorization: `Bearer ${token}`,
      Accept: 'application/json'
    }
    if (payload !== undefined) {
      headers['Content-Type'] = 'application/json'
      headers['Content-Length'] = Buffer.byteLength(payload, 'utf8')
    }

    let settled = false
    const settle = (finish: () => void): void => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      finish()
    }

    const req = request({
      hostname: '127.0.0.1',
      port: endpoint.port,
      method,
      path,
      headers,
      agent: false
    })
    const timer = setTimeout(() => {
      settle(() => reject(new BackendRequestError('timeout')))
      req.destroy()
    }, timeoutMs)

    req.on('response', (res) => {
      const chunks: Buffer[] = []
      let size = 0
      res.on('data', (chunk: Buffer) => {
        size += chunk.length
        if (size > MAX_RESPONSE_BYTES) {
          settle(() => reject(new BackendRequestError('response_too_large')))
          req.destroy()
          return
        }
        chunks.push(chunk)
      })
      res.on('end', () => {
        settle(() => resolve({ status: res.statusCode ?? 0, text: Buffer.concat(chunks).toString('utf8') }))
      })
      res.on('error', () => settle(() => reject(new BackendRequestError('backend_unavailable'))))
      res.on('aborted', () => settle(() => reject(new BackendRequestError('backend_unavailable'))))
    })
    req.on('error', () => settle(() => reject(new BackendRequestError('backend_unavailable'))))
    req.end(payload)
  })
}

/** JSON si lo es; vacío → null; texto recortado en otro caso. */
export function parseReplyBody(text: string): unknown {
  if (text.trim() === '') return null
  try {
    return JSON.parse(text) as unknown
  } catch {
    return text.slice(0, MAX_TEXT_CHARS)
  }
}

/** Código de error RFC 9457 (`code`) o `{error:{code}}`; si no casa, `http_error`. */
export function extractErrorCode(body: unknown): string {
  if (isPlainObject(body)) {
    const candidates = [body.code, isPlainObject(body.error) ? body.error.code : undefined]
    for (const candidate of candidates) {
      if (typeof candidate === 'string' && CODE_PATTERN.test(candidate)) return candidate
    }
  }
  return 'http_error'
}

export async function callOperation(host: BackendHost, payload: unknown): Promise<ApiCallResult> {
  try {
    if (!isPlainObject(payload) || typeof payload.method !== 'string' || !METHODS.has(payload.method)) {
      return invalid()
    }
    if (Object.keys(payload).some((key) => !['method', 'path', 'body', 'options'].includes(key))) return invalid()

    const method = payload.method as HttpMethod
    const path = validatePath(method, payload.path)
    if (path === null) return invalid()
    const extraHeaders = headersFromOptions(method, payload.options)
    if (extraHeaders === null) return invalid()
    if (payload.body !== undefined) {
      if (method === 'GET') return invalid()
      serializeBody(payload.body)
    }

    // Antes de enviar: aquí esperar es seguro porque aún no hay petición.
    const endpoint = await host.waitUntilReady(READY_TIMEOUT_MS)
    if (endpoint === null) return failure('backend_unavailable')

    const reply = await requestBackend(
      endpoint,
      endpoint.uiToken,
      method,
      path,
      payload.body,
      REQUEST_TIMEOUT_MS,
      extraHeaders
    )
    const parsed = parseReplyBody(reply.text)
    if (reply.status >= 200 && reply.status < 300) {
      return { ok: true, status: reply.status, data: parsed }
    }
    return { ok: false, status: reply.status, code: extractErrorCode(parsed), body: parsed }
  } catch (error) {
    if (error instanceof BackendRequestError) return failure(error.code)
    logError('apiProxy', 'Fallo inesperado en callOperation', describeError(error))
    return failure('backend_unavailable')
  }
}
