/**
 * Contrato de una interfaz del modo Jarvis (J1). Cada interfaz (`nucleo`, `holomesa`, `visor`) vive en
 * `jarvis/layouts/<id>/` con un `index.tsx` que exporta por defecto un componente `JarvisLayout`.
 *
 * `JarvisShell` es el anfitrión: crea el ÚNICO lienzo y el Stage, la capa del avatar elegido y se los
 * pasa; la interfaz pone su HUD en DOM y añade al Stage sus propias capas (y las quita al desmontarse).
 *
 * Qué usa una interfaz, y de dónde:
 * - Datos REST del Workspace: `useJarvisData` de `@/jarvis/data` (instantáneas, D1).
 * - Estado vivo: `stores/*` (chat, agente, trabajos, avisos, confirmaciones, voz, apariencia, modo) y
 *   `voice/levels.ts` (espectro y onda). Las mutaciones, con las funciones de `modules/<x>/api.ts`;
 *   las confirmaciones, con `stores/confirmations` (diálogo nativo de main).
 * - Nada de `fetch` propio, ni caché, ni reglas de negocio en `jarvis/` (jarvis-arquitectura.md §2.2).
 *
 * Decisiones (preguntas de visor-port.md §6, válidas para las tres interfaces):
 * 1. Firma: la interfaz recibe el `Stage` ya creado y un `JarvisAvatarSlot`, no una factory. El avatar
 *    es una preferencia global (`avatarId`): lo crea y lo cambia el anfitrión; la interfaz solo da su
 *    recuadro por función (por fotograma, como W4) y puede colgar paneles de `anchorId`.
 * 2. Arranque y salida: cada interfaz trae los suyos. La entrada se reproduce al montarse y la interfaz
 *    llama a `onReady` en cuanto su primer fotograma se ve (Drakter se desmonta entonces; la entrada
 *    puede seguir). La salida se registra con `setExitTransition` y el anfitrión la espera (tope 1,5 s)
 *    antes de desmontar. Con `reducedMotion`, ni secuencia de entrada ni de salida (fundido ≤ 150 ms).
 * 3. Selector rápido de interfaz y avatar: componente común de `JarvisShell`, en la esquina superior
 *    derecha (reservada: la interfaz no pinta ahí), siempre accesible, también con Ctrl+Shift+A.
 *    También están «Volver a Drakter» (Ctrl+Shift+J), Ajustes y Ctrl+K.
 * 4. Teclado de secciones: lo captura `JarvisShell`, no la interfaz. Ctrl+0…9 (global) y, en Jarvis,
 *    también 0…9 sin modificadores (fuera de campos de texto) con el mismo mapa que la barra de Drakter
 *    (`navigation/sections.ts`). La interfaz recibe `section` y lo representa a su manera (p. ej. el
 *    visor gira al sector de esa sección); para ir a otra, `navigate(section)`.
 */
import type { ComponentType } from 'react'
import type { AvatarViewport } from '@/character/avatars/types'
import type { SectionId } from '@/navigation/sections'
import type { JarvisLayoutChoice } from '@/stores/preferences'
import type { QualityTier, Stage, StageFrame } from '../stage/types'

export type JarvisLayoutId = JarvisLayoutChoice

/** El avatar elegido, dibujado como capa del Stage. La interfaz solo decide dónde va. */
export interface JarvisAvatarSlot {
  /**
   * Recuadro del avatar en px CSS (origen arriba a la izquierda), leído en cada fotograma: la interfaz
   * puede moverlo o animarlo. Sin llamar, va centrado. `null` vuelve al recuadro por defecto.
   */
  setViewport(get: ((frame: StageFrame) => AvatarViewport) | null): void
  /** Id de anclaje del Stage (`stage.anchor(anchorId)`) para colgar paneles DOM del avatar. */
  readonly anchorId: string
  /** Hay avatar 3D dibujándose (no es `none` y cargó). Si no, la interfaz puede mostrar su propio indicador. */
  readonly available: boolean
}

export interface JarvisLayoutProps {
  /** `null`: sin WebGL2 o con el contexto perdido. La interfaz sigue funcionando en DOM («HUD sin lienzo»). */
  readonly stage: Stage | null
  readonly avatar: JarvisAvatarSlot
  /** Nivel de calidad vigente (el Stage lo puede bajar solo; se actualiza). */
  readonly quality: QualityTier
  /** Ajuste de la app o `prefers-reduced-motion`: sin arranque cinematográfico, parallax ni cámara viva. */
  readonly reducedMotion: boolean
  /** Sección actual, común a los dos modos (hash). */
  readonly section: SectionId
  readonly navigate: (section: SectionId) => void
  /**
   * Llamar UNA vez cuando la interfaz ya se ve (su primer fotograma con datos o con su estado de carga).
   * El anfitrión cierra entonces la transición (`settleUiMode('ready')`) y desmonta Drakter.
   */
  readonly onReady: () => void
  /** Volver a Drakter (mismo efecto que el botón común o Ctrl+Shift+J). */
  readonly exit: () => void
  /**
   * Registra la secuencia de salida (al volver a Drakter por cualquier vía). Debe resolver al acabar;
   * el anfitrión no espera más de 1,5 s. `null` la quita. Se borra sola al desmontar la interfaz.
   */
  readonly setExitTransition: (run: (() => Promise<void>) | null) => void
}

export type JarvisLayout = ComponentType<JarvisLayoutProps>

export interface JarvisLayoutMeta {
  readonly id: JarvisLayoutId
  /** Nombre visible (Ajustes, selector rápido, Ctrl+K). */
  readonly name: string
  /** Una línea para Ajustes. */
  readonly description: string
}
