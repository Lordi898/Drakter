import { CircleUserRound } from 'lucide-react'
import type { ReactNode } from 'react'
import { CharacterSlot } from '@/character/CharacterSlot'
import { DEFAULT_AVATAR_ID, listAvatars, NO_AVATAR, resolveAvatar } from '@/character/avatars/registry'
import { cn } from '@/lib/utils'
import { useDrakterState } from '@/stores/agent'
import { updatePreferences, usePreferences } from '@/stores/preferences'
import { Section } from './settingsUi'

interface ChoiceProps {
  readonly value: string
  readonly checked: boolean
  readonly name: string
  readonly description: string
  readonly picture: ReactNode
}

/** Tarjeta de un grupo de radios nativo: flechas, Tab y lector de pantalla funcionan sin más. */
function Choice({ value, checked, name, description, picture }: ChoiceProps) {
  return (
    <label
      className={cn(
        'group flex cursor-pointer flex-col gap-2 rounded-xl border p-2 transition-colors',
        'has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring',
        checked ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted/60'
      )}
      title={description}
    >
      <input
        type="radio"
        name="setting-avatar"
        value={value}
        checked={checked}
        onChange={() => updatePreferences({ avatarId: value })}
        className="sr-only"
        aria-describedby={`avatar-desc-${value}`}
      />
      <div className="aspect-square overflow-hidden rounded-lg bg-muted">{picture}</div>
      <span className="truncate text-sm font-medium text-foreground">{name}</span>
      <span id={`avatar-desc-${value}`} className="sr-only">
        {description}
      </span>
    </label>
  )
}

/** Elegir el avatar 3D (o el personaje clásico), con miniaturas y una vista previa en vivo. */
export function AvatarSection() {
  const { avatarId } = usePreferences()
  const state = useDrakterState()
  const active = resolveAvatar(avatarId)
  // «Clásico» solo se marca si se eligió de verdad: con un avatar aún no portado no hay tarjeta marcada y,
  // al pulsar «Clásico», se guarda `none` (si no, al portarse ese avatar cambiaría sin que el usuario lo pidiera).
  const selected = active ? active.meta.id : avatarId === NO_AVATAR ? NO_AVATAR : null
  const pending = !active && avatarId !== NO_AVATAR

  return (
    <Section title="Avatar">
      <div className="grid gap-6 py-4 md:grid-cols-[minmax(0,1fr)_14rem]">
        <div>
          <p className="text-sm text-muted-foreground">
            El personaje que te acompaña en Drakter y en el modo Jarvis. También puedes pedirlo por voz.
          </p>
          {pending ? (
            <p className="mt-2 text-sm text-muted-foreground">
              {avatarId === DEFAULT_AVATAR_ID ? 'El avatar predeterminado' : 'El avatar elegido'} aún no está
              disponible en esta versión; mientras tanto se ve el personaje clásico y aparecerá solo cuando llegue.
              Si prefieres quedarte con el clásico, elígelo abajo.
            </p>
          ) : null}
          <div role="radiogroup" aria-label="Avatar" className="mt-4 grid grid-cols-[repeat(auto-fill,minmax(7.5rem,1fr))] gap-3">
            <Choice
              value={NO_AVATAR}
              checked={selected === NO_AVATAR}
              name="Clásico"
              description="El personaje clásico, sin 3D: tu .riv si lo tienes o la ilustración."
              picture={
                <div className="flex size-full items-center justify-center text-muted-foreground">
                  <CircleUserRound aria-hidden="true" className="size-12" strokeWidth={1.25} />
                </div>
              }
            />
            {listAvatars().map(({ meta }) => (
              <Choice
                key={meta.id}
                value={meta.id}
                checked={selected === meta.id}
                name={meta.name}
                description={meta.description}
                picture={<img src={meta.thumbnail} alt="" className="size-full object-cover" draggable={false} />}
              />
            ))}
          </div>
        </div>
        <div className="flex flex-col items-center gap-2">
          <p className="self-start text-sm font-medium text-foreground">Vista previa</p>
          <div className="w-56">
            <CharacterSlot state={state} size="expanded" />
          </div>
        </div>
      </div>
    </Section>
  )
}
