/**
 * El avatar 3D activo como capa del Stage (jarvis-arquitectura.md §2.5 y §4.4): dibuja en el renderer
 * compartido dentro de un recuadro que decide el HUD. No sabe qué avatar es: recibe su `loadLayer`.
 */
import type { AvatarControls } from '@/character/avatars/wiring'
import type { AvatarLayer, AvatarTheme, AvatarViewport, CreateAvatarLayer } from '@/character/avatars/types'
import type { CharacterState } from '@/character/types'
import type { StageAnchor, StageFrame, StageLayer } from '../types'

export interface AvatarStageLayerOptions {
  /** `AvatarEntry.loadLayer` del avatar activo (`character/avatars/registry.ts`). */
  readonly load: () => Promise<CreateAvatarLayer>
  /** Recuadro del avatar en px CSS (origen arriba a la izquierda). Se lee en cada fotograma: el HUD lo mueve. */
  readonly viewport: (frame: StageFrame) => AvatarViewport
  /** Orden de dibujo en el Stage (por defecto 50: sobre fondo y retícula, bajo efectos de primer plano). */
  readonly order?: number
  /** Sin fondo propio (por defecto sí: el fondo es el del Stage). */
  readonly transparent?: boolean
  /** Tema de lo que hay debajo (por defecto `dark`: Jarvis fuerza el tema oscuro). */
  readonly theme?: AvatarTheme
}

export interface AvatarStageLayer extends StageLayer {
  /**
   * Cables estables para `useAvatarWiring`. Antes de que la capa exista se guarda el último estado
   * y se aplica al iniciarse; los avisos de ese intervalo se descartan.
   */
  readonly controls: AvatarControls
  /** El avatar no pudo cargarse en este renderer: el anfitrión puede usar `createAvatar` en un lienzo propio. */
  failed(): boolean
}

const HALF = 0.6 // radio de la mirada: como en createAvatar, 0,6 del lado mayor del recuadro

const clamp = (v: number): number => Math.max(-1, Math.min(1, v))

export function createAvatarStageLayer(options: AvatarStageLayerOptions): AvatarStageLayer {
  let layer: AvatarLayer | null = null
  let failed = false
  let disposed = false
  let state: CharacterState = 'idle'
  let reduced: boolean | null = null
  let vp: AvatarViewport = { x: 0, y: 0, width: 0, height: 0 }
  let sized = { w: 0, h: 0, scale: 0 }

  const controls: AvatarControls = {
    setState: (next) => {
      state = next
      layer?.setState(next)
    },
    setAudioLevel: (level) => layer?.setAudioLevel(level),
    notify: (event) => layer?.notify(event)
  }

  const fit = (frame: StageFrame): void => {
    vp = options.viewport(frame)
    if (!layer) return
    if (vp.width !== sized.w || vp.height !== sized.h || frame.renderScale !== sized.scale) {
      sized = { w: vp.width, h: vp.height, scale: frame.renderScale }
      layer.resize(vp.width, vp.height, frame.renderScale)
    }
  }

  return {
    id: 'avatar',
    order: options.order ?? 50,
    controls,
    failed: () => failed,

    async init(frame) {
      try {
        const create = await options.load()
        if (disposed) return
        const created = create(frame.renderer, {
          reducedMotion: frame.reducedMotion,
          pixelRatio: frame.renderScale,
          transparent: options.transparent ?? true,
          theme: options.theme ?? 'dark'
        })
        layer = created
        reduced = frame.reducedMotion
        created.setState(state)
        fit(frame)
        await created.ready
      } catch (reason) {
        // Un avatar que no carga no tumba el Stage: el resto de capas siguen.
        failed = true
        layer?.dispose()
        layer = null
        console.warn('[drakter:personaje] el avatar no pudo arrancar como capa del Stage', reason)
      }
    },

    update(frame) {
      fit(frame)
      if (!layer) return
      if (frame.reducedMotion !== reduced) {
        reduced = frame.reducedMotion
        layer.setReducedMotion(reduced)
      }
      // Puntero del Stage (-1..1, y hacia arriba) → mirada del avatar (-1..1 respecto a su recuadro, y hacia abajo).
      if (frame.pointer.active && vp.width > 0) {
        const px = ((frame.pointer.x + 1) / 2) * frame.width
        const py = ((1 - frame.pointer.y) / 2) * frame.height
        const half = Math.max(vp.width, vp.height) * HALF
        layer.lookAt(clamp((px - (vp.x + vp.width / 2)) / half), clamp((py - (vp.y + vp.height / 2)) / half))
      } else {
        layer.lookAt(0, 0)
      }
    },

    render(frame) {
      layer?.render(frame.dt, vp)
    },

    anchors(): Readonly<Record<string, StageAnchor>> {
      const visible = layer !== null && vp.width > 0
      return { avatar: { x: vp.x + vp.width / 2, y: vp.y + vp.height / 2, visible } }
    },

    dispose() {
      disposed = true
      layer?.dispose()
      layer = null
    }
  }
}
