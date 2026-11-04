import { useMemo, useState } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { fetchSettings, saveSetting } from '@/pages/today/requests'
import { describeError } from '@/services/api'
import { notify } from '@/services/notify'
import { LoadFailure } from './AgentStatusSection'
import { Section, SettingRow, useLoad } from './settingsUi'

const SYSTEM_VALUE = '__system__'

function systemZone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone
}

function supportedZones(): readonly string[] {
  const intl = Intl as unknown as {
    supportedValuesOf?: (key: string) => string[]
  }
  return intl.supportedValuesOf ? intl.supportedValuesOf('timeZone') : []
}

function TimezoneRow({ persisted, initial }: { readonly persisted: boolean; readonly initial: string | null }) {
  const [saved, setSaved] = useState<string | null>(initial)
  const [busy, setBusy] = useState(false)
  const system = systemZone()

  const zones = useMemo(() => {
    const all = new Set(supportedZones())
    all.add(system)
    if (saved !== null) all.add(saved)
    return [...all].sort()
  }, [system, saved])

  const change = (value: string) => {
    if (value === SYSTEM_VALUE || value === saved || busy) return
    setBusy(true)
    saveSetting('default_timezone', value)
      .then(() => {
        setSaved(value)
        notify({
          tone: 'success',
          title: 'Zona horaria guardada',
          body: value
        })
      })
      .catch((error: unknown) => {
        notify({
          tone: 'error',
          title: 'No se pudo guardar la zona horaria',
          body: describeError(error, 'Inténtalo de nuevo.')
        })
      })
      .finally(() => setBusy(false))
  }

  return (
    <SettingRow
      title="Zona horaria"
      description={
        persisted
          ? 'Se usa para decidir qué es hoy en tu agenda.'
          : 'Se podrá guardar cuando el espacio de trabajo esté listo.'
      }
      labelFor="setting-timezone"
    >
      {(describedBy) => (
        <Select value={saved ?? SYSTEM_VALUE} onValueChange={change} disabled={!persisted || busy}>
          <SelectTrigger id="setting-timezone" aria-describedby={describedBy} className="w-64">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {saved === null ? <SelectItem value={SYSTEM_VALUE}>{`Según el sistema (${system})`}</SelectItem> : null}
            {zones.map((zone) => (
              <SelectItem key={zone} value={zone}>
                {zone}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
    </SettingRow>
  )
}

export function TimezoneSection() {
  const [state, reload] = useLoad(fetchSettings)
  return (
    <Section title="Zona horaria">
      {state.status === 'loading' ? <SettingRow title="Leyendo los ajustes…" /> : null}
      {state.status === 'error' ? (
        <LoadFailure error={state.error} fallback="No se pudieron leer los ajustes." onRetry={reload} />
      ) : null}
      {state.status === 'ready' ? (
        <TimezoneRow
          persisted={state.data.persisted}
          initial={state.data.items.find((item) => item.key === 'default_timezone')?.value ?? null}
        />
      ) : null}
    </Section>
  )
}
