import { GENERATED_ROUTES } from './routes.generated'

/**
 * Lista cerrada de rutas que el renderer puede pedir (D-14). Main rechaza
 * cualquier otro par de método y ruta. `{x}` casa con un segmento.
 *
 * Se genera desde `contracts/api/routes.md` con `scripts/generate-routes.mjs`,
 * que excluye lo que exige el token `approver`: aprobar y rechazar
 * confirmaciones, escribir raíces de almacén y permisos. Solo los usa main.
 */
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export interface AllowedRoute {
  readonly method: HttpMethod
  readonly path: string
}

export const ALLOWED_ROUTES: readonly AllowedRoute[] = GENERATED_ROUTES.map(([method, path]) => ({ method, path }))

/**
 * Operaciones con nombre (plan de voz v2 §4.3). Cada una es un par método/ruta
 * de `ALLOWED_ROUTES`; `{job_id}` se sustituye por un UUID validado en main.
 */
export const OPERATIONS = {
  'voice.offer': { method: 'POST', path: '/api/v1/voice/offer' },
  'voice.activate': { method: 'POST', path: '/api/v1/voice/activate' },
  'voice.mode': { method: 'POST', path: '/api/v1/voice/mode' },
  'voice.status': { method: 'GET', path: '/api/v1/voice/status' },
  'jobs.list': { method: 'GET', path: '/api/v1/jobs' },
  'jobs.cancel': { method: 'POST', path: '/api/v1/jobs/{job_id}/cancel' }
} as const satisfies Record<string, AllowedRoute>

export type OperationName = keyof typeof OPERATIONS
