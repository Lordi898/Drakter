import { useEffect, useState } from 'react'
import { Switch } from '@/components/ui/switch'
import { fetchSettings } from '@/pages/today/requests'
import { describeError } from '@/services/api'
import { notify } from '@/services/notify'
import { setWakeEnabled } from '@/stores/voice'
import { Rows, Section, SettingRow } from './settingsUi'

export function VoiceSection() {
  const [checked, setChecked] = useState<boolean | null>(null)

  useEffect(() => {
    let cancelled = false
    fetchSettings()
      .then(({ items }) => {
        if (cancelled) return
        const value = items.find((item) => item.key === 'voice_wake_enabled')?.value
        setChecked(value === undefined ? true : value === 'true')
      })
      .catch(() => {
        if (!cancelled) setChecked(null)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const change = (next: boolean) => {
    const previous = checked
    setChecked(next)
    setWakeEnabled(next).catch((error: unknown) => {
      setChecked(previous)
      notify({
        tone: 'error',
        title: 'No se pudo guardar el ajuste de voz',
        body: describeError(error, 'Inténtalo de nuevo.')
      })
    })
  }

  return (
    <Section title="Voz">
      <Rows>
        <SettingRow
          title='Activar con la palabra Jarvis'
          description="Drakter empieza a escuchar cuando dices la palabra de activación."
          labelFor="setting-wake-word"
        >
          {(describedBy) => (
            <Switch
              id="setting-wake-word"
              aria-describedby={describedBy}
              disabled={checked === null}
              checked={checked ?? false}
              onCheckedChange={change}
            />
          )}
        </SettingRow>
      </Rows>
    </Section>
  )
}
