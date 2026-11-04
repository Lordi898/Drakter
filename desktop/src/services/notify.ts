import { toast } from 'sonner'
import { addNotification, type NotificationInput } from '@/stores/notifications'
import { getPreferences } from '@/stores/preferences'

const toastByTone = {
  info: toast.info,
  success: toast.success,
  warning: toast.warning,
  error: toast.error
} as const

export function notify(input: NotificationInput): void {
  addNotification(input)
  toastByTone[input.tone](input.title, input.body === undefined ? undefined : { description: input.body })

  if (!input.desktop || !getPreferences().desktopNotifications) return
  // En un navegador normal (vista previa) el puente no existe aunque el tipo diga lo contrario.
  if (typeof window.drakter === 'undefined') return
  window.drakter
    .showDesktopNotification({ title: input.title, ...(input.body === undefined ? {} : { body: input.body }) })
    .catch((error: unknown) => {
      console.warn('No se pudo mostrar la notificación de escritorio.', error)
    })
}
