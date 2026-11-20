import { useEffect, useState } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { fetchSettings } from '@/pages/today/requests'
import { describeError } from '@/services/api'
import { notify } from '@/services/notify'
import { updatePreferences, usePreferences } from '@/stores/preferences'
import { setWakeEnabled } from '@/stores/voice'
import { useMicDevices } from '@/voice/micDevices'
import { Rows, Section, SettingRow } from './settingsUi'

export function VoiceSection() {
  const [checked, setChecked] = useState<boolean | null>(null)
  const { micDeviceId } = usePreferences()
  const { inputs, split } = useMicDevices()
  // Una elección que ya no existe equivale a «Predeterminado» (el cliente cae a él).
  const selected = inputs.some((d) => d.id === micDeviceId) ? micDeviceId : ''

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
        <SettingRow
          title="Micrófono"
          description={
            split(selected)
              ? 'Esta entrada es de un dispositivo distinto al de la salida de audio predeterminada: puede que Drakter te hable por unos auriculares y te escuche por otro micrófono.'
              : 'Entrada de audio que usa Drakter para oírte.'
          }
          labelFor="setting-mic"
        >
          {(describedBy) => (
            <Select
              value={selected === '' ? 'default' : selected}
              onValueChange={(value) => updatePreferences({ micDeviceId: value === 'default' ? '' : value })}
            >
              <SelectTrigger id="setting-mic" aria-describedby={describedBy} className="w-64">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="default">Predeterminado del sistema</SelectItem>
                {inputs.map((d) => (
                  <SelectItem key={d.id} value={d.id}>
                    {d.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </SettingRow>
      </Rows>
    </Section>
  )
}
