import { Button } from '@/components/ui/button'
import { isDisconnected } from '@/pages/today/requests'
import type { SettingsStatus } from '@/pages/today/contract'
import { describeError } from '@/services/api'
import { Rows, Section, SettingRow, type Loadable } from './settingsUi'

export function DevModeBanner() {
  return (
    <div
      role="status"
      className="mb-6 rounded-[var(--radius)] border border-ambar bg-ambar/15 px-4 py-3 text-sm font-medium text-foreground"
    >
      Modo de desarrollo activo: las respuestas son simuladas, no vienen de un modelo real.
    </div>
  )
}

export function isDevActive(state: Loadable<SettingsStatus>): boolean {
  return state.status === 'ready' && state.data.agent.dev_mode === 'active'
}

export function LoadFailure({
  error,
  fallback,
  onRetry
}: {
  readonly error: unknown
  readonly fallback: string
  readonly onRetry: () => void
}) {
  const message = isDisconnected(error)
    ? 'El servicio local de Drakter no está conectado.'
    : describeError(error, fallback)
  return (
    <SettingRow title={message}>
      <Button variant="outline" onClick={onRetry}>
        Reintentar
      </Button>
    </SettingRow>
  )
}

function keyRow(key: SettingsStatus['agent']['key']) {
  if (key === 'configured') return <SettingRow title="Clave de API" description="Configurada" />
  if (key === 'missing') {
    return (
      <SettingRow
        title="Falta la clave de API"
        description="Añade ANTHROPIC_API_KEY a ~/.config/drakter/.env y reinicia Drakter."
      />
    )
  }
  return (
    <SettingRow
      title="Clave de API: no comprobada"
      description="Drakter no lee ese archivo; lo sabrá cuando el agente arranque."
    />
  )
}

function devRow(mode: SettingsStatus['agent']['dev_mode']) {
  if (mode === 'inactive') return <SettingRow title="Modo de desarrollo: desactivado" />
  if (mode === 'unknown') return <SettingRow title="Modo de desarrollo: no comprobado" />
  return null
}

export function AgentStatusSection({
  state,
  onRetry
}: {
  readonly state: Loadable<SettingsStatus>
  readonly onRetry: () => void
}) {
  if (state.status === 'loading') {
    return (
      <Section title="Conexión">
        <SettingRow title="Leyendo el estado de Drakter…" />
      </Section>
    )
  }
  if (state.status === 'error') {
    return (
      <Section title="Conexión">
        <LoadFailure error={state.error} fallback="No se pudo leer el estado." onRetry={onRetry} />
      </Section>
    )
  }
  const { agent, storage } = state.data
  return (
    <Section title="Conexión">
      {agent.dev_mode === 'active' ? (
        <div className="pt-4">
          <DevModeBanner />
        </div>
      ) : null}
      <Rows>
        {keyRow(agent.key)}
        {devRow(agent.dev_mode)}
        {agent.provider !== null ? (
          <SettingRow title="Proveedor">
            <span className="text-sm text-muted-foreground">{agent.provider}</span>
          </SettingRow>
        ) : null}
        {agent.model !== null ? (
          <SettingRow title="Modelo">
            <span className="text-sm text-muted-foreground">{agent.model}</span>
          </SettingRow>
        ) : null}
        <SettingRow title="Carpeta de datos">
          <span className="max-w-[32ch] break-all text-right font-mono text-sm text-muted-foreground">
            {storage.data_dir}
          </span>
        </SettingRow>
        {storage.schema_version !== null ? (
          <SettingRow title="Versión del esquema">
            <span className="text-sm text-muted-foreground">{storage.schema_version}</span>
          </SettingRow>
        ) : null}
      </Rows>
    </Section>
  )
}
