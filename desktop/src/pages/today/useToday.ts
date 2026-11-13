import { useCallback, useEffect, useRef, useState } from 'react'
import { useLinkStatus } from '@/stores/connection'
import type { TodayResponse } from './contract'
import { dayInZone } from './format'
import { fetchSettings, fetchToday } from './requests'

const MIDNIGHT_CHECK_MS = 60_000

export interface UseToday {
  readonly data: TodayResponse | null
  readonly error: unknown
  /** Hay una petición en curso (también durante recargas, con `data` visible). */
  readonly loading: boolean
  readonly reload: () => void
}

export function useToday(): UseToday {
  const [data, setData] = useState<TodayResponse | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [loading, setLoading] = useState(true)
  const requestId = useRef(0)
  const dataRef = useRef<TodayResponse | null>(null)

  const load = useCallback(async () => {
    const id = ++requestId.current
    setLoading(true)
    let timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone
    try {
      const settings = await fetchSettings()
      const configured = settings.items.find((item) => item.key === 'default_timezone')?.value
      if (configured) timeZone = configured
    } catch {
      // Sin ajustes se usa la zona del sistema: no es un error de pantalla.
    }
    if (id !== requestId.current) return
    try {
      const next = await fetchToday(timeZone)
      if (id !== requestId.current) return
      dataRef.current = next
      setData(next)
      setError(null)
    } catch (caught) {
      if (id !== requestId.current) return
      setError(caught)
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    void load()
    const onFocus = (): void => void load()
    const timer = window.setInterval(() => {
      const current = dataRef.current
      if (current && dayInZone(current.timezone) !== current.date) void load()
    }, MIDNIGHT_CHECK_MS)
    window.addEventListener('focus', onFocus)
    return () => {
      requestId.current += 1
      window.clearInterval(timer)
      window.removeEventListener('focus', onFocus)
    }
  }, [load])

  // Hoy es la pantalla inicial: se monta antes de que el servicio local conecte.
  // Al pasar a 'open' (arranque o reconexión) se recarga sin esperar al foco.
  const link = useLinkStatus()
  const previousLink = useRef(link)
  useEffect(() => {
    if (link === 'open' && previousLink.current !== 'open') void load()
    previousLink.current = link
  }, [link, load])

  const reload = useCallback(() => void load(), [load])
  return { data, error, loading, reload }
}
