import { useState } from 'react'
import { Button } from '@/components/ui/button'
import type { BackupItem } from '@/pages/today/contract'
import { createBackup, fetchBackups } from '@/pages/today/requests'
import { describeError } from '@/services/api'
import { notify } from '@/services/notify'
import { LoadFailure } from './AgentStatusSection'
import { Rows, Section, SettingRow, useLoad } from './settingsUi'

const dateFormat = new Intl.DateTimeFormat('es-ES', {
  dateStyle: 'long',
  timeStyle: 'short'
})

function formatDate(iso: string): string {
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? iso : dateFormat.format(date)
}

function formatSize(bytes: number): string {
  const mb = bytes / (1024 * 1024)
  return `${mb.toLocaleString('es-ES', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} MB`
}

function labelText(label: string): string {
  if (label === 'manual') return 'Manual'
  if (label === 'pre-restore') return 'Antes de restaurar'
  return label
}

const loadBackups = () => fetchBackups().then((response) => response.items)

export function BackupsSection() {
  const [state, reload, setItems] = useLoad<readonly BackupItem[]>(loadBackups)
  const [busy, setBusy] = useState(false)

  const create = () => {
    if (busy) return
    setBusy(true)
    createBackup()
      .then(() => {
        notify({ tone: 'success', title: 'Copia de seguridad creada' })
        return loadBackups().then(setItems)
      })
      .catch((error: unknown) => {
        notify({
          tone: 'error',
          title: 'No se pudo crear la copia de seguridad',
          body: describeError(error, 'Inténtalo de nuevo.')
        })
      })
      .finally(() => setBusy(false))
  }

  return (
    <Section title="Copias de seguridad">
      <SettingRow
        title="Crear copia ahora"
        description="Restaurar una copia se hará desde aquí cuando esté disponible con confirmación."
      >
        <Button variant="outline" onClick={create} disabled={busy} aria-busy={busy}>
          {busy ? 'Creando copia…' : 'Crear copia ahora'}
        </Button>
      </SettingRow>
      {state.status === 'loading' ? <SettingRow title="Leyendo las copias…" /> : null}
      {state.status === 'error' ? (
        <LoadFailure error={state.error} fallback="No se pudieron leer las copias." onRetry={reload} />
      ) : null}
      {state.status === 'ready' && state.data.length === 0 ? <SettingRow title="Aún no hay copias." /> : null}
      {state.status === 'ready' && state.data.length > 0 ? (
        <Rows>
          {state.data.map((backup) => (
            <SettingRow key={backup.name} title={formatDate(backup.created_at)} description={labelText(backup.label)}>
              <span className="text-sm text-muted-foreground">{formatSize(backup.size_bytes)}</span>
            </SettingRow>
          ))}
        </Rows>
      ) : null}
    </Section>
  )
}
