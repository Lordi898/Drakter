/**
 * Lista cerrada de rutas que el renderer puede pedir (D-14). Main rechaza
 * cualquier otro par de método y ruta. `{x}` casa con un segmento.
 *
 * PROVISIONAL: se sustituye por la lista generada desde `openapi.json`. Mientras
 * tanto se añade aquí cada ruta real del backend.
 *
 * Aprobar y rechazar confirmaciones, las raíces de almacén y los permisos NO
 * entran nunca: exigen el token `approver` y solo los usa main.
 */
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export interface AllowedRoute {
  readonly method: HttpMethod
  readonly path: string
}

export const ALLOWED_ROUTES: readonly AllowedRoute[] = [
  { method: 'GET', path: '/health' },
  { method: 'POST', path: '/api/v1/chat/messages' },
  { method: 'POST', path: '/api/v1/chat/turns/{turn_id}/cancel' },
  { method: 'GET', path: '/api/v1/confirmations' },
  { method: 'GET', path: '/api/v1/confirmations/{id}' }
]
