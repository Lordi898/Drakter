/**
 * Ubicaciones por el puente: main abre los diálogos nativos y el renderer nunca
 * envía una ruta. El resto del módulo usa `@/services/api`.
 */
import type { ApiCallResult, ApprovalOutcome } from '../../../electron/shared/bridge'
import { ApiError } from '@/services/api'

const FAILED = 'No se ha podido completar la acción.'

interface FailureBody {
  readonly error?: { readonly code?: unknown }
  readonly confirmation?: { readonly id?: unknown }
}

function failure(result: Extract<ApiCallResult, { ok: false }>): ApiError {
  const code = (result.body as FailureBody | null | undefined)?.error?.code
  return new ApiError(result.status, typeof code === 'string' ? code : result.code, FAILED)
}

function unwrap(result: ApiCallResult): void {
  if (!result.ok) throw failure(result)
}

/** `false` si el usuario cancela el diálogo. */
export async function addLocation(): Promise<boolean> {
  const result = await window.api.addStorageLocation()
  if (result === null) return false
  unwrap(result)
  return true
}

/** `false` si el usuario cancela el diálogo. */
export async function changeLocation(
  id: string,
  changes: { agent_read?: boolean; enabled?: boolean }
): Promise<boolean> {
  const result = await window.api.updateStorageLocation(id, changes)
  if (result === null) return false
  unwrap(result)
  return true
}

/** Pide el ticket y abre la aprobación nativa: es main quien decide. */
export async function removeLocation(id: string): Promise<ApprovalOutcome> {
  const result = await window.api.deleteStorageLocation(id)
  if (result.ok) return 'approved'
  const ticket = (result.body as FailureBody | null | undefined)?.confirmation?.id
  if (result.status !== 409 || typeof ticket !== 'string') throw failure(result)
  return window.api.requestApproval(ticket)
}
