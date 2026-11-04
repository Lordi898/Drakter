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
