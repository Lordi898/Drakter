/**
 * Lista cerrada de operaciones que el renderer puede pedir (D-14). Main rechaza
 * cualquier otro `opId`.
 *
 * PROVISIONAL: se sustituye por `operations.generated.ts`, generado desde
 * `openapi.json`. Mientras tanto se añade aquí cada ruta real del backend.
 *
 * Aprobar y rechazar confirmaciones, las raíces de almacén y los permisos NO
 * entran nunca: exigen el token `approver` y solo los usa main.
 */
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export interface OperationSpec {
  readonly method: HttpMethod
  /** Ruta absoluta con `{marcadores}` para los parámetros. */
  readonly path: string
}

export const OPERATIONS = {
  'system.health': { method: 'GET', path: '/health' },
  'chat.send': { method: 'POST', path: '/api/v1/chat/messages' },
  'chat.cancel': { method: 'POST', path: '/api/v1/chat/turns/{turn_id}/cancel' },
  'confirmations.list': { method: 'GET', path: '/api/v1/confirmations' },
  'confirmations.get': { method: 'GET', path: '/api/v1/confirmations/{id}' }
} as const satisfies Readonly<Record<string, OperationSpec>>

export type OpId = keyof typeof OPERATIONS
