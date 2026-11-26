import { JARVIS_LAYOUTS } from '@/app/jarvisLayouts'
import { UI_MODE_SHORTCUT_LABEL } from '@/app/useGlobalShortcuts'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import {
  JARVIS_LAYOUT_CHOICES,
  updatePreferences,
  usePreferences,
  type JarvisLayoutChoice,
  type JarvisQuality,
  type JarvisStartup
} from '@/stores/preferences'
import { getUiMode, jarvisAvailable, prefetchJarvis, requestUiMode } from '@/stores/uiMode'
import { Rows, Section, SettingRow } from './settingsUi'

const STARTUP_OPTIONS: readonly { readonly value: JarvisStartup; readonly label: string }[] = [
  { value: 'drakter', label: 'Siempre en Drakter' },
  { value: 'last', label: 'Recordar el último modo' }
]

const QUALITY_OPTIONS: readonly { readonly value: JarvisQuality; readonly label: string }[] = [
  { value: 'auto', label: 'Automática' },
  { value: 'cine', label: 'Cine' },
  { value: 'equilibrado', label: 'Equilibrado' },
  { value: 'ahorro', label: 'Ahorro' }
]

const isStartup = (value: string): value is JarvisStartup => STARTUP_OPTIONS.some((o) => o.value === value)
const isLayout = (value: string): value is JarvisLayoutChoice => (JARVIS_LAYOUT_CHOICES as readonly string[]).includes(value)
const isQuality = (value: string): value is JarvisQuality => QUALITY_OPTIONS.some((o) => o.value === value)

export function JarvisSection() {
  const preferences = usePreferences()
  if (!jarvisAvailable()) return null

  return (
    <Section title="Modo Jarvis">
      <Rows>
        <SettingRow
          title="Abrir el modo Jarvis"
          description={`Interfaz holográfica con los mismos datos. También con ${UI_MODE_SHORTCUT_LABEL}.`}
        >
          <Button
            variant="outline"
            onPointerEnter={prefetchJarvis}
            onFocus={prefetchJarvis}
            onClick={() => requestUiMode('jarvis', 'button')}
          >
            Abrir modo Jarvis
          </Button>
        </SettingRow>
        <SettingRow
          title="Interfaz"
          description="Cómo se ve el modo Jarvis. También desde el selector «Apariencia» de Jarvis o por voz («interfaz visor»)."
          labelFor="setting-jarvis-layout"
        >
          {(describedBy) => (
            <Select
              value={preferences.jarvisLayout}
              onValueChange={(value) => {
                if (isLayout(value)) updatePreferences({ jarvisLayout: value })
              }}
            >
              <SelectTrigger id="setting-jarvis-layout" aria-describedby={describedBy} className="w-56">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {JARVIS_LAYOUTS.map((layout) => (
                  <SelectItem key={layout.id} value={layout.id}>
                    {layout.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </SettingRow>
        <SettingRow
          title="Al arrancar"
          description="Drakter es siempre la interfaz de inicio, salvo que prefieras volver a la última que usaste."
          labelFor="setting-jarvis-startup"
        >
          {(describedBy) => (
            <Select
              value={preferences.jarvisStartup}
              onValueChange={(value) => {
                if (!isStartup(value)) return
                // Al empezar a recordar, se apunta el modo actual para no arrancar con uno antiguo.
                updatePreferences({ jarvisStartup: value, lastUiMode: getUiMode().mode })
              }}
            >
              <SelectTrigger id="setting-jarvis-startup" aria-describedby={describedBy} className="w-56">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STARTUP_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </SettingRow>
        <SettingRow
          title="Calidad gráfica"
          description="Automática la elige según tu gráfica. Ahorro gasta menos batería y procesador."
          labelFor="setting-jarvis-quality"
        >
          {(describedBy) => (
            <Select
              value={preferences.jarvisQuality}
              onValueChange={(value) => {
                if (isQuality(value)) updatePreferences({ jarvisQuality: value })
              }}
            >
              <SelectTrigger id="setting-jarvis-quality" aria-describedby={describedBy} className="w-56">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {QUALITY_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
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
