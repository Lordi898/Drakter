import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import type { CompanionStatus } from './api'
import { setFloatingHelpOpen, useFloating } from './store'

const INSTALL_COMMAND = './scripts/install-gnome-extension.sh'
const ENABLE_COMMAND = 'gnome-extensions enable drakter-companion@drakter'

const SUMMARY: Record<Exclude<CompanionStatus, 'ok'>, string> = {
  missing: 'Falta la extensión de GNOME «Drakter Companion». Sin ella Drakter no puede flotar encima de tus apps.',
  outdated: 'La extensión «Drakter Companion» instalada es antigua y no entiende esta versión de Drakter.',
  denied: 'La extensión «Drakter Companion» ha rechazado la conexión de Drakter.',
  unsupported_session: 'El modo flotante solo funciona en GNOME con Wayland, y esta sesión es de otro tipo.'
}

function Command({ children }: { readonly children: string }) {
  return (
    <code className="block rounded-md border bg-muted px-3 py-2 font-mono text-[13px] break-all text-foreground select-all">
      {children}
    </code>
  )
}

function Steps({ companion }: { readonly companion: CompanionStatus }) {
  if (companion === 'unsupported_session') {
    return (
      <p className="text-sm">
        Cierra la sesión y, en la pantalla de acceso, elige «GNOME» (no «GNOME sobre Xorg»). Después vuelve a abrir
        Drakter.
      </p>
    )
  }
  if (companion === 'denied') {
    return (
      <ol className="list-decimal space-y-2 pl-5 text-sm">
        <li>Cierra Drakter del todo (desde la bandeja, «Salir») y vuelve a abrirlo.</li>
        <li>
          Si sigue igual, reinstala la extensión desde la carpeta de Drakter:
          <Command>{INSTALL_COMMAND}</Command>
        </li>
        <li>Cierra la sesión de GNOME y vuelve a entrar.</li>
      </ol>
    )
  }
  return (
    <ol className="list-decimal space-y-2 pl-5 text-sm">
      <li>
        Abre una terminal en la carpeta de Drakter y {companion === 'outdated' ? 'actualiza' : 'instala'} la extensión:
        <Command>{INSTALL_COMMAND}</Command>
      </li>
      <li>
        <strong className="font-medium">Cierra la sesión de GNOME y vuelve a entrar.</strong> En Wayland una extensión
        nueva o actualizada solo se carga así; hace falta una vez por versión.
      </li>
      <li>
        Si no se activa sola, actívala en la app «Extensiones» o con:
        <Command>{ENABLE_COMMAND}</Command>
      </li>
      <li>
        Abre Drakter y pulsa de nuevo el botón del modo flotante, o usa <kbd>Super+Alt+D</kbd>.
      </li>
    </ol>
  )
}

/** Ayuda de instalación de la extensión. La abren los botones, Ctrl+Shift+F y la bandeja sin extensión. */
export function FloatingHelpDialog() {
  const { state, helpOpen } = useFloating()
  const companion: CompanionStatus = state?.companion ?? 'missing'
  const summary = companion === 'ok' ? null : SUMMARY[companion]

  return (
    <Dialog open={helpOpen} onOpenChange={setFloatingHelpOpen}>
      <DialogContent className="rounded-[var(--radius-sheet)] sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Activar el modo flotante</DialogTitle>
          <DialogDescription>
            {summary ?? 'La extensión de GNOME ya está lista. Puedes cerrar esta ayuda y activar el modo flotante.'}
          </DialogDescription>
        </DialogHeader>
        {companion !== 'ok' ? <Steps companion={companion} /> : null}
        {state?.reason && companion !== 'ok' ? (
          <p className="text-xs text-muted-foreground" role="status">
            Detalle: {state.reason}
          </p>
        ) : null}
        <p className="text-xs text-muted-foreground">
          Guía completa: <span className="font-mono">docs/usage/modo-flotante.md</span>
        </p>
        <DialogFooter>
          <Button onClick={() => setFloatingHelpOpen(false)}>Entendido</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
