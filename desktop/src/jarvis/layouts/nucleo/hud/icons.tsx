import type { ReactElement } from 'react'

export type IconKey = 'nucleo' | 'hoy' | 'tareas' | 'habitos' | 'calendario' | 'relaciones' | 'almacen' | 'ajustes'

const PATHS: Readonly<Record<IconKey, ReactElement>> = {
  nucleo: <><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="3.2" className="f" /></>,
  hoy: <><circle cx="12" cy="12" r="9" /><path d="M12 12V5M12 12l4.5 2.6" /></>,
  tareas: <><ellipse cx="12" cy="12" rx="9.5" ry="4.6" transform="rotate(-24 12 12)" /><circle cx="12" cy="12" r="2.4" className="f" /><circle cx="19.6" cy="7.4" r="1.6" className="f" /></>,
  habitos: <><path d="M12 3a9 9 0 1 1-9 9" /><path d="M12 6.5A5.5 5.5 0 1 1 6.5 12" /><circle cx="12" cy="12" r="1.6" className="f" /></>,
  calendario: <><circle cx="12" cy="12" r="9" /><path d="M12 3v4M19 7.5l-3.2 2.2M20.8 14.4l-3.9-.9M15.6 20.2l-1.7-3.6M8.4 20.2l1.7-3.6M3.2 14.4l3.9-.9M5 7.5l3.2 2.2" /></>,
  relaciones: <><path d="M6 7l11 3M17 10l-6 8M6 7l5 11" /><circle cx="6" cy="7" r="2.2" className="f" /><circle cx="17" cy="10" r="2.6" className="f" /><circle cx="11" cy="18" r="2" className="f" /></>,
  almacen: <><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="4" /><path d="M12 3v5M20.6 14.8l-4.8-1.6M5 17.6l3.9-3" /></>,
  ajustes: <><circle cx="12" cy="12" r="3" /><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1" /></>
}

export function Icon({ k }: { readonly k: IconKey }) {
  return <svg viewBox="0 0 24 24" className="ic" aria-hidden="true">{PATHS[k]}</svg>
}
