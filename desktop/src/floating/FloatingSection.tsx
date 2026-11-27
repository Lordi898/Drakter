import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { fetchSettings, saveSetting } from '@/pages/today/requests'
import { describeError } from '@/services/api'
import { notify } from '@/services/notify'
import { Rows, Section, SettingRow } from '@/settings/settingsUi'
import { FLOATING_SHORTCUT_LABEL } from './shortcut'
import { requestFloating, setFloatingHelpOpen, useFloating } from './store'

/** Claves del backend (CONTRACT §15, B2) y sus valores por defecto. */
const SIZE_KEY = 'floating_avatar_size'
const SOUND_KEY = 'floating_sound'
const HANDS_KEY = 'floating_hands_enabled'
const SCREEN_KEY = 'floating_screen_enabled'

type AvatarSize = 'default' | 'small' | 'cursor'
const SIZE_OPTIONS: readonly { readonly value: AvatarSize; readonly label: string }[] = [
  { value: 'default', label: 'Normal' },
  { value: 'small', label: 'Pequeño' },
  { value: 'cursor', label: 'Junto al cursor' }
]
const isSize = (value: string): value is AvatarSize => SIZE_OPTIONS.some((o) => o.value === value)

interface FloatingSettings {
  readonly size: AvatarSize
  readonly sound: boolean
  readonly hands: boolean
  readonly screen: boolean
}
const DEFAULTS: FloatingSettings = { size: 'default', sound: true, hands: false, screen: false }

function parse(items: readonly { readonly key: string; readonly value: string | null }[]): FloatingSettings {
  const get = (key: string): string | null => items.find((item) => item.key === key)?.value ?? null
  const size = get(SIZE_KEY)
  const sound = get(SOUND_KEY)
  const hands = get(HANDS_KEY)
  const screen = get(SCREEN_KEY)
  return {
    size: size !== null && isSize(size) ? size : DEFAULTS.size,
    sound: sound === null ? DEFAULTS.sound : sound === 'true',
    hands: hands === null ? DEFAULTS.hands : hands === 'true',
    screen: screen === null ? DEFAULTS.screen : screen === 'true'
  }
}

function StatusRow() {
  const { state } = useFloating()
  const description = !state
    ? 'Comprobando la extensión de GNOME…'
    : !state.available
      ? 'No disponible: falta preparar la extensión de GNOME «Drakter Companion».'
      : state.active
        ? 'Activo. Drakter flota sobre tus apps; Super+Alt+D lo quita.'
        : `Drakter flota sobre tus apps, sigue al cursor y te señala lo que hay en pantalla. También con ${FLOATING_SHORTCUT_LABEL} o Super+Alt+D.`
  return (
    <SettingRow title="Modo flotante" description={description}>
      {state && !state.available ? (
        <Button variant="outline" onClick={() => setFloatingHelpOpen(true)}>
          Cómo instalarlo
        </Button>
      ) : (
        <Button variant="outline" disabled={!state || state.busy !== null} onClick={() => requestFloating('toggle')}>
          {state?.active ? 'Quitar modo flotante' : 'Activar modo flotante'}
        </Button>
      )}
    </SettingRow>
  )
}

/** Sección «Modo flotante» de Ajustes. Los ajustes viven en el backend; main los lee al activar. */
export function FloatingSection() {
  const [settings, setSettings] = useState<FloatingSettings | null>(null)

  useEffect(() => {
    let cancelled = false
    fetchSettings()
      .then(({ items }) => {
        if (!cancelled) setSettings(parse(items))
      })
      .catch(() => {
        if (!cancelled) setSettings(null)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const save = (key: string, value: string, next: FloatingSettings): void => {
    const previous = settings
    setSettings(next)
    saveSetting(key, value).catch((error: unknown) => {
      setSettings(previous)
      notify({
        tone: 'error',
        title: 'No se pudo guardar el ajuste del modo flotante',
        body: describeError(error, 'Inténtalo de nuevo.')
      })
    })
  }

  const disabled = settings === null
  const current = settings ?? DEFAULTS

  return (
    <Section title="Modo flotante">
      <Rows>
        <StatusRow />
        <SettingRow
          title="Tamaño del avatar"
          description="Cómo de grande se ve JARVIS mientras flota. Se aplica la próxima vez que actives el modo."
          labelFor="setting-floating-size"
        >
          {(describedBy) => (
            <Select
              value={current.size}
              disabled={disabled}
              onValueChange={(value) => {
                if (isSize(value)) save(SIZE_KEY, value, { ...current, size: value })
              }}
            >
              <SelectTrigger id="setting-floating-size" aria-describedby={describedBy} className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SIZE_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </SettingRow>
        <SettingRow
          title="Sonidos del avatar"
          description="Pequeños sonidos al aparecer, señalar y terminar. La voz de Drakter no cambia."
          labelFor="setting-floating-sound"
        >
          {(describedBy) => (
            <Switch
              id="setting-floating-sound"
              aria-describedby={describedBy}
              disabled={disabled}
              checked={current.sound}
              onCheckedChange={(checked) => save(SOUND_KEY, String(checked), { ...current, sound: checked })}
            />
          )}
        </SettingRow>
        <SettingRow
          title="Dejar que Drakter vea mi pantalla"
          description="Con esto activado, Drakter puede hacer capturas de tu pantalla y leer el texto de tus ventanas, pero solo con el modo flotante activo y cuando la conversación lo pide (por ejemplo, «¿dónde pulso para exportar?»). Las capturas se envían al modelo de IA para que te responda y no se guardan en tu equipo."
          labelFor="setting-floating-screen"
        >
          {(describedBy) => (
            <Switch
              id="setting-floating-screen"
              aria-describedby={describedBy}
              disabled={disabled}
              checked={current.screen}
              onCheckedChange={(checked) => save(SCREEN_KEY, String(checked), { ...current, screen: checked })}
            />
          )}
        </SettingRow>
        <SettingRow
          title="Dejar que Drakter use mis apps"
          description="Con esto activado, Drakter puede pulsar y escribir en otras ventanas cuando se lo pidas. Antes de cualquier paso arriesgado te pide permiso, y nunca toca terminales, gestores de contraseñas ni los ajustes del sistema."
          labelFor="setting-floating-hands"
        >
          {(describedBy) => (
            <Switch
              id="setting-floating-hands"
              aria-describedby={describedBy}
              disabled={disabled}
              checked={current.hands}
              onCheckedChange={(checked) => save(HANDS_KEY, String(checked), { ...current, hands: checked })}
            />
          )}
        </SettingRow>
      </Rows>
    </Section>
  )
}
