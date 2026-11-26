/**
 * Alertas del Visor: las notificaciones nuevas de la app (`stores/notifications`: recordatorios del
 * backend, resultados de acciones del HUD…) entran con un barrido y se retiran solas a los 6 s.
 * Solo las que llegan con el Visor abierto; como mucho tres a la vez. Sin animación infinita.
 * Las confirmaciones NO se pintan aquí: las muestra el aviso común de la app (encima de cualquier
 * interfaz), que abre el diálogo nativo de main (CLAUDE.md §8: un único aviso).
 */
import { useEffect, useRef, useState } from 'react'
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
