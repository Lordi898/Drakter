/**
 * Aprobación con diálogo nativo (D-13). Main descarga el detalle de la
 * confirmación: el renderer solo aporta el id y no puede decidir por otra vía.
 */
import { dialog } from 'electron'
import type { ApprovalOutcome } from '../shared/bridge'
import { BackendRequestError, extractErrorCode, parseReplyBody, requestBackend } from './apiProxy'
import type { BackendHost } from './host-types'
import { describeError, logError } from './log'
import { getMainWindow } from './window'

/** Título del diálogo nativo: el modo flotante lo busca por él para traerlo al frente. */
export const APPROVAL_TITLE = 'Confirmar acción'

export const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const READY_TIMEOUT_MS = 10_000
const DETAIL_TIMEOUT_MS = 15_000
const REJECT_TIMEOUT_MS = 15_000
const APPROVE_TIMEOUT_MS = 60_000 // ejecuta la acción
const MAX_SUMMARY_CHARS = 500
const MAX_RISK_CHARS = 40

interface ConfirmationDetail {
  readonly summary: string
  readonly affectedCount: number | null
  readonly paramsHash: string
  readonly risk?: string
}

const inFlight = new Map<string, Promise<ApprovalOutcome>>()
let queueTail: Promise<unknown> = Promise.resolve()

/**
 * Se avisa antes de abrir cada diálogo (`true`, y se espera como mucho `GUARD_WAIT_MS`) y al cerrarse
 * (`false`). El modo flotante lo usa para ocultar su capa entera: nada pintado puede quedar encima del
 * único control humano (revisión de seguridad del PR #76, I8).
 */
export type ApprovalGuard = (open: boolean) => Promise<void>
const GUARD_WAIT_MS = 1500
let guard: ApprovalGuard | null = null

export function setApprovalGuard(next: ApprovalGuard | null): void {
  guard = next
}

async function runGuard(open: boolean): Promise<void> {
  const current = guard
  if (!current) return
  let timer: NodeJS.Timeout | undefined
  try {
    await Promise.race([
      current(open),
      new Promise<void>((resolve) => {
        timer = setTimeout(resolve, GUARD_WAIT_MS)
      })
    ])
  } catch (error) {
    logError('approvals', 'Fallo al preparar la pantalla para la confirmación', describeError(error))
  } finally {
    clearTimeout(timer)
  }
}

/** El texto viene del backend (dato no confiable): sin control, una línea, recortado. */
export function sanitize(text: string, max: number): string {
  return text
    .replace(/[\p{Cc}\p{Cf}\u2028\u2029]+/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, max)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

type ParsedDetail = ConfirmationDetail | 'expired' | 'failed'

function parseDetail(body: unknown): ParsedDetail {
  if (!isRecord(body)) return 'failed'
  const { summary, affected_count, params_hash, status, expires_at, risk } = body
  if (
    typeof summary !== 'string' ||
    !(affected_count === null || (Number.isSafeInteger(affected_count) && (affected_count as number) >= 0)) ||
    typeof params_hash !== 'string' ||
    params_hash === '' ||
    typeof status !== 'string' ||
    typeof expires_at !== 'string'
  ) {
    return 'failed'
  }
  if (status !== 'pending') return 'expired'
  const expiry = Date.parse(expires_at)
  if (Number.isNaN(expiry)) return 'failed'
  if (expiry <= Date.now()) return 'expired'
  return {
    summary,
    affectedCount: affected_count as number | null,
    paramsHash: params_hash,
    risk: typeof risk === 'string' ? risk : undefined
  }
}

async function runApproval(host: BackendHost, id: string): Promise<ApprovalOutcome> {
  try {
    const ready = await host.waitUntilReady(READY_TIMEOUT_MS)
    if (ready === null) return 'failed'

    const base = `/api/v1/confirmations/${encodeURIComponent(id)}`
    const detailReply = await requestBackend(ready, ready.uiToken, 'GET', base, undefined, DETAIL_TIMEOUT_MS)
    if (detailReply.status === 404 || detailReply.status === 410) return 'expired'
    if (detailReply.status < 200 || detailReply.status >= 300) return 'failed'
    const detail = parseDetail(parseReplyBody(detailReply.text))
    if (detail === 'expired' || detail === 'failed') return detail

    // Sin resumen legible nadie puede decidir: no se abre un diálogo en blanco.
    const message = sanitize(detail.summary, MAX_SUMMARY_CHARS)
    if (message === '') return 'failed'

    const lines = detail.affectedCount === null ? [] : [`Elementos afectados: ${detail.affectedCount}`]
    const risk = detail.risk === undefined ? '' : sanitize(detail.risk, MAX_RISK_CHARS)
    if (risk) lines.push(`Riesgo: ${risk}`)
    const options = {
      type: 'warning' as const,
      title: APPROVAL_TITLE,
      message,
      detail: lines.join('\n'),
      buttons: ['Cancelar', 'Aprobar'],
      defaultId: 0,
      cancelId: 0,
      noLink: true
    }
    const parent = getMainWindow()
    // Siempre como propiedad: el arnés e2e sustituye `dialog.showMessageBox`.
    // Con la principal oculta (modo flotante, CONTRACT §4.2) el diálogo se abre sin padre.
    await runGuard(true)
    let result: Electron.MessageBoxReturnValue
    try {
      result =
        parent && !parent.isDestroyed() && parent.isVisible()
          ? await dialog.showMessageBox(parent, options)
          : await dialog.showMessageBox(options)
    } finally {
      await runGuard(false)
    }

    // El backend pudo reiniciarse mientras el diálogo estaba abierto.
    const endpoint = host.getEndpoint()
    if (endpoint === null) return 'failed'

    if (result.response !== 1) {
      const reply = await requestBackend(endpoint, endpoint.approverToken, 'POST', `${base}/reject`, undefined, REJECT_TIMEOUT_MS)
      if (reply.status >= 200 && reply.status < 300) return 'rejected'
      if (reply.status === 404 || reply.status === 409 || reply.status === 410) return 'expired'
      return 'failed'
    }

    const reply = await requestBackend(
      endpoint,
      endpoint.approverToken,
      'POST',
      `${base}/approve`,
      { params_hash: detail.paramsHash },
      APPROVE_TIMEOUT_MS
    )
    if (reply.status >= 200 && reply.status < 300) return 'approved'
    if (reply.status === 404 || reply.status === 410) return 'expired'
    if (reply.status === 409) {
      return extractErrorCode(parseReplyBody(reply.text)) === 'conflict' ? 'conflict' : 'expired'
    }
    return 'failed'
  } catch (error) {
    const detail = error instanceof BackendRequestError ? error.code : describeError(error)
    logError('approvals', 'Fallo en la aprobación', detail)
    return 'failed'
  }
}

export function requestApproval(host: BackendHost, payload: unknown): Promise<ApprovalOutcome> {
  if (typeof payload !== 'string' || !UUID_PATTERN.test(payload)) return Promise.resolve('failed')
  const id = payload.toLowerCase()
  const existing = inFlight.get(id)
  if (existing) return existing

  // Un solo diálogo a la vez; `runApproval` nunca rechaza, así que la cola no se rompe.
  const run = queueTail.then(() => runApproval(host, id))
  queueTail = run
  inFlight.set(id, run)
  void run.finally(() => inFlight.delete(id))
  return run
}
