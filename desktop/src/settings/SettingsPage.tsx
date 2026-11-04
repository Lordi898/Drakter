import { useEffect, useState, type ReactNode } from 'react'
import { PageHeader } from '@/components/PageHeader'
import { ErrorBoundary } from '@/components/errors/ErrorBoundary'
import { ErrorProbe } from '@/components/errors/ErrorProbe'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import { notify } from '@/services/notify'
import { updatePreferences, usePreferences, type ThemePreference } from '@/stores/preferences'
import type { AppInfo } from '../../electron/shared/bridge'

const THEME_OPTIONS: readonly { readonly value: ThemePreference; readonly label: string }[] = [
  { value: 'system', label: 'Según el sistema' },
  { value: 'light', label: 'Claro' },
  { value: 'dark', label: 'Oscuro' }
]

function isThemePreference(value: string): value is ThemePreference {
  return THEME_OPTIONS.some((option) => option.value === value)
}

interface SettingRowProps {
  readonly title: string
  readonly description?: string
  readonly labelFor?: string
  readonly children?: ReactNode
}

function SettingRow({ title, description, labelFor, children }: SettingRowProps) {
  return (
    <div className="flex items-center justify-between gap-6 py-4">
      <div className="min-w-0">
        {labelFor ? (
          <Label htmlFor={labelFor} className="text-base">
            {title}
          </Label>
        ) : (
          <p className="text-base font-medium text-foreground">{title}</p>
        )}
        {description ? <p className="mt-1 text-sm text-muted-foreground">{description}</p> : null}
      </div>
      {children ? <div className="flex shrink-0 items-center">{children}</div> : null}
    </div>
  )
}

function Section({ title, children }: { readonly title: string; readonly children: ReactNode }) {
  return (
    <section className="pb-8">
      <h2 className="pb-2 text-lg font-semibold text-foreground">{title}</h2>
      <Separator />
      {children}
    </section>
  )
}

function Rows({ children }: { readonly children: ReactNode }) {
  const items = Array.isArray(children) ? children : [children]
  return (
    <div>
      {items.map((child, index) => (
        <div key={index}>
          {index > 0 ? <Separator /> : null}
          {child}
        </div>
      ))}
    </div>
  )
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
        <p className="max-w-[40ch] text-right text-sm text-muted-foreground" role={state.status === 'error' ? 'alert' : undefined}>
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

  return (
    <div className="mx-auto w-full max-w-3xl">
      <PageHeader
        title="Configuración"
        summary="Tus preferencias se guardan en este equipo al cambiarlas."
      />

      <Section title="Apariencia">
        <Rows>
          <SettingRow title="Tema" description="Elige el aspecto de la ventana." labelFor="setting-theme">
            <Select
              value={preferences.theme}
              onValueChange={(value) => {
                if (isThemePreference(value)) updatePreferences({ theme: value })
              }}
            >
              <SelectTrigger id="setting-theme" className="w-48">
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
          </SettingRow>
          <SettingRow
            title="Reducir movimiento"
            description="Quita las animaciones y transiciones de la interfaz."
            labelFor="setting-reduce-motion"
          >
            <Switch
              id="setting-reduce-motion"
              checked={preferences.reduceMotion}
              onCheckedChange={(checked) => updatePreferences({ reduceMotion: checked })}
            />
          </SettingRow>
        </Rows>
      </Section>

      <Section title="Notificaciones">
        <Rows>
          <SettingRow
            title="Avisos de escritorio"
            description="Muestra los avisos importantes también fuera de la ventana de Drakter."
            labelFor="setting-desktop-notifications"
          >
            <Switch
              id="setting-desktop-notifications"
              checked={preferences.desktopNotifications}
              onCheckedChange={(checked) => updatePreferences({ desktopNotifications: checked })}
            />
          </SettingRow>
          <SettingRow title="Notificación de prueba" description="Comprueba cómo te llegan los avisos.">
            <Button
              variant="outline"
              onClick={() => notify({ tone: 'info', title: 'Notificación de prueba', desktop: true })}
            >
              Enviar notificación de prueba
            </Button>
          </SettingRow>
        </Rows>
      </Section>

      <Section title="Conexión">
        <SettingRow
          title="Drakter aún no está conectado"
          description="Cuando Drakter esté conectado, los ajustes de conexión aparecerán aquí."
        />
      </Section>

      <Section title="Acerca de Drakter">
        <AboutRows state={appInfo} />
      </Section>

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
    </div>
  )
}
