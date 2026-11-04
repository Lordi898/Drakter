import { notify } from '@/services/notify'
import { ApiError } from '@/services/api'

/** Mensajes propios por código; nunca el texto que envía el servidor. */
const MESSAGES: Readonly<Record<string, string>> = {
  not_found: 'Ya no existe: puede que otra acción lo haya quitado.',
  revision_mismatch: 'Este recurso ha cambiado mientras lo editabas. Hemos recargado la versión actual.',
  confirmation_required: 'Esta acción espera tu aprobación. No se ha hecho ningún cambio.',
  confirmation_unavailable: 'La confirmación aún no está disponible.',
  permission_denied: 'No tienes permiso para hacer esto.',
  path_not_allowed: 'Esa ruta no está permitida.',
  file_too_large: 'El archivo es demasiado grande.',
  archive_limit_exceeded: 'El comprimido supera los límites permitidos.',
  unsupported_format: 'Este formato no se puede leer.',
  resource_unavailable: 'El recurso no está disponible ahora mismo.',
  read_failed: 'No se ha podido leer el contenido.',
  url_not_allowed: 'Esa dirección no está permitida.',
  link_fetch_failed: 'No se ha podido descargar el enlace.',
  duplicate: 'Ya existe un recurso igual.',
  has_dependents: 'Tiene relaciones con otros elementos.',
  entity_archived: 'Está archivado.',
  no_session: 'Drakter no está conectado al servicio local.',
  network: 'No se ha podido contactar con el servicio local.',
  timeout: 'El servicio local ha tardado demasiado en responder.'
}

export function errorCode(error: unknown): string | null {
  return error instanceof ApiError ? error.code : null
}

export function isDisconnected(error: unknown): boolean {
  const code = errorCode(error)
  return code === 'no_session' || code === 'network'
}

export function humanMessage(error: unknown): string {
  const code = errorCode(error)
  return (code && MESSAGES[code]) || 'No se ha podido completar la acción.'
}

export interface PendingConfirmation {
  readonly summary: string
  readonly affected: number | null
}

/** Datos de `error.confirmation` (409 `confirmation_required`), leídos con cautela. */
export function confirmationOf(error: unknown): PendingConfirmation | null {
  if (!(error instanceof ApiError) || !error.confirmation) return null
  const { summary, affected_count } = error.confirmation
  return { summary: summary.slice(0, 300), affected: affected_count }
}

export function describeConfirmation(error: unknown): string {
  const c = confirmationOf(error)
  if (!c) return MESSAGES['confirmation_required'] ?? ''
  const count = c.affected === null ? '' : ` Afecta a ${c.affected} elemento${c.affected === 1 ? '' : 's'}.`
  return `Espera aprobación: ${c.summary}.${count} No se ha hecho ningún cambio.`
}

export function notifyError(title: string, error: unknown): void {
  const waiting = errorCode(error) === 'confirmation_required'
  notify({ tone: waiting ? 'info' : 'error', title, body: waiting ? describeConfirmation(error) : humanMessage(error) })
}
