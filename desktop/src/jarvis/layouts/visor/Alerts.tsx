/**
 * Alertas del Visor: las notificaciones nuevas de la app (`stores/notifications`: recordatorios del
 * backend, resultados de acciones del HUD…) entran con un barrido y se retiran solas a los 6 s.
 * Solo las que llegan con el Visor abierto; como mucho tres a la vez. Sin animación infinita.
 */
import { useEffect, useRef, useState, type MouseEvent } from 'react'
import { reviewConfirmation, useConfirmations } from '@/stores/confirmations'
import { useNotifications, type AppNotification } from '@/stores/notifications'

const SHOW_MS = 6000
const MAX = 3

export function Alerts() {
  const all = useNotifications()
  const seen = useRef<Set<string> | null>(null)
  const [shown, setShown] = useState<readonly AppNotification[]>([])

  useEffect(() => {
    if (seen.current === null) { seen.current = new Set(all.map((n) => n.id)); return } // las previas no se anuncian
    const fresh = all.filter((n) => !seen.current!.has(n.id))
    if (!fresh.length) return
    for (const n of fresh) seen.current.add(n.id)
    setShown((s) => [...fresh, ...s].slice(0, MAX)) // el store ya va de la más nueva a la más antigua
    const ids = fresh.map((n) => n.id)
    window.setTimeout(() => setShown((s) => s.filter((n) => !ids.includes(n.id))), SHOW_MS)
  }, [all])

  return (
    <div className="jv-visor-alerts">
      <Confirmations />
      <div role="status" aria-live="polite" className="jv-visor-alerts-list">
      {shown.map((n) => (
        <div key={n.id} className={`jv-visor-alert ${n.tone}`}>
          <i className="sw" aria-hidden="true" />
          <b>{n.title}</b>
          {n.body && <span>{n.body}</span>}
        </div>
      ))}
      </div>
    </div>
  )
}

/**
 * Confirmaciones pendientes con la piel del Visor (la lista común de la app queda detrás del lienzo).
 * Solo «Revisar»: la decisión la toma el diálogo nativo de main (`reviewConfirmation` con el gesto real);
 * aquí no hay, ni debe haber, ningún control para aprobar o rechazar. Sin reloj por segundo: se muestra
 * la hora a la que caduca.
 */
export function Confirmations() {
  const items = useConfirmations()
  const [busy, setBusy] = useState<string | null>(null)
  const [problem, setProblem] = useState<string | null>(null)
  if (items.length === 0) return null
  const review = (id: string, e: MouseEvent<HTMLButtonElement>): void => {
    setBusy(id); setProblem(null)
    reviewConfirmation(id, e)
      .then((o) => { if (o === 'conflict') setProblem('Los elementos han cambiado; la acción no se ha ejecutado.'); else if (o === 'failed') setProblem('No se ha podido completar la decisión.') })
      .catch(() => setProblem('No se ha podido abrir la revisión. Inténtalo de nuevo.'))
      .finally(() => setBusy(null))
  }
  return (
    <ul className="jv-visor-confirms" aria-label="Confirmaciones pendientes">
      {items.map((c) => (
        <li key={c.action_id} className="jv-visor-alert warning">
          <b>Drakter necesita tu confirmación</b>
          <span>{c.summary.slice(0, 240)}</span>
          <small>{typeof c.affected_count === 'number' ? `Afecta a ${c.affected_count}  ·  ` : ''}caduca a las {new Date(c.expires_at).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}</small>
          <button type="button" disabled={busy !== null} data-lock="Revisar en el diálogo de confirmación" onClick={(e) => review(c.action_id, e)}>{busy === c.action_id ? 'Revisando…' : 'Revisar'}</button>
        </li>
      ))}
      {problem && <li className="jv-visor-alert error" role="alert"><b>{problem}</b></li>}
    </ul>
  )
}
