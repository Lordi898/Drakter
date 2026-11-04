/**
 * Operaciones del módulo. El renderer no conoce rutas ni token: estas entradas se
 * copian en `OPERATIONS` de `electron/shared/operations.ts`, la lista cerrada de main
 * (se generan desde `openapi.json` cuando exista). Sin ellas, main rechaza la llamada.
 */
export const NOTIFICATION_OPERATIONS = {
  'notifications.list': { method: 'GET', path: '/api/v1/notifications' },
  'notifications.read': { method: 'POST', path: '/api/v1/notifications/read' },
  'notifications.status': { method: 'GET', path: '/api/v1/notifications/status' }
} as const
