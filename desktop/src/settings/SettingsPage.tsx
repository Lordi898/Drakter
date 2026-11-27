import { useEffect, useState } from 'react'
import { PageHeader } from '@/components/PageHeader'
import { ErrorBoundary } from '@/components/errors/ErrorBoundary'
import { ErrorProbe } from '@/components/errors/ErrorProbe'
import { FloatingSection } from '@/floating/FloatingSection'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { RemindersNotice } from '@/modules/notifications'
import { fetchSettingsStatus } from '@/pages/today/requests'
import { notify } from '@/services/notify'
import { updatePreferences, usePreferences, type ThemePreference } from '@/stores/preferences'
import { AgentStatusSection, DevModeBanner, isDevActive } from './AgentStatusSection'
import { AvatarSection } from './AvatarSection'
import { BackupsSection } from './BackupsSection'
import { JarvisSection } from './JarvisSection'
import { Rows, Section, SettingRow, useLoad } from './settingsUi'
import { TimezoneSection } from './TimezoneSection'
import { VoiceSection } from './VoiceSection'
import type { AppInfo } from '../../electron/shared/bridge'

const THEME_OPTIONS: readonly {
  readonly value: ThemePreference
  readonly label: string
}[] = [
  { value: 'system', label: 'Según el sistema' },
  { value: 'light', label: 'Claro' },
  { value: 'dark', label: 'Oscuro' }
]

function isThemePreference(value: string): value is ThemePreference {
  return THEME_OPTIONS.some((option) => option.value === value)
}

type AppInfoState =
  | { readonly status: 'unavailable' }
  | { readonly status: 'loading' }
  | { readonly status: 'error' }
  | { readonly status: 'ready'; readonly info: AppInfo }

function useAppInfo(): AppInfoState {
  const [state, setState] = useState<AppInfoState>(() =>
    typeof window.drakter === 'undefined' ? { status: 'unavailable' } : { status: 'loading' }
  )

  useEffect(() => {
    if (typeof window.drakter === 'undefined') return
    let cancelled = false
    window.drakter
      .getAppInfo()
      .then((info) => {
        if (!cancelled) setState({ status: 'ready', info })
      })
      .catch(() => {
        if (!cancelled) setState({ status: 'error' })
      })
    return () => {
      cancelled = true
    }
  }, [])

  return state
}

function AboutRows({ state }: { readonly state: AppInfoState }) {
  if (state.status !== 'ready') {
    const message =
      state.status === 'unavailable'
        ? 'Disponible solo en la aplicación de escritorio'
        : state.status === 'loading'
          ? 'Cargando la información de la aplicación…'
          : 'No se pudo leer la información de la aplicación. Reinicia Drakter e inténtalo de nuevo.'
    return (
      <SettingRow title="Información de la aplicación">
        <p
          className="max-w-[40ch] text-right text-sm text-muted-foreground"
          role={state.status === 'error' ? 'alert' : undefined}
        >
          {message}
        </p>
      </SettingRow>
    )
  }
  const { info } = state
  const entries: readonly (readonly [string, string])[] = [
    ['Versión de Drakter', info.appVersion],
    ['Electron', info.electronVersion],
    ['Chromium', info.chromeVersion],
    ['Node', info.nodeVersion],
    ['Plataforma', info.platform]
  ]
  return (
    <Rows>
      {entries.map(([label, value]) => (
        <SettingRow key={label} title={label}>
          <span className="text-sm text-muted-foreground">{value}</span>
        </SettingRow>
      ))}
    </Rows>
  )
}

export function SettingsPage() {
  const preferences = usePreferences()
  const appInfo = useAppInfo()
  const [status, reloadStatus] = useLoad(fetchSettingsStatus)

  return (
    <div className="mx-auto w-full max-w-3xl">
      {isDevActive(status) ? <DevModeBanner /> : null}
      <PageHeader
        title="Configuración"
        summary="La apariencia y los avisos se guardan en este equipo. La zona horaria y las copias dependen del servicio local de Drakter."
      />

      <Section title="Apariencia">
        <Rows>
          <SettingRow title="Tema" description="Elige el aspecto de la ventana." labelFor="setting-theme">
            {(describedBy) => (
              <Select
                value={preferences.theme}
                onValueChange={(value) => {
                  if (isThemePreference(value)) updatePreferences({ theme: value })
                }}
              >
                <SelectTrigger id="setting-theme" aria-describedby={describedBy} className="w-48">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {THEME_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </SettingRow>
          <SettingRow
            title="Reducir movimiento"
            description="Quita las animaciones y transiciones de la interfaz. Drakter ya respeta la preferencia de tu sistema."
            labelFor="setting-reduce-motion"
          >
            {(describedBy) => (
              <Switch
                id="setting-reduce-motion"
                aria-describedby={describedBy}
                checked={preferences.reduceMotion}
                onCheckedChange={(checked) => updatePreferences({ reduceMotion: checked })}
              />
            )}
          </SettingRow>
        </Rows>
      </Section>

      <AvatarSection />

      <JarvisSection />

      <FloatingSection />

      <Section title="Notificaciones">
        <RemindersNotice />
        <Rows>
          <SettingRow
            title="Avisos de escritorio"
            description="Muestra los avisos importantes también fuera de la ventana de Drakter."
            labelFor="setting-desktop-notifications"
          >
            {(describedBy) => (
              <Switch
                id="setting-desktop-notifications"
                aria-describedby={describedBy}
                checked={preferences.desktopNotifications}
                onCheckedChange={(checked) => updatePreferences({ desktopNotifications: checked })}
              />
            )}
          </SettingRow>
          <SettingRow title="Notificación de prueba" description="Comprueba cómo te llegan los avisos.">
            <Button
              variant="outline"
              onClick={() =>
                notify({
                  tone: 'info',
                  title: 'Notificación de prueba',
                  desktop: true
                })
              }
            >
              Enviar notificación de prueba
            </Button>
          </SettingRow>
        </Rows>
      </Section>

      <AgentStatusSection state={status} onRetry={reloadStatus} />

      <VoiceSection />

      <TimezoneSection />

      <BackupsSection />

      <Section title="Acerca de Drakter">
        <AboutRows state={appInfo} />
      </Section>

      {appInfo.status === 'ready' && !appInfo.info.packaged ? (
        <Section title="Diagnóstico">
          <SettingRow
            title="Probar la gestión de errores"
            description="Provoca un fallo controlado para ver cómo lo recoge Drakter."
          >
            <ErrorBoundary scope="diagnóstico">
              <ErrorProbe />
            </ErrorBoundary>
          </SettingRow>
        </Section>
      ) : null}
    </div>
  )
}
